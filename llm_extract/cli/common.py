from pathlib import Path
from typing import Optional

import typer

from llm_extract.factory import (
    build_attributes_from_workbook,
    build_attributes_from_csv,
)
from llm_extract.loader import load_workbook, load_csv, SUPPORTED_FILETYPES

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


def validate_filetype(filetype: str, param_hint: str) -> None:
    """
    Validate a single filetype against the supported list.

    :param filetype: the file type to validate, without a leading dot (e.g. "pdf")
    :param param_hint: CLI option name to report in the error message
    :raises typer.BadParameter: if filetype is unsupported
    """
    if filetype not in SUPPORTED_FILETYPES:
        raise typer.BadParameter(
            f"Unsupported file type '{filetype}'. Supported: {', '.join(sorted(SUPPORTED_FILETYPES))}",
            param_hint=param_hint,
        )


def validate_output_dir(output_dir: Optional[Path]) -> None:
    """
    Validate that output_dir is a directory, not a file.

    Typer's own file_okay/dir_okay checks only apply to paths that already exist,
    so a nonexistent path shaped like a file (e.g. "results.csv") would otherwise
    silently be treated as a directory to create.

    :param output_dir: the output path to validate
    :raises typer.BadParameter: if output_dir has a file extension
    """
    if output_dir is not None and output_dir.suffix:
        raise typer.BadParameter(
            "--output-dir must be a directory, not a file.",
            param_hint="--output-dir",
        )
