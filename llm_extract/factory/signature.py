from typing import Union

import dspy
from pydantic.fields import FieldInfo

from llm_extract.models import Attribute, TypeExpr

EXTRACTION_SIGNATURE_DOCSTRING = (
    "Extract the attributes from the source where available."
)


def build_extraction_signature(
    attrs: list[Attribute], multimodal: bool = False
) -> dspy.Signature:
    """
    Build a DSPy Signature class dynamically from a list of attributes.

    :param attrs: list of attributes defining the output fields
    :param multimodal: if True, source field accepts mixed text/image content
    :return: a DSPy Signature class with typed input and output fields
    """
    fields, annotations = _build_signature_fields(attrs, multimodal=multimodal)
    return type(
        "ExtractAttributesFromSource",
        (dspy.Signature,),
        {
            **fields,
            "__annotations__": annotations,
            "__doc__": EXTRACTION_SIGNATURE_DOCSTRING,
        },
    )


def _build_signature_fields(
    attrs: list[Attribute],
    multimodal: bool = False,
) -> tuple[dict[str, FieldInfo], dict[str, TypeExpr]]:
    """
    Build DSPy input/output fields from a list of attributes.

    :param attrs: list of attributes
    :param multimodal: if True, source field accepts mixed text/image content
    :return: tuple of (fields dict, annotations dict)
    """
    source_type = Union[str, list[Union[str, dspy.Image]]] if multimodal else str
    fields = {
        "source": dspy.InputField(
            description="The source material to extract attributes from."
        )
    }
    annotations = {"source": source_type}

    for attr in attrs:
        fields[attr.name] = dspy.OutputField(description=attr.description)
        annotations[attr.name] = attr.attr_type

    return fields, annotations
