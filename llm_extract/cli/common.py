from pathlib import Path
from typing import Optional

import typer

from llm_extract.factory import (
    build_attributes_from_workbook,
    build_attributes_from_csv,
)
from llm_extract.loader import load_workbook, load_csv

app = typer.Typer()
EXCEL_SUFFIXES = {".xlsx", ".xlsm"}


def _load_attributes(attrs: Path, root_type: Optional[str]) -> list:
    """
    Load attributes from CSV or Excel workbook.

    :param attrs: path to the attributes file (CSV or Excel workbook)
    :param root_type: name of the top-level sheet (required for Excel workbooks)
    :return: list of Attribute objects
    :raises typer.BadParameter: if Excel workbook is provided without --type
    """
    if attrs.suffix.lower() in EXCEL_SUFFIXES:
        if root_type is None:
            raise typer.BadParameter(
                "--type is required when --attrs is an Excel workbook.",
                param_hint="--type",
            )
        workbook_data = load_workbook(attrs)
        return build_attributes_from_workbook(workbook_data, root_type)
    else:
        csv_data = load_csv(attrs)
        return build_attributes_from_csv(csv_data)
