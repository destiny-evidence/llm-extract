from llm_extract.models import Attribute
from llm_extract.factory import extraction_signature_builder
from llm_extract.modules import Extract, ExtractionResult


def extract(source: str, attributes: list[Attribute]) -> ExtractionResult:
    """
    Extract structured attributes from a source text.

    :param source: the source text to extract attributes from
    :param attributes: list of attributes defining what to extract
    :return: an ExtractionResult wrapping the DSPy Prediction
    """
    signature = extraction_signature_builder(attributes)
    extractor = Extract(signature)
    return ExtractionResult(prediction=extractor(source))
