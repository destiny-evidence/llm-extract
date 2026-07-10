from pathlib import Path
from typing import Callable

from llm_extract.export.extraction_result import ExtractionResult


def write_extraction_result(
    result: ExtractionResult,
    output_path: Path,
    use_excel: bool,
    also_json: bool = False,
) -> None:
    """
    Write a single extraction result to disk, choosing the format and optionally
    writing a JSON sidecar alongside it.

    :param result: the extraction result to write
    :param output_path: destination path for the csv/xlsx file
    :param use_excel: whether to write an Excel file (True) or CSV file (False)
    :param also_json: whether to additionally write a JSON file alongside it,
                       named after `output_path` with a .json extension
    :return: None
    """
    if use_excel:
        result.write_excel(output_path)
    else:
        result.write_csv(output_path)

    if also_json:
        result.write_json(output_path.with_suffix(".json"))


def write_extraction_results_to_folder(
    output_dir: Path,
    results: list[tuple[str, ExtractionResult]],
    use_excel: bool = False,
    also_json: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    """
    Write multiple extraction results to a folder with one file per result.

    Each file is named <filename>-extracted.csv or .xlsx depending on use_excel.
    Preserves directory structure when results include relative paths with subdirectories.

    :param output_dir: directory to write results to (created if it doesn't exist)
    :param results: list of (filename_or_relative_path, ExtractionResult) tuples
    :param use_excel: whether to write Excel files (True) or CSV files (False)
    :param also_json: whether to additionally write a <filename>-extracted.json
                       file alongside the csv/xlsx file, for programmatic consumption
    :param on_progress: optional callback (current, total) called after each file is written
    :return: None
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    extension = "xlsx" if use_excel else "csv"

    for i, (filename, result) in enumerate(results):
        file_path = output_dir / f"{filename}-extracted.{extension}"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        write_extraction_result(result, file_path, use_excel, also_json=also_json)

        if on_progress:
            on_progress(i + 1, len(results))
