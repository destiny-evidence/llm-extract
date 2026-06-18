import typing
import pytest
from llm_extract.models import Attribute, string_to_type
from llm_extract.exceptions import (
    AttributeTypeConversionError,
    CannotCreateAttributeWithDisallowedNameError,
)


# --- string_to_type ---


def test_string_to_type_simple() -> None:
    assert string_to_type("str") == typing.Optional[str]


def test_string_to_type_numeric() -> None:
    assert string_to_type("int") == typing.Optional[int]
    assert string_to_type("float") == typing.Optional[float]


def test_string_to_type_bool() -> None:
    assert string_to_type("bool") == typing.Optional[bool]


def test_string_to_type_generic_list() -> None:
    assert string_to_type("list[str]") == typing.Optional[list[str]]
    assert string_to_type("list[int]") == typing.Optional[list[int]]


def test_string_to_type_union_types_are_accepted() -> None:
    # | passes the allowlist check (only identifiers are validated),
    # so union types silently succeed rather than raising
    assert string_to_type("str | int") == typing.Optional[str | int]
    assert string_to_type("str|int") == typing.Optional[str | int]
    assert string_to_type("int | float") == typing.Optional[int | float]
    assert string_to_type("str | int | float") == typing.Optional[str | int | float]


def test_string_to_type_literal() -> None:
    assert (
        string_to_type('Literal["a", "b"]') == typing.Optional[typing.Literal["a", "b"]]
    )
    assert (
        string_to_type("Literal['a', 'b']") == typing.Optional[typing.Literal["a", "b"]]
    )


def test_string_to_type_literal_values_not_treated_as_identifiers() -> None:
    # 'datetime' would be disallowed as a bare identifier, but here it's a
    # quoted literal value, so it should not be flagged
    assert (
        string_to_type('Literal["datetime"]')
        == typing.Optional[typing.Literal["datetime"]]
    )


def test_string_to_type_disallowed_identifier_raises() -> None:
    with pytest.raises(ValueError, match="Disallowed types"):
        string_to_type("datetime")


def test_string_to_type_module_access_raises() -> None:
    with pytest.raises(ValueError, match="Disallowed types"):
        string_to_type("os.system")


def test_string_to_type_import_attempt_raises() -> None:
    with pytest.raises(ValueError, match="Disallowed types"):
        string_to_type("str; import os")


# --- Attribute.from_csv_row ---


def _csv_row(
    name: str = "price", type_: str = "float", desc: str = "The price"
) -> dict:
    return {"name": name, "type": type_, "description": desc}


def test_attribute_from_csv_row_valid() -> None:
    attr = Attribute.from_csv_row(_csv_row())
    assert attr.name == "price"
    assert attr.attr_type == typing.Optional[float]
    assert attr.description == "The price"


def test_attribute_from_csv_row_complex_type() -> None:
    attr = Attribute.from_csv_row(_csv_row(type_="list[str]"))
    assert attr.attr_type == typing.Optional[list[str]]


def test_attribute_from_csv_row_disallowed_name_raises() -> None:
    with pytest.raises(CannotCreateAttributeWithDisallowedNameError):
        Attribute.from_csv_row(_csv_row(name="source"), disallowed_names={"source"})


def test_attribute_from_csv_row_allowed_when_not_in_disallowed_set() -> None:
    attr = Attribute.from_csv_row(_csv_row(name="source"), disallowed_names=set())
    assert attr.name == "source"


def test_attribute_from_csv_row_invalid_type_raises() -> None:
    with pytest.raises(AttributeTypeConversionError):
        Attribute.from_csv_row(_csv_row(type_="pathlib.Path"))
