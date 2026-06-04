import dspy
from models import Attribute, TypeExpr
from pydantic.fields import FieldInfo

EXTRACTION_SIGNATURE_DOCSTRING = "Extract the attributes from the source where available."


def extraction_signature_builder(
        attrs: list[Attribute]
) -> dspy.Signature:
    fields, annotations = fields_builder(attrs)
    custom_signature = type(
        "CustomSignature",
        (dspy.Signature,),
        fields
    )
    custom_signature.__annotations__ = annotations
    return custom_signature


def fields_builder(
        attrs: list[Attribute]
) -> (dict[str, FieldInfo], dict[str, TypeExpr]):
    fields = {
        "source": dspy.InputField(
            desc="The source to extract attributes from."
        )
    }
    type_hints = {"source": str}
    for attr in attrs:
        fields[attr.name] = dspy.OutputField(desc=attr.description)
        type_hints[attr.name] = attr.attr_type
    return fields, type_hints
