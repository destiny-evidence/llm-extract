from pathlib import Path
from typing import Optional

import typer

from llm_extract.api import extract
from llm_extract.config import configure_dspy
from llm_extract.loader import load_attributes_csv

app = typer.Typer()


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
        help="CSV file defining the attributes to extract.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
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
    attributes = load_attributes_csv(attrs)
    result = extract(file.read_text(), attributes)
    if output is None:
        result.display()
    else:
        if output.is_dir():
            output = output / f"{file.stem}-extracted.csv"
        result.write_csv(output)
