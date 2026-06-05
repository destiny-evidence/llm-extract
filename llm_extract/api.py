import dspy
from llm_extract.models import Attribute
from llm_extract.factory import extraction_signature_builder
from llm_extract.modules import Extract


def extract(source: str, attributes: list[Attribute]) -> dspy.Prediction:
    """
    Extract structured attributes from a source text.

    :param source: the source text to extract attributes from
    :param attributes: list of attributes defining what to extract
    :return: a DSPy Prediction containing the extracted attribute values
    """
    signature = extraction_signature_builder(attributes)
    extractor = Extract(signature)
    return extractor(source)
