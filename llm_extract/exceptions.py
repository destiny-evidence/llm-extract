class AttributeTypeConversionError(Exception):
    """Raised when a type string from the CSV cannot be converted to a Python type."""


class LoadingAttributeFromCSVError(Exception):
    """Raised when the attributes CSV cannot be loaded or parsed."""


class CannotCreateAttributeWithDisallowedNameError(Exception):
    """Raised when an attribute uses a reserved name."""


class MissingEnvironmentVariablesError(Exception):
    """Raised when one or more required environment variables are not set after loading .env sources."""


class UnknownCustomTypeError(Exception):
    """Raised when a type references a sheet/custom type that cannot be found."""


class CircularTypeReferenceError(Exception):
    """Raised when custom types reference each other in a circular chain."""


class LoadingAttributesFromExcelError(Exception):
    """Raised when attributes cannot be loaded or parsed from an Excel workbook."""
