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
        from llm_extract.factory import string_to_type

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
