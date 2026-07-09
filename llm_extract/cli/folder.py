from pathlib import Path
from typing import Optional, Callable

import typer
from tqdm import tqdm

from llm_extract.api import extract_folder
from llm_extract.cli.common import app, _load_attributes, EXCEL_SUFFIXES
from llm_extract.config import configure_dspy
from llm_extract.export import write_extraction_results_to_folder
from llm_extract.loader import SUPPORTED_FILETYPES


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
        help=f"File type(s) to extract from. Supported: {', '.join(sorted(SUPPORTED_FILETYPES))}. PDF extraction requires a vision-capable model.",
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
    json_output: bool = typer.Option(
        False,
        "--json",
        is_flag=True,
        help=(
            "Additionally write a <filename>-extracted.json file per result, "
            "preserving the full nested structure for programmatic use."
        ),
    ),
) -> None:
    """Extract structured attributes from multiple files in a folder (text or PDF)."""
    filetypes = _validate_filetypes(filetypes)
    has_pdf = "pdf" in filetypes
    configure_dspy(env_file=env_file, multimodal=has_pdf)
    attributes = _load_attributes(attrs, root_type)
    _validate_output_is_directory(output)

    results = extract_folder(
        source,
        attributes,
        filetypes=filetypes,
        with_reasoning=with_reasoning,
        max_concurrent=max_concurrent,
        recursive=recursive,
        on_progress=_make_folder_progress_callback(),
    )

    if not results:
        typer.echo(
            f"No files matching {', '.join(f'.{ft}' for ft in filetypes)} found in {source}"
        )
        return

    output_dir = output or (source.parent / f"{source.name}-extracted")
    use_excel = attrs.suffix.lower() in EXCEL_SUFFIXES
    write_extraction_results_to_folder(
        output_dir,
        results,
        use_excel=use_excel,
        also_json=json_output,
        on_progress=_make_export_progress_callback(),
    )
    typer.echo(f"Extracted {len(results)} files to {output_dir}")


def _make_folder_progress_callback() -> Callable[[str, int, int], None]:
    """
    Create a progress callback for folder extraction.

    Returns a callback that displays a tqdm progress bar during the loading phase.
    DSPy handles progress display during batch extraction.

    :return: progress callback (stage, current, total) -> None
    """
    loading_bar = None

    def callback(stage: str, current: int, total: int) -> None:
        nonlocal loading_bar
        if stage == "loading_source":
            if loading_bar is None:
                loading_bar = tqdm(total=total, desc="Loading sources", unit="file")
            loading_bar.update(1)
            if current == total - 1:
                loading_bar.close()
                loading_bar = None

    return callback


def _make_export_progress_callback() -> Callable[[int, int], None]:
    """
    Create a progress callback for writing extraction results to a folder.

    Returns a callback that displays a tqdm progress bar while results are written to disk.

    :return: progress callback (current, total) -> None
    """
    write_bar = None

    def callback(current: int, total: int) -> None:
        nonlocal write_bar
        if write_bar is None:
            write_bar = tqdm(total=total, desc="Writing results", unit="file")
        write_bar.update(1)
        if current == total:
            write_bar.close()
            write_bar = None

    return callback


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
