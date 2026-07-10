import dataclasses
from pathlib import Path

import dspy

from llm_extract.export import csv as csv_export
from llm_extract.export import excel as excel_export
from llm_extract.export import json as json_export
from llm_extract.models import Attribute


@dataclasses.dataclass
class ExtractionResult:
    """Wraps a DSPy Prediction with CSV, Excel, and JSON serialisation."""

    prediction: dspy.Prediction
    attributes: list[Attribute] = dataclasses.field(default_factory=list)

    def to_csv_rows(self) -> list[list]:
        """
        Serialise extraction results to a list of rows ready for csv.writer.

        :return: list of [name, value] rows, with a header row first and an
                 optional [_reasoning_, ...] row last if reasoning was produced
        """
        return csv_export.to_csv_rows(self.prediction)

    def write_csv(self, path: Path) -> None:
        """
        Write extraction results to a CSV file.

        :param path: destination file path
        """
        csv_export.write_csv(self.prediction, path)

    def to_json(self) -> dict:
        """
        Serialise extraction results to a plain JSON-able dict, preserving the
        full nested structure (no flattening, no JSON-in-a-cell).

        :return: dict mapping each attribute name to its value, with missing
                 values represented as the NOT_FOUND sentinel (matching
                 CSV/Excel), and a "_reasoning_" key if reasoning was produced
        """
        return json_export.to_json(self.prediction, self.attributes)

    def write_json(self, path: Path) -> None:
        """
        Write extraction results to a JSON file, preserving the full nested
        structure so results can be consumed programmatically without
        parsing CSV/Excel.

        :param path: destination file path
        """
        json_export.write_json(self.prediction, self.attributes, path)

    def write_excel(self, path: Path) -> None:
        """
        Write extraction results to an Excel workbook.

        See :func:`llm_extract.export.excel.write_excel` for the full
        sheet-linking layout this produces.

        :param path: destination file path
        """
        excel_export.write_excel(self.prediction, self.attributes, path)
