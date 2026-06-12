from pathlib import Path
from typing import Optional

import typer

from llm_extract.api import extract
from llm_extract.config import configure_dspy
from llm_extract.factory import build_attributes_from_sheets
from llm_extract.loader import load_attributes_csv, load_workbook_sheets

app = typer.Typer()

EXCEL_SUFFIXES = {".xlsx", ".xlsm"}


@app.command(name="extract")
def extract_command(
    file: Path = typer.Option(
        ...,
        help="Source text file to extract attributes from.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    attrs: Path = typer.Option(
        ...,
        help=(
            "CSV or Excel file defining the attributes to extract. For an Excel "
            "workbook, each sheet defines a custom type and --type selects the "
            "top-level sheet to extract."
        ),
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    root_type: Optional[str] = typer.Option(
        None,
        "--type",
        help="Name of the top-level sheet to extract. Required when --attrs is an Excel workbook.",
    ),
    env_file: Optional[Path] = typer.Option(
        None,
        "--env",
        help="Path to a .env file to load.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    with_reasoning: bool = typer.Option(
        False,
        "--with-reasoning",
        is_flag=True,
        help="Use chain-of-thought reasoning. Produces a _reasoning_ row in the output but adds latency and cost.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        help=(
            "Where to write results. Pass a .csv file path for an exact destination, "
            "or a directory to auto-name the file as <source>-extracted.csv. "
            "If omitted, results are printed to the console."
        ),
        file_okay=True,
        dir_okay=True,
        writable=True,
    ),
) -> None:
    """Extract structured attributes from a text file."""
    configure_dspy(env_file=env_file)
    if attrs.suffix.lower() in EXCEL_SUFFIXES:
        if root_type is None:
            raise typer.BadParameter(
                "--type is required when --attrs is an Excel workbook.",
                param_hint="--type",
            )
        sheets = load_workbook_sheets(attrs)
        attributes = build_attributes_from_sheets(sheets, root_type)
    else:
        attributes = load_attributes_csv(attrs)
    result = extract(file.read_text(), attributes, with_reasoning=with_reasoning)
    if output is None:
        result.display()
    else:
        if output.is_dir():
            output = output / f"{file.stem}-extracted.csv"
        result.write_csv(output)
