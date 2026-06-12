import csv
import dataclasses
import json
import re
import typing
from pathlib import Path

import dspy
import openpyxl
from pydantic_core import to_jsonable_python

from llm_extract.models import Attribute

NOT_FOUND = "NOT_FOUND"

_INVALID_SHEET_NAME_CHARS = re.compile(r"[:\\/?*\[\]]")


def _format_value(value: object) -> object:
    if value is None:
        return NOT_FOUND
    if isinstance(value, str):
        return value.strip("\"'")
    if isinstance(value, (list, dict)) or dataclasses.is_dataclass(value):
        # Custom types from Excel templates are nested pydantic dataclasses,
        # which json.dumps can't serialise directly - convert to plain
        # dicts/lists first, recursing through any nesting.
        return json.dumps(to_jsonable_python(value))
    return value


def _unwrap_optional(type_: object) -> object:
    """
    Unwrap an `Optional[X]` annotation to `X`.

    :param type_: a type annotation, possibly `Optional[X]`
    :return: `X` if `type_` is `Optional[X]`, otherwise `type_` unchanged
    """
    args = typing.get_args(type_)
    if type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return type_


def _sanitize_sheet_name(name: str) -> str:
    """
    Make a string safe to use as an Excel sheet title.

    :param name: the proposed sheet name
    :return: `name` with characters invalid in Excel sheet titles replaced
             by underscores and truncated to Excel's 31 character limit
    """
    return _INVALID_SHEET_NAME_CHARS.sub("_", name)[:31]


def _flatten_columns(dataclass_type: type, prefix: str = "") -> list[str]:
    """
    Compute flattened column names for a dataclass type.

    Fields whose type is itself a dataclass are flattened into dot-prefixed
    columns (e.g. "intervention_type.type_of_intervention"). Any other
    field, including a list of dataclasses, becomes a single column.

    :param dataclass_type: the dataclass type to flatten
    :param prefix: prefix to prepend to each column name
    :return: list of flattened column names
    """
    columns = []
    for field in dataclasses.fields(dataclass_type):
        inner_type = _unwrap_optional(field.type)
        name = f"{prefix}{field.name}"
        if dataclasses.is_dataclass(inner_type):
            columns.extend(_flatten_columns(inner_type, prefix=f"{name}."))
        else:
            columns.append(name)
    return columns


def _flatten_instance(instance: object, dataclass_type: type, prefix: str = "") -> dict:
    """
    Flatten a dataclass instance into a dict of column name to formatted value.

    :param instance: the dataclass instance to flatten, or None
    :param dataclass_type: the dataclass type describing `instance`'s shape
    :param prefix: prefix to prepend to each column name
    :return: dict mapping flattened column names to values formatted via
             :func:`_format_value`
    """
    row = {}
    for field in dataclasses.fields(dataclass_type):
        inner_type = _unwrap_optional(field.type)
        name = f"{prefix}{field.name}"
        value = getattr(instance, field.name, None) if instance is not None else None
        if dataclasses.is_dataclass(inner_type):
            row.update(_flatten_instance(value, inner_type, prefix=f"{name}."))
        else:
            row[name] = _format_value(value)
    return row


def _write_dataclass_sheet(
    workbook: openpyxl.Workbook, sheet_name: str, dataclass_type: type, items: list
) -> None:
    """
    Add a sheet with one row per item, flattening dataclass fields into columns.

    :param workbook: the workbook to add the sheet to
    :param sheet_name: title for the new sheet, assumed already sanitised
    :param dataclass_type: the dataclass type describing each item's shape
    :param items: dataclass instances to write as rows, must be non-empty
    """
    columns = _flatten_columns(dataclass_type)
    sheet = workbook.create_sheet(sheet_name)
    sheet.append(columns)
    for item in items:
        row = _flatten_instance(item, dataclass_type)
        sheet.append([row[column] for column in columns])


def _append_link_row(
    sheet: openpyxl.worksheet.worksheet.Worksheet, name: str, target_sheet_name: str
) -> None:
    """
    Append a [name, link] row, where the link cell jumps to another sheet.

    :param sheet: the sheet to append the row to
    :param name: value for the first ("name") column
    :param target_sheet_name: title of the sheet the link cell should jump to
    """
    sheet.append([name, target_sheet_name])
    link_cell = sheet.cell(row=sheet.max_row, column=2)
    link_cell.hyperlink = f"#'{target_sheet_name}'!A1"
    link_cell.style = "Hyperlink"


@dataclasses.dataclass
class ExtractionResult:
    """Wraps a DSPy Prediction with CSV and Excel serialisation."""

    prediction: dspy.Prediction
    attributes: list[Attribute] = dataclasses.field(default_factory=list)

    def to_csv_rows(self) -> list[list]:
        """
        Serialise extraction results to a list of rows ready for csv.writer.

        :return: list of [name, value] rows, with a header row first and an
                 optional [_reasoning_, ...] row last if reasoning was produced
        """
        rows = [["name", "value"]]

        for key in (k for k in self.prediction.keys() if k != "reasoning"):
            value = getattr(self.prediction, key)
            rows.append([key, _format_value(value)])

        reasoning = getattr(self.prediction, "reasoning", None)
        if reasoning is not None:
            rows.append(["_reasoning_", reasoning])

        return rows

    def write_csv(self, path: Path) -> None:
        """
        Write extraction results to a CSV file.

        :param path: destination file path
        """
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(self.to_csv_rows())

    def write_excel(self, path: Path) -> None:
        """
        Write extraction results to an Excel workbook.

        A "Summary" sheet has one row per top-level attribute. Plain
        attributes show their formatted value directly. Attributes that are
        a custom type, or a non-empty list of a custom type, instead get a
        link to a dedicated sheet: one row per item, with columns for each
        field. Fields that are themselves a custom type one level deep are
        flattened into dot-prefixed columns (e.g.
        "intervention_type.type_of_intervention"); any deeper nesting falls
        back to a JSON-encoded cell. Custom-type attributes with no value are
        shown as NOT_FOUND in the Summary sheet, with no dedicated sheet.

        :param path: destination file path
        """
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)
        summary = workbook.create_sheet("Summary")
        summary.append(["name", "value"])

        for attr in self.attributes:
            value = getattr(self.prediction, attr.name, None)
            inner_type = _unwrap_optional(attr.attr_type)

            dataclass_type = None
            items = []
            if typing.get_origin(inner_type) is list:
                (elem_type,) = typing.get_args(inner_type)
                if dataclasses.is_dataclass(elem_type):
                    dataclass_type, items = elem_type, value or []
            elif dataclasses.is_dataclass(inner_type):
                dataclass_type = inner_type
                items = [value] if value is not None else []

            if dataclass_type is None:
                summary.append([attr.name, _format_value(value)])
            elif items:
                sheet_name = _sanitize_sheet_name(attr.name)
                _write_dataclass_sheet(workbook, sheet_name, dataclass_type, items)
                _append_link_row(summary, attr.name, sheet_name)
            else:
                summary.append([attr.name, NOT_FOUND])

        reasoning = getattr(self.prediction, "reasoning", None)
        if reasoning is not None:
            summary.append(["_reasoning_", reasoning])

        workbook.save(path)

    def display(self) -> None:
        """Print extraction results as an aligned two-column table to stdout."""
        rows = self.to_csv_rows()
        name_width = max(len(str(row[0])) for row in rows)
        for row in rows:
            print(f"{str(row[0]).ljust(name_width)}  {row[1]}")
