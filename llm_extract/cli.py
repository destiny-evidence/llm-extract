from pathlib import Path
from typing import Optional

import typer

from llm_extract.api import extract, extract_folder
from llm_extract.config import configure_dspy
from llm_extract.export import write_extraction_results_to_folder
from llm_extract.factory import build_attributes_from_sheets
from llm_extract.loader import load_attributes_csv, load_workbook_sheets

app = typer.Typer()

EXCEL_SUFFIXES = {".xlsx", ".xlsm"}
SUPPORTED_FILETYPES = {"txt", "md"}


def _load_attributes(attrs: Path, root_type: Optional[str]) -> list:
    """Load attributes from CSV or Excel file."""
    if attrs.suffix.lower() in EXCEL_SUFFIXES:
        if root_type is None:
            raise typer.BadParameter(
                "--type is required when --attrs is an Excel workbook.",
                param_hint="--type",
            )
        sheets = load_workbook_sheets(attrs)
        return build_attributes_from_sheets(sheets, root_type)
    else:
        return load_attributes_csv(attrs)


def _validate_filetypes(filetypes: list[str]) -> list[str]:
    """
    Validate filetypes against the supported list.

    :param filetypes: list of requested file types
    :return: the same list if all are valid
    :raises typer.BadParameter: if any filetype is unsupported
    """
    for ft in filetypes:
        if ft not in SUPPORTED_FILETYPES:
            raise typer.BadParameter(
                f"Unsupported file type '{ft}'. Supported: {', '.join(sorted(SUPPORTED_FILETYPES))}",
                param_hint="--filetype",
            )
    return filetypes


def _validate_output_is_directory(output: Optional[Path]) -> None:
    """
    Validate that output path is a directory, not a file.

    :param output: the output path to validate
    :raises typer.BadParameter: if output has a file extension
    """
    if output is not None and output.suffix:
        raise typer.BadParameter(
            "When extracting from a folder, --output must be a directory, not a file.",
            param_hint="--output",
        )


@app.command()
def file(
    source: Path = typer.Option(
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
            "Where to write results. Pass a .csv or .xlsx file path for an exact "
            "destination, or a directory to auto-name the file as "
            "<source>-extracted.csv. If omitted, results are printed to the console."
        ),
        file_okay=True,
        dir_okay=True,
        writable=True,
    ),
) -> None:
    """Extract structured attributes from a single text file."""
    configure_dspy(env_file=env_file)
    attributes = _load_attributes(attrs, root_type)

    result = extract(source.read_text(), attributes, with_reasoning=with_reasoning)
    if output is None:
        result.display()
    else:
        if output.is_dir():
            extension = "xlsx" if attrs.suffix.lower() in EXCEL_SUFFIXES else "csv"
            output = output / f"{source.stem}-extracted.{extension}"
        if output.suffix.lower() in EXCEL_SUFFIXES:
            result.write_excel(output)
        else:
            result.write_csv(output)


@app.command()
def folder(
    source: Path = typer.Option(
        ...,
        help="Folder containing text files to extract attributes from.",
        exists=True,
        file_okay=False,
        dir_okay=True,
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
    filetypes: list[str] = typer.Option(
        ["txt"],
        "--filetype",
        help=f"File type(s) to extract from. Supported: {', '.join(sorted(SUPPORTED_FILETYPES))}",
    ),
    max_concurrent: int = typer.Option(
        8,
        "--max-concurrent",
        help="Maximum number of concurrent extractions (default 8).",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        is_flag=True,
        help="Recursively traverse subdirectories and preserve directory structure in output.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        help=(
            "Directory to write results to. Each file is written as <filename>-extracted.csv or .xlsx. "
            "If omitted, creates <source>-extracted/ in the same parent directory as the source folder."
        ),
        file_okay=False,
        dir_okay=True,
        writable=True,
    ),
) -> None:
    """Extract structured attributes from multiple text files in a folder."""
    configure_dspy(env_file=env_file)
    attributes = _load_attributes(attrs, root_type)
    filetypes = _validate_filetypes(filetypes)
    _validate_output_is_directory(output)

    results = extract_folder(
        source,
        attributes,
        filetypes=filetypes,
        with_reasoning=with_reasoning,
        max_concurrent=max_concurrent,
        recursive=recursive,
    )

    if not results:
        typer.echo(
            f"No files matching {', '.join(f'.{ft}' for ft in filetypes)} found in {source}"
        )
        return

    output_dir = output or (source.parent / f"{source.name}-extracted")
    use_excel = attrs.suffix.lower() in EXCEL_SUFFIXES
    write_extraction_results_to_folder(output_dir, results, use_excel=use_excel)
    typer.echo(f"Extracted {len(results)} files to {output_dir}")
