import dspy
from llm_extract.models import Attribute, TypeExpr
from pydantic.fields import FieldInfo

EXTRACTION_SIGNATURE_DOCSTRING = (
    "Extract the attributes from the source where available."
)


def extraction_signature_builder(attrs: list[Attribute]) -> dspy.Signature:
    """
    Build a DSPy Signature class dynamically from a list of attributes.

    :param attrs: list of attributes defining the output fields
    :return: a DSPy Signature class with typed input and output fields
    """
    fields, annotations = fields_builder(attrs)
    return type(
        "ExtractAttributesFromSource",
        (dspy.Signature,),
        {
            **fields,
            "__annotations__": annotations,
            "__doc__": EXTRACTION_SIGNATURE_DOCSTRING,
        },
    )


def fields_builder(
    attrs: list[Attribute],
) -> tuple[dict[str, FieldInfo], dict[str, TypeExpr]]:
    """
    Build DSPy field definitions and type annotations from a list of attributes.

    :param attrs: list of attributes to convert into DSPy fields
    :return: tuple of (fields dict, annotations dict) ready for signature construction
    """
    fields = {"source": dspy.InputField(desc="The source to extract attributes from.")}
    type_hints = {"source": str}
    for attr in attrs:
        fields[attr.name] = dspy.OutputField(desc=attr.description)
        type_hints[attr.name] = attr.attr_type
    return fields, type_hints
