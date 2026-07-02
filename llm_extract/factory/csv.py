from llm_extract.models import CSVData, Attribute
from llm_extract.factory.attribute import build_attribute_from_row


def build_attributes_from_csv(csv_data: CSVData) -> list[Attribute]:
    """
    Build a list of attributes from CSV data.

    :param csv_data: CSVData containing loaded attribute rows
    :return: list of Attribute objects
    :raises AttributeTypeConversionError: if any type expression is invalid
    :raises CannotCreateAttributeWithDisallowedNameError: if any name is disallowed
    :raises LoadingAttributesFromExcelError: if row processing fails
    """
    return [build_attribute_from_row(row) for row in csv_data.rows]
