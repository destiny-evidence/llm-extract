class AttributeTypeConversionError(Exception):
    pass


class LoadingAttributeFromCSVError(Exception):
    pass


class CannotCreateAttributeWithDisallowedNameError(
        Exception
):
    pass
