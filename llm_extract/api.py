from llm_extract.models import Attribute
from llm_extract.factory import extraction_signature_builder
from llm_extract.export import ExtractionResult
from llm_extract.modules import Extract


def extract(
    source: str, attributes: list[Attribute], with_reasoning: bool = False
) -> ExtractionResult:
    """
    Extract structured attributes from a source text.

    :param source: the source text to extract attributes from
    :param attributes: list of attributes defining what to extract
    :param with_reasoning: whether to use chain-of-thought reasoning
    :return: an ExtractionResult wrapping the DSPy Prediction
    """
    signature = extraction_signature_builder(attributes)
    extractor = Extract(signature)
    return ExtractionResult(
        prediction=extractor(source, with_reasoning=with_reasoning),
        attributes=attributes,
    )
