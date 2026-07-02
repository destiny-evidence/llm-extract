import re
from dataclasses import make_dataclass

from pydantic import Field
from pydantic.dataclasses import dataclass as pydantic_dataclass

from llm_extract.exceptions import (
    UnknownCustomTypeError,
    AttributeTypeConversionError,
    LoadingAttributesFromExcelError,
    CannotCreateAttributeWithDisallowedNameError,
    CircularTypeReferenceError,
)
from llm_extract.factory.type import (
    DISALLOWED_NAMES,
    normalise_literal_type,
    remove_quoted_strings,
)
from llm_extract.factory.attribute import build_attribute_from_row
from llm_extract.models import WorkbookData, Attribute, ALLOWED_TYPES, TypeExpr


def build_attributes_from_workbook(
    workbook_data: WorkbookData, root_sheet: str = "Query"
) -> list[Attribute]:
    """
    Build a list of attributes from workbook data.

    :param workbook_data: WorkbookData containing all sheets
    :param root_sheet: name of the top-level sheet to extract
    :return: list of Attribute objects
    :raises UnknownCustomTypeError: if root_sheet doesn't exist
    :raises CircularTypeReferenceError: if sheets reference each other in a cycle
    """
    return _build_attributes_from_sheets(workbook_data.sheets, root_sheet)


def _build_attributes_from_sheets(
    sheets: dict[str, list[dict]], root_sheet: str = "Query"
) -> list[Attribute]:
    """
    Build a list of attributes from a workbook.

    Each sheet in the workbook defines a type: the sheet name is the type name,
    and each row in the sheet is a field of that type.

    :param sheets: dict mapping sheet name to list of row dicts
    :param root_sheet: name of the top-level sheet to extract
    :return: list of Attribute objects
    :raises UnknownCustomTypeError: if root_sheet or any referenced sheet doesn't exist
    :raises CircularTypeReferenceError: if sheets reference each other in a cycle
    """
    if root_sheet not in sheets:
        raise UnknownCustomTypeError(f"No sheet named '{root_sheet}' was found.")
    return _resolve_sheet_to_attributes(
        root_sheet,
        sheets,
        building={root_sheet},
        resolved={},
        disallowed_names=DISALLOWED_NAMES,
    )


def _get_custom_type_names(type_str: str) -> set[str]:
    """
    Extract identifiers from a type expression that refer to custom types.

    :param type_str: type expression string, e.g. 'list[Author]' or 'str'
    :return: set of identifiers that are not built-in allowed types
    """
    normalised = normalise_literal_type(type_str)
    without_strings = remove_quoted_strings(normalised)
    return set(re.findall(r"[a-zA-Z]\w*", without_strings)) - ALLOWED_TYPES


def _resolve_sheet_to_attributes(
    sheet_name: str,
    sheets: dict[str, list[dict]],
    building: set[str],
    resolved: dict[str, TypeExpr],
    disallowed_names: set[str] = frozenset(),
) -> list[Attribute]:
    """
    Resolve the rows of a sheet into a list of Attribute objects.

    Any custom type referenced by a row's 'type' expression is recursively
    resolved into a nested dataclass via _build_type.

    :param sheet_name: name of the sheet whose rows should be resolved
    :param sheets: dict mapping sheet name to a list of row dicts
    :param building: set of sheet names currently being resolved (for cycle detection)
    :param resolved: dict of sheet names to their resolved TypeExpr dataclass
    :param disallowed_names: set of names that cannot be used as attribute names
    :return: list of Attribute objects
    """
    attrs = []
    for row in sheets[sheet_name]:
        type_context = {
            name: _build_custom_type(name, sheets, building, resolved)
            for name in _get_custom_type_names(row["type"])
        }
        try:
            attr = build_attribute_from_row(
                row,
                disallowed_names=disallowed_names,
                type_context=type_context,
            )
            attrs.append(attr)
        except AttributeTypeConversionError as e:
            raise LoadingAttributesFromExcelError(
                f"In sheet '{sheet_name}': {e.args[0]}"
            )
        except CannotCreateAttributeWithDisallowedNameError as e:
            raise LoadingAttributesFromExcelError(
                f"In sheet '{sheet_name}': {e.args[0]}"
            )

    return attrs


def _build_custom_type(
    sheet_name: str,
    sheets: dict[str, list[dict]],
    building: set[str],
    resolved: dict[str, TypeExpr],
) -> TypeExpr:
    """
    Build a type for a custom type (sheet) reference.

    Recursively resolves any other custom types that the target sheet references.

    :param sheet_name: name of the sheet to build a type for
    :param sheets: dict of all sheets
    :param building: set of sheet names currently in progress (for cycle detection)
    :param resolved: dict of already-resolved sheet names to their TypeExpr
    :return: the TypeExpr for the resolved sheet
    """
    if sheet_name in resolved:
        return resolved[sheet_name]
    if sheet_name not in sheets:
        raise UnknownCustomTypeError(f"No sheet named '{sheet_name}' was found.")
    if sheet_name in building:
        raise CircularTypeReferenceError(
            f"Circular type reference detected involving '{sheet_name}'."
        )

    building.add(sheet_name)
    attrs = _resolve_sheet_to_attributes(sheet_name, sheets, building, resolved)
    building.discard(sheet_name)

    fields = [
        (attr.name, attr.attr_type, Field(description=attr.description))
        for attr in attrs
    ]

    resolved[sheet_name] = pydantic_dataclass(make_dataclass(sheet_name, fields))
    return resolved[sheet_name]
