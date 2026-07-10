import json
from pathlib import Path

import dspy
from pydantic_core import to_jsonable_python

from llm_extract.export.common import apply_not_found_sentinel
from llm_extract.models import Attribute


def to_json(prediction: dspy.Prediction, attributes: list[Attribute]) -> dict:
    """
    Serialise a prediction to a plain JSON-able dict, preserving the full
    nested structure (no flattening, no JSON-in-a-cell).

    :param prediction: the DSPy Prediction holding the extracted values
    :param attributes: the attribute definitions extracted, used for their names
    :return: dict mapping each attribute name to its value, converted via
             `to_jsonable_python` (handles our pydantic-dataclass-based
             custom types, which `Prediction.toDict()` does not - it only
             recognises genuine `pydantic.BaseModel` instances). Missing
             values are the NOT_FOUND sentinel, matching CSV/Excel, applied
             at any nesting depth (e.g. a null field inside a custom type,
             or a missing custom-type attribute). Includes a "_reasoning_"
             key if reasoning was produced.
    """
    keys = [attr.name for attr in attributes] or [
        k for k in prediction.keys() if k != "reasoning"
    ]
    result = {
        key: apply_not_found_sentinel(
            to_jsonable_python(getattr(prediction, key, None))
        )
        for key in keys
    }

    reasoning = getattr(prediction, "reasoning", None)
    if reasoning is not None:
        result["_reasoning_"] = reasoning

    return result


def write_json(
    prediction: dspy.Prediction, attributes: list[Attribute], path: Path
) -> None:
    """
    Write a prediction's results to a JSON file, preserving the full nested
    structure so results can be consumed programmatically without parsing
    CSV/Excel.

    :param prediction: the DSPy Prediction holding the extracted values
    :param attributes: the attribute definitions extracted, used for their names
    :param path: destination file path
    """
    with path.open("w") as f:
        json.dump(to_json(prediction, attributes), f, indent=2)
