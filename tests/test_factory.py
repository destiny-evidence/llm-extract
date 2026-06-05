import typing
import dspy
import pytest
from llm_extract.factory import extraction_signature_builder, fields_builder
from llm_extract.models import Attribute


@pytest.fixture
def sample_attrs() -> list[Attribute]:
    return [
        Attribute(
            name="product_name",
            attr_type=typing.Optional[str],
            description="Name of product",
        ),
        Attribute(
            name="price", attr_type=typing.Optional[float], description="Price in USD"
        ),
    ]


def test_fields_builder_always_includes_source(sample_attrs: list[Attribute]) -> None:
    fields, annotations = fields_builder(sample_attrs)
    assert "source" in fields
    assert annotations["source"] is str


def test_fields_builder_output_fields_match_attrs(
    sample_attrs: list[Attribute],
) -> None:
    fields, annotations = fields_builder(sample_attrs)
    assert "product_name" in fields
    assert "price" in fields
    assert annotations["product_name"] == typing.Optional[str]
    assert annotations["price"] == typing.Optional[float]


def test_fields_builder_empty_attrs_yields_only_source() -> None:
    fields, annotations = fields_builder([])
    assert list(fields.keys()) == ["source"]
    assert list(annotations.keys()) == ["source"]


def test_fields_builder_field_count(sample_attrs: list[Attribute]) -> None:
    fields, _ = fields_builder(sample_attrs)
    assert len(fields) == 1 + len(sample_attrs)


def test_extraction_signature_builder_returns_signature_subclass(
    sample_attrs: list[Attribute],
) -> None:
    sig = extraction_signature_builder(sample_attrs)
    assert issubclass(sig, dspy.Signature)


def test_extraction_signature_builder_has_output_fields(
    sample_attrs: list[Attribute],
) -> None:
    sig = extraction_signature_builder(sample_attrs)
    assert "product_name" in sig.output_fields
    assert "price" in sig.output_fields


def test_extraction_signature_builder_has_source_input_field(
    sample_attrs: list[Attribute],
) -> None:
    sig = extraction_signature_builder(sample_attrs)
    assert "source" in sig.input_fields
