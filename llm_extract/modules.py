import dspy
from dataclasses import dataclass

NOT_FOUND = "NOT_FOUND"


@dataclass
class ExtractionResult:
    """Wraps a DSPy Prediction with CSV serialisation."""

    prediction: dspy.Prediction

    def to_csv_rows(self) -> list[list]:
        """
        Serialise extraction results to a list of rows ready for csv.writer.

        :return: list of [name, value] rows, with a header row first and an
                 optional [_reasoning_, ...] row last if reasoning was produced
        """
        rows = [["name", "value"]]

        for key in (k for k in self.prediction.keys() if k != "reasoning"):
            value = getattr(self.prediction, key)
            rows.append([key, NOT_FOUND if value is None else value])

        reasoning = getattr(self.prediction, "reasoning", None)
        if reasoning is not None:
            rows.append(["_reasoning_", reasoning])

        return rows

    def display(self) -> None:
        """Print extraction results as an aligned two-column table to stdout."""
        rows = self.to_csv_rows()
        name_width = max(len(str(row[0])) for row in rows)
        for row in rows:
            print(f"{str(row[0]).ljust(name_width)}  {row[1]}")


class Extract(dspy.Module):
    """DSPy module that extracts structured attributes from a source text."""

    def __init__(self, signature: dspy.Signature) -> None:
        self.signature = signature

    def forward(self, source: str, with_reasoning: bool = True) -> dspy.Prediction:
        """
        Run extraction on the source text.

        :param source: the source text to extract attributes from
        :param with_reasoning: whether to use ChainOfThought (True) or Predict (False)
        :return: a DSPy Prediction containing the extracted attribute values
        """
        if with_reasoning:
            extractor = dspy.ChainOfThought(self.signature)
        else:
            extractor = dspy.Predict(self.signature)
        return extractor(source=source)
