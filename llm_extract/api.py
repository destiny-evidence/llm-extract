from pathlib import Path

import dspy

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


def extract_folder(
    folder_path: Path,
    attributes: list[Attribute],
    filetypes: list[str],
    with_reasoning: bool = False,
    max_concurrent: int = 8,
    recursive: bool = False,
) -> list[tuple[str, ExtractionResult]]:
    """
    Extract structured attributes from all files in a folder concurrently.

    Processes multiple file types by iterating through provided filetypes,
    collecting results across all matches. Can optionally traverse subdirectories
    recursively while preserving the directory structure in result names.

    :param folder_path: path to folder containing text files
    :param attributes: list of attributes defining what to extract
    :param filetypes: list of file types to extract (e.g., ["txt", "md"])
    :param with_reasoning: whether to use chain-of-thought reasoning
    :param max_concurrent: maximum number of concurrent extractions (default 8)
    :param recursive: whether to recursively traverse subdirectories (default False)
    :return: list of (relative_path, ExtractionResult) tuples, where relative_path
             includes directory structure for recursive extractions
    """
    folder_path = Path(folder_path)
    signature = extraction_signature_builder(attributes)
    extractor = Extract(signature)

    all_results = []
    for filetype in filetypes:
        pattern = f"**/*.{filetype}" if recursive else f"*.{filetype}"
        files = sorted(folder_path.glob(pattern))

        if not files:
            continue

        examples = [
            dspy.Example(
                source=f.read_text(), with_reasoning=with_reasoning
            ).with_inputs("source", "with_reasoning")
            for f in files
        ]

        predictions = extractor.batch(examples, num_threads=max_concurrent)

        all_results.extend(
            [
                (
                    str(f.relative_to(folder_path).with_suffix("")),
                    ExtractionResult(pred, attributes),
                )
                for f, pred in zip(files, predictions)
            ]
        )

    return all_results
