class AttributeTypeConversionError(Exception):
    """Raised when a type string from the CSV cannot be converted to a Python type."""


class LoadingAttributeFromCSVError(Exception):
    """Raised when the attributes CSV cannot be loaded or parsed."""


class CannotCreateAttributeWithDisallowedNameError(Exception):
    """Raised when an attribute uses a reserved name."""
