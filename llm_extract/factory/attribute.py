from llm_extract.exceptions import (
    AttributeTypeConversionError,
    CannotCreateAttributeWithDisallowedNameError,
)
from llm_extract.factory.type import DISALLOWED_NAMES, build_type_from_string
from llm_extract.models import TypeExpr, Attribute


def build_attribute_from_row(
    row: dict,
    disallowed_names: set[str] = DISALLOWED_NAMES,
    type_context: dict[str, TypeExpr] | None = None,
) -> Attribute:
    """
    Create an Attribute from a row dict with validation.

    :param row: dict with keys 'name', 'type', 'description'
    :param disallowed_names: set of reserved names that cannot be used as attribute names
    :param type_context: extra named types that may be referenced in the type expression
    :return: a validated Attribute instance
    :raises AttributeTypeConversionError: if the type expression is invalid
    :raises CannotCreateAttributeWithDisallowedNameError: if the name is disallowed
    """
    try:
        attr_type = build_type_from_string(row["type"], type_context=type_context)
    except ValueError as exc:
        raise AttributeTypeConversionError(
            f"Couldn't convert attribute type to Python type: {exc}"
        )
    attr_name = row["name"]
    if attr_name in disallowed_names:
        raise CannotCreateAttributeWithDisallowedNameError(
            f"The name: {attr_name} is disallowed, please choose another."
        )
    return Attribute(
        name=row["name"], attr_type=attr_type, description=row["description"]
    )
