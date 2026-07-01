import re
from dataclasses import make_dataclass
from typing import Union

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


def extraction_signature_builder(
    attrs: list[Attribute], multimodal: bool = False
) -> dspy.Signature:
    """
    Build a DSPy Signature class dynamically from a list of attributes.

    :param attrs: list of attributes defining the output fields
    :param multimodal: if True, source field accepts mixed text/image content
    :return: a DSPy Signature class with typed input and output fields
    """
    fields, annotations = fields_builder(attrs, multimodal=multimodal)
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
    multimodal: bool = False,
) -> tuple[dict[str, FieldInfo], dict[str, TypeExpr]]:
    """
    Build DSPy input/output fields from a list of attributes.

    :param attrs: list of attributes
    :param multimodal: if True, source field accepts mixed text/image content
    :return: tuple of (fields dict, annotations dict)
    """
    source_type = Union[str, list[Union[str, dspy.Image]]] if multimodal else str
    fields = {
        "source": dspy.InputField(
            description="The source material to extract attributes from."
        )
    }
    annotations = {"source": source_type}

    for attr in attrs:
        fields[attr.name] = dspy.OutputField(description=attr.description)
        annotations[attr.name] = attr.attr_type

    return fields, annotations


def _custom_type_names(type_str: str) -> set[str]:
    """Extract identifiers from type expression that may refer to custom types."""
    # Handle both ASCII and Unicode smart quotes
    without_quotes = re.sub(r'[\'""“”][^\'"]*[\'""“”]', "", type_str)
    return set(re.findall(r"[a-zA-Z]\w*", without_quotes)) - ALLOWED_TYPES


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
    :param resolved: dict of sheet names to their resolved TypeExpr dataclass
    :param disallowed_names: set of names that cannot be used as attribute names
    :return: list of Attribute objects
    """
    attrs = []
    for row in sheets[sheet_name]:
        type_context = {
            name: _build_type(name, sheets, building, resolved)
            for name in _custom_type_names(row["type"])
        }
        try:
            attr = Attribute.from_csv_row(
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


def _build_type(
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
    :param building: set of sheet names currently in progress (to detect cycles)
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
    attrs = _resolve_attributes(sheet_name, sheets, building, resolved)
    building.discard(sheet_name)

    fields = [
        (attr.name, attr.attr_type, Field(description=attr.description))
        for attr in attrs
    ]

    resolved[sheet_name] = pydantic_dataclass(make_dataclass(sheet_name, fields))
    return resolved[sheet_name]


def build_attributes_from_sheets(
    sheets: dict[str, list[dict]], root_sheet: str = "Query"
) -> list[Attribute]:
    """
    Build a list of attributes from a workbook.

    Each sheet in the workbook defines a type: the sheet name is the type name,
    and each row in the sheet is a field in that type.

    :param sheets: dict mapping sheet name to list of row dicts
    :param root_sheet: name of the top-level sheet to extract
    :return: list of Attribute objects
    :raises UnknownCustomTypeError: if root_sheet or any referenced sheet doesn't exist
    :raises CircularTypeReferenceError: if sheets reference each other in a cycle
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
