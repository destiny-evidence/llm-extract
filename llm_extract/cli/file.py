from pathlib import Path
from typing import Optional

import typer

from llm_extract.api import extract
from llm_extract.cli.common import (
    app,
    _load_attributes,
    validate_filetype,
    validate_output_dir,
    EXCEL_SUFFIXES,
)
from llm_extract.config import configure_dspy
from llm_extract.export import ExtractionResult, write_extraction_result
from llm_extract.loader import MULTIMODAL_FILETYPES
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
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help=(
            "Directory to write results to, named <source>-extracted.csv or .xlsx "
            "(chosen from --attrs). Defaults to the current working directory."
        ),
        file_okay=False,
        dir_okay=True,
        writable=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        is_flag=True,
        help=(
            "Additionally write a <source>-extracted.json file, preserving the "
            "full nested structure for programmatic use."
        ),
    ),
) -> None:
    """Extract structured attributes from a single file (text or PDF)."""
    filetype = source.suffix.lower().lstrip(".")
    validate_filetype(filetype, param_hint="--source")
    is_multimodal = filetype in MULTIMODAL_FILETYPES
    configure_dspy(env_file=env_file, multimodal=is_multimodal)
    attributes = _load_attributes(attrs, root_type)
    use_excel = attrs.suffix.lower() in EXCEL_SUFFIXES
    validate_output_dir(output_dir)

    result = extract(
        source,
        attributes,
        with_reasoning=with_reasoning,
        on_progress=_file_progress_callback,
    )

    write_dir = output_dir or Path.cwd()
    extension = "xlsx" if use_excel else "csv"
    output_path = write_dir / f"{source.stem}-extracted.{extension}"
    write_extraction_result(result, output_path, use_excel, also_json=json_output)

    typer.echo(f"Extracted attributes to {output_path}")


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
