import typing
from pathlib import Path

import dspy
import pytest
from llm_extract.config import configure_dspy
from llm_extract.loader import load_attributes_csv
from llm_extract.factory import extraction_signature_builder
from llm_extract.modules import Extract

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def extractor():
    configure_dspy()
    attrs = load_attributes_csv(FIXTURES / "attributes.csv")
    signature = extraction_signature_builder(attrs)
    return Extract(signature)


@pytest.fixture(scope="module")
def source_text():
    with open(FIXTURES / "sample.txt") as f:
        return f.read()


def test_can_extract_attributes_correctly(extractor, source_text):
    results = extractor(source_text)
    attrs = load_attributes_csv(FIXTURES / "attributes.csv")

    assert isinstance(results, dspy.Prediction)
    for attr in attrs:
        value = getattr(results, attr.name)
        if value is None:
            continue
        inner_type = typing.get_args(attr.attr_type)[0]  # unwrap Optional[X] -> X
        origin = typing.get_origin(inner_type)
        if origin is list:
            assert isinstance(value, list), f"{attr.name}: expected list"
            (elem_type,) = typing.get_args(inner_type)
            assert all(isinstance(e, elem_type) for e in value), (
                f"{attr.name}: expected all elements to be {elem_type}"
            )
        else:
            check_type = origin if origin is not None else inner_type
            assert isinstance(value, check_type), (
                f"{attr.name}: expected {inner_type}, got {type(value)}"
            )
