import re
import builtins
import typing
from llm_extract.exceptions import (
    AttributeTypeConversionError,
    CannotCreateAttributeWithDisallowedNameError,
)
from pydantic.dataclasses import dataclass

# TODO could add Optional + Union for more sophisticated types
ALLOWED_TYPES = {"str", "int", "float", "bool", "list", "dict", "tuple", "set", "None"}

TypeExpr = typing.Any


# TODO reconsider wrapping all the types in Optional as a default
def string_to_type(string: str) -> TypeExpr:
    """
    Parse a type expression string into a Python type wrapped in Optional.

    :param string: type expression string, e.g. 'list[int]' or 'float'
    :return: the corresponding Optional-wrapped Python type
    """
    identifiers = set(re.findall(r"[a-zA-Z]\w*", string))
    if not identifiers <= ALLOWED_TYPES:
        raise ValueError(f"Disallowed types: {identifiers - ALLOWED_TYPES}")
    return eval(f"Optional[{string}]", {**vars(typing), **vars(builtins)})


@dataclass
class Attribute:
    """Represents a single extractable attribute with its name, type, and description."""

    name: str
    attr_type: TypeExpr
    description: str

    @classmethod
    def from_csv_row(
        cls, row: dict, disallowed_names: set[str] = frozenset()
    ) -> "Attribute":
        """
        Construct an Attribute from a CSV row dict.

        :param row: dict with keys 'name', 'type', 'description'
        :param disallowed_names: set of reserved names that cannot be used as attribute names
        :return: a validated Attribute instance
        """
        try:
            attr_type = string_to_type(row["type"])
        except ValueError as exc:
            raise AttributeTypeConversionError(
                f"Couldn't convert attribute type to Python type: {exc}"
            )
        attr_name = row["name"]
        if attr_name in disallowed_names:
            raise CannotCreateAttributeWithDisallowedNameError(
                f"The name: {attr_name} is disallowed, pleas choose another."
            )
        return cls(
            name=row["name"], attr_type=attr_type, description=row["description"]
        )
