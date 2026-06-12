import re
from dataclasses import make_dataclass

import dspy
from pydantic import Field
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic.fields import FieldInfo

from llm_extract.loader import DISALLOWED_NAMES
from llm_extract.models import ALLOWED_TYPES, Attribute, TypeExpr
from llm_extract.exceptions import (
    AttributeTypeConversionError,
    CannotCreateAttributeWithDisallowedNameError,
    CircularTypeReferenceError,
    LoadingAttributesFromExcelError,
    UnknownCustomTypeError,
)

EXTRACTION_SIGNATURE_DOCSTRING = (
    "Extract the attributes from the source where available."
)


def extraction_signature_builder(attrs: list[Attribute]) -> dspy.Signature:
    """
    Build a DSPy Signature class dynamically from a list of attributes.

    :param attrs: list of attributes defining the output fields
    :return: a DSPy Signature class with typed input and output fields
    """
    fields, annotations = fields_builder(attrs)
    return type(
        "ExtractAttributesFromSource",
        (dspy.Signature,),
        {
            **fields,
            "__annotations__": annotations,
            "__doc__": EXTRACTION_SIGNATURE_DOCSTRING,
        },
    )


def fields_builder(
    attrs: list[Attribute],
) -> tuple[dict[str, FieldInfo], dict[str, TypeExpr]]:
    """
    Build DSPy field definitions and type annotations from a list of attributes.

    :param attrs: list of attributes to convert into DSPy fields
    :return: tuple of (fields dict, annotations dict) ready for signature construction
    """
    fields = {"source": dspy.InputField(desc="The source to extract attributes from.")}
    type_hints = {"source": str}
    for attr in attrs:
        fields[attr.name] = dspy.OutputField(desc=attr.description)
        type_hints[attr.name] = attr.attr_type
    return fields, type_hints


def build_attributes_from_sheets(
    sheets: dict[str, list[dict]], root_sheet: str
) -> list[Attribute]:
    """
    Build the attributes for a top-level type from parsed workbook sheets.

    Each sheet represents a user-defined custom type. A field's type may
    reference another sheet by name, in which case that sheet is recursively
    resolved into a nested dataclass.

    :param sheets: dict mapping sheet name to a list of row dicts, as returned
        by load_workbook_sheets
    :param root_sheet: name of the sheet defining the top-level type to extract
    :return: list of parsed Attribute objects for the root sheet
    """
    if root_sheet not in sheets:
        raise UnknownCustomTypeError(f"No sheet named '{root_sheet}' was found.")
    return _resolve_attributes(
        root_sheet,
        sheets,
        building={root_sheet},
        resolved={},
        disallowed_names=DISALLOWED_NAMES,
    )


def _custom_type_names(type_str: str) -> set[str]:
    """
    Extract identifiers from a type expression that refer to user-defined types.

    :param type_str: type expression string, e.g. 'list[Author]' or 'str'
    :return: set of identifiers in the expression that are not built-in allowed types
    """
    return set(re.findall(r"[a-zA-Z]\w*", type_str)) - ALLOWED_TYPES


def _resolve_attributes(
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
    :param building: set of sheet names currently being resolved, used to
        detect circular type references
    :param resolved: cache of sheet name to already-built type, used to avoid
        rebuilding shared custom types
    :param disallowed_names: set of reserved names that cannot be used as attribute names
    :return: list of parsed Attribute objects for the sheet
    """
    attrs = []
    for row in sheets[sheet_name]:
        type_context = {
            name: _build_type(name, sheets, building, resolved)
            for name in _custom_type_names(row["type"])
        }
        try:
            attrs.append(
                Attribute.from_csv_row(
                    row, disallowed_names=disallowed_names, type_context=type_context
                )
            )
        except (
            AttributeTypeConversionError,
            CannotCreateAttributeWithDisallowedNameError,
        ) as exc:
            raise LoadingAttributesFromExcelError(
                f"Failed to load attribute '{row.get('name')}' from sheet "
                f"'{sheet_name}': {exc}"
            )
    return attrs


def _build_type(
    sheet_name: str,
    sheets: dict[str, list[dict]],
    building: set[str],
    resolved: dict[str, TypeExpr],
) -> TypeExpr:
    """
    Build (or retrieve from cache) a pydantic dataclass for a custom type sheet.

    :param sheet_name: name of the sheet defining the custom type
    :param sheets: dict mapping sheet name to a list of row dicts
    :param building: set of sheet names currently being resolved, used to
        detect circular type references
    :param resolved: cache of sheet name to already-built type; updated in
        place with the newly built type before returning
    :return: a pydantic dataclass type built from the sheet's fields
    :raises UnknownCustomTypeError: if no sheet named sheet_name exists
    :raises CircularTypeReferenceError: if sheet_name is already being resolved
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
    attrs = _resolve_attributes(sheet_name, sheets, building, resolved)
    building.discard(sheet_name)

    fields = [
        (attr.name, attr.attr_type, Field(default=None, description=attr.description))
        for attr in attrs
    ]
    cls = pydantic_dataclass(make_dataclass(sheet_name, fields))
    resolved[sheet_name] = cls
    return cls
