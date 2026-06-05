from pathlib import Path

import typer
from typing import Optional

from llm_extract.api import extract
from llm_extract.config import configure_dspy
from llm_extract.loader import load_attributes_csv

app = typer.Typer()


@app.command()
def extract(
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
        help="Path to a .env file to load.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    """Extract structured attributes from a text file."""
    configure_dspy(env_file=env_file)
    attributes = load_attributes_csv(attrs)
    results = extract(file.read_text(), attributes)
    typer.echo(results)
