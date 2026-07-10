import csv
from pathlib import Path

import dspy

from llm_extract.export.common import format_value


def to_csv_rows(prediction: dspy.Prediction) -> list[list]:
    """
    Serialise a prediction to a list of rows ready for csv.writer.

    :param prediction: the DSPy Prediction holding the extracted values
    :return: list of [name, value] rows, with a header row first and an
             optional [_reasoning_, ...] row last if reasoning was produced
    """
    rows = [["name", "value"]]

    for key in (k for k in prediction.keys() if k != "reasoning"):
        value = getattr(prediction, key)
        rows.append([key, format_value(value)])

    reasoning = getattr(prediction, "reasoning", None)
    if reasoning is not None:
        rows.append(["_reasoning_", reasoning])

    return rows


def write_csv(prediction: dspy.Prediction, path: Path) -> None:
    """
    Write a prediction's results to a CSV file.

    :param prediction: the DSPy Prediction holding the extracted values
    :param path: destination file path
    """
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(to_csv_rows(prediction))
