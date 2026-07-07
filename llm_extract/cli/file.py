from pathlib import Path
from typing import Optional

import typer

from llm_extract.api import extract
from llm_extract.cli.common import app, _load_attributes, EXCEL_SUFFIXES
from llm_extract.config import configure_dspy
from llm_extract.export import ExtractionResult
from llm_extract.models import ExtractionStage, MixedDocument


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
    """Extract structured attributes from a single file (text or PDF)."""
    is_pdf = source.suffix.lower() == ".pdf"
    configure_dspy(env_file=env_file, multimodal=is_pdf)
    attributes = _load_attributes(attrs, root_type)

    result = extract(
        source,
        attributes,
        with_reasoning=with_reasoning,
        on_progress=_file_progress_callback,
    )
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


def _file_progress_callback(
    stage: ExtractionStage,
    source: Path,
    result: ExtractionResult | None = None,
    error: Exception | None = None,
    doc: MixedDocument | None = None,
) -> None:
    """
    Display extraction progress for single file extraction.

    :param stage: the current extraction stage
    :param source: path to the source file being processed
    :param result: the extraction result (populated on COMPLETED stage)
    :param error: any error that occurred (populated on COMPLETED stage)
    :param doc: the MixedDocument object for PDFs (populated on TRANSFORMING_PDF stage)
    """
    match stage:
        case ExtractionStage.LOADING_SOURCE:
            typer.echo(f"Loading {source.name}...")
        case ExtractionStage.SOURCE_LOADED:
            typer.echo(f"✓ Loaded {source.name}")
        case ExtractionStage.TRANSFORMING_PDF:
            if doc:
                ratio = f"({doc.text_page_count} text, {doc.image_page_count} images)"
                typer.echo(f"Processing PDF pages... {ratio}")
            else:
                typer.echo(f"Processing PDF pages...")
        case ExtractionStage.EXTRACTING:
            typer.echo(f"Extracting with LLM...")
        case ExtractionStage.COMPLETED:
            if error:
                typer.echo(f"❌ Failed: {error}")
            else:
                typer.echo(f"✓ Extracted {len(result.attributes)} attributes")
