import dataclasses
import typing
import dspy
import pytest
from llm_extract.factory import (
    build_attributes_from_sheets,
    extraction_signature_builder,
    fields_builder,
)
from llm_extract.models import Attribute
from llm_extract.exceptions import (
    CircularTypeReferenceError,
    LoadingAttributesFromExcelError,
    UnknownCustomTypeError,
)


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


# --- build_attributes_from_sheets ---


def _row(name: str, type_: str, description: str = "desc") -> dict:
    return {"name": name, "type": type_, "description": description}


def test_build_attributes_from_sheets_simple_types() -> None:
    sheets = {"Study": [_row("title", "str"), _row("year", "int")]}
    attrs = build_attributes_from_sheets(sheets, "Study")
    assert [a.name for a in attrs] == ["title", "year"]
    assert attrs[0].attr_type == typing.Optional[str]
    assert attrs[1].attr_type == typing.Optional[int]


def test_build_attributes_from_sheets_literal_type() -> None:
    # Literal["small", "large"] should not be mistaken for a custom-type
    # sheet reference to a sheet named "small" or "large"
    sheets = {"Study": [_row("size", 'Literal["small", "large"]')]}
    attrs = build_attributes_from_sheets(sheets, "Study")
    assert attrs[0].attr_type == typing.Optional[typing.Literal["small", "large"]]


def test_build_attributes_from_sheets_unknown_root_sheet_raises() -> None:
    with pytest.raises(UnknownCustomTypeError):
        build_attributes_from_sheets({}, "Study")


def test_build_attributes_from_sheets_resolves_custom_type() -> None:
    sheets = {
        "Study": [_row("author", "Author")],
        "Author": [_row("name", "str")],
    }
    attrs = build_attributes_from_sheets(sheets, "Study")
    author_type = typing.get_args(attrs[0].attr_type)[0]
    assert dataclasses.is_dataclass(author_type)
    assert author_type.__name__ == "Author"
    assert [f.name for f in dataclasses.fields(author_type)] == ["name"]


def test_build_attributes_from_sheets_resolves_list_of_custom_type() -> None:
    sheets = {
        "Study": [_row("authors", "list[Author]")],
        "Author": [_row("name", "str")],
    }
    attrs = build_attributes_from_sheets(sheets, "Study")
    list_type = typing.get_args(attrs[0].attr_type)[0]  # unwrap Optional[list[Author]]
    (author_type,) = typing.get_args(list_type)
    assert author_type.__name__ == "Author"


def test_build_attributes_from_sheets_memoizes_shared_type() -> None:
    sheets = {
        "Study": [_row("a", "TypeA"), _row("b", "TypeB")],
        "TypeA": [_row("shared", "Shared")],
        "TypeB": [_row("shared", "Shared")],
        "Shared": [_row("value", "str")],
    }
    attrs = build_attributes_from_sheets(sheets, "Study")
    type_a = typing.get_args(attrs[0].attr_type)[0]
    type_b = typing.get_args(attrs[1].attr_type)[0]
    shared_from_a = typing.get_args(dataclasses.fields(type_a)[0].type)[0]
    shared_from_b = typing.get_args(dataclasses.fields(type_b)[0].type)[0]
    assert shared_from_a is shared_from_b


def test_build_attributes_from_sheets_self_reference_raises() -> None:
    sheets = {"Study": [_row("self", "Study")]}
    with pytest.raises(CircularTypeReferenceError):
        build_attributes_from_sheets(sheets, "Study")


def test_build_attributes_from_sheets_circular_reference_raises() -> None:
    sheets = {
        "A": [_row("b", "B")],
        "B": [_row("a", "A")],
    }
    with pytest.raises(CircularTypeReferenceError):
        build_attributes_from_sheets(sheets, "A")


def test_build_attributes_from_sheets_unknown_type_raises() -> None:
    sheets = {"Study": [_row("x", "Bogus")]}
    with pytest.raises(UnknownCustomTypeError):
        build_attributes_from_sheets(sheets, "Study")


def test_build_attributes_from_sheets_disallowed_root_name_raises() -> None:
    sheets = {"Study": [_row("source", "str")]}
    with pytest.raises(LoadingAttributesFromExcelError):
        build_attributes_from_sheets(sheets, "Study")


def test_build_attributes_from_sheets_allows_disallowed_name_in_nested_type() -> None:
    sheets = {
        "Study": [_row("author", "Author")],
        "Author": [_row("source", "str")],
    }
    attrs = build_attributes_from_sheets(sheets, "Study")
    author_type = typing.get_args(attrs[0].attr_type)[0]
    assert [f.name for f in dataclasses.fields(author_type)] == ["source"]
