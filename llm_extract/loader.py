import csv
from pathlib import Path

import openpyxl

from llm_extract.models import Attribute
from llm_extract.exceptions import (
    AttributeTypeConversionError,
    CannotCreateAttributeWithDisallowedNameError,
    LoadingAttributeFromCSVError,
)

EXPECTED_COLUMNS = {"name", "type", "description"}
DISALLOWED_NAMES = {"source"}


def load_attributes_csv(path: Path | str) -> list[Attribute]:
    """
    Load and parse attributes from a CSV file.

    :param path: path to the CSV file with columns: name, type, description
    :return: list of parsed Attribute objects
    """
    path = Path(path)
    with path.open() as f:
        reader = csv.DictReader(f)
        missing = EXPECTED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing columns: {missing}")
        try:
            attributes = [
                Attribute.from_csv_row(row, disallowed_names=DISALLOWED_NAMES)
                for row in reader
            ]
        except (
            AttributeTypeConversionError,
            CannotCreateAttributeWithDisallowedNameError,
        ) as exc:
            raise LoadingAttributeFromCSVError(
                f"Failed to load attributes from csv: {exc}"
            )
        return attributes


def load_workbook_sheets(path: Path | str) -> dict[str, list[dict]]:
    """
    Load all sheets from an Excel workbook as raw attribute rows.

    Each sheet represents a user-defined custom type, and must have 'name',
    'type' and 'description' columns, with each row describing one field of
    that type.

    :param path: path to the Excel workbook
    :return: dict mapping sheet name to a list of row dicts
    """
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = {}
    for name in workbook.sheetnames:
        rows = workbook[name].iter_rows(values_only=True)
        header = next(rows, None)
        if header is None:
            sheets[name] = []
            continue
        missing = EXPECTED_COLUMNS - set(header)
        if missing:
            raise ValueError(f"Sheet '{name}' missing columns: {missing}")
        sheets[name] = [
            dict(zip(header, row))
            for row in rows
            if any(cell is not None for cell in row)
        ]
    return sheets
