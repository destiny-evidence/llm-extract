import typing
from dataclasses import dataclass
from enum import StrEnum

from pydantic.dataclasses import dataclass as pydantic_dataclass


class ExtractionStage(StrEnum):
    """Stages in the extraction pipeline."""

    LOADING_SOURCE = "loading_source"
    SOURCE_LOADED = "source_loaded"
    TRANSFORMING_PDF = "transforming_pdf"
    EXTRACTING = "extracting"
    COMPLETED = "completed"


# TODO could add Optional + Union for more sophisticated types
ALLOWED_TYPES = {
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "tuple",
    "set",
    "None",
    "Literal",
}

TypeExpr = typing.Any


@dataclass
class CSVData:
    """CSV attribute data loaded from a file."""

    rows: list[dict[str, str]]


@dataclass
class WorkbookData:
    """Excel workbook attribute data loaded from a file."""

    sheets: dict[str, list[dict[str, str]]]


@pydantic_dataclass
class Attribute:
    """Represents a single extractable attribute with its name, type, and description."""

    name: str
    attr_type: TypeExpr
    description: str
