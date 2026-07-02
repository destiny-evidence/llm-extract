import typing
import pytest
from llm_extract.models import Attribute
from llm_extract.factory import string_to_type
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


def test_string_to_type_literal_unquoted() -> None:
    # Literals must use unquoted identifiers
    assert string_to_type("Literal[a, b]") == typing.Optional[typing.Literal["a", "b"]]
    assert (
        string_to_type("Literal[journal_article, preprint, book]")
        == typing.Optional[typing.Literal["journal_article", "preprint", "book"]]
    )


def test_string_to_type_literal_quoted_raises() -> None:
    # Quoted literals are not allowed - users must remove quotes
    with pytest.raises(ValueError, match="Literal values must not be quoted"):
        string_to_type('Literal["a", "b"]')
    with pytest.raises(ValueError, match="Literal values must not be quoted"):
        string_to_type("Literal['a', 'b']")


def test_string_to_type_literal_values_not_treated_as_identifiers() -> None:
    # Literal values should not be flagged as disallowed types
    assert (
        string_to_type("Literal[datetime]")
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
