import re
import builtins
import typing
from llm_extract.exceptions import (
    AttributeTypeConversionError,
    CannotCreateAttributeWithDisallowedNameError,
)
from pydantic.dataclasses import dataclass

# TODO could add Optional + Union for more sophisticated types
ALLOWED_TYPES = {
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "tuple",
    "set",
    "None",
    "Literal",
}

TypeExpr = typing.Any


# TODO reconsider wrapping all the types in Optional as a default
def string_to_type(
    string: str, type_context: dict[str, TypeExpr] | None = None
) -> TypeExpr:
    """
    Parse a type expression string into a Python type wrapped in Optional.

    :param string: type expression string, e.g. 'list[int]' or 'float'
    :param type_context: extra named types (e.g. user-defined custom types)
        that may be referenced in the type expression alongside the built-in
        allowed types
    :return: the corresponding Optional-wrapped Python type
    """
    type_context = type_context or {}
    # Strip quoted contents (e.g. Literal["a", "b"]) so literal values aren't
    # mistaken for disallowed type identifiers. Handles both straight and smart quotes.
    without_string_literals = re.sub(
        "['\"\\u201c\\u201d][^'\"]*['\"\\u201c\\u201d]", "", string
    )
    identifiers = set(re.findall(r"[a-zA-Z]\w*", without_string_literals))
    allowed = ALLOWED_TYPES | set(type_context)
    if not identifiers <= allowed:
        raise ValueError(f"Disallowed types: {identifiers - allowed}")
    return eval(
        f"Optional[{string}]", {**vars(typing), **vars(builtins), **type_context}
    )


@dataclass
class Attribute:
    """Represents a single extractable attribute with its name, type, and description."""

    name: str
    attr_type: TypeExpr
    description: str

    @classmethod
    def from_csv_row(
        cls,
        row: dict,
        disallowed_names: set[str] = frozenset(),
        type_context: dict[str, TypeExpr] | None = None,
    ) -> "Attribute":
        """
        Construct an Attribute from a CSV row dict.

        :param row: dict with keys 'name', 'type', 'description'
        :param disallowed_names: set of reserved names that cannot be used as attribute names
        :param type_context: extra named types (e.g. user-defined custom types) that
            may be referenced by the row's 'type' expression
        :return: a validated Attribute instance
        """
        try:
            attr_type = string_to_type(row["type"], type_context=type_context)
        except ValueError as exc:
            raise AttributeTypeConversionError(
                f"Couldn't convert attribute type to Python type: {exc}"
            )
        attr_name = row["name"]
        if attr_name in disallowed_names:
            raise CannotCreateAttributeWithDisallowedNameError(
                f"The name: {attr_name} is disallowed, please choose another."
            )
        return cls(
            name=row["name"], attr_type=attr_type, description=row["description"]
        )
