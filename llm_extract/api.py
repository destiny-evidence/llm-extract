from pathlib import Path
from typing import Union

import dspy

from llm_extract.models import Attribute
from llm_extract.factory import extraction_signature_builder
from llm_extract.export import ExtractionResult
from llm_extract.modules import Extract
from llm_extract.pdf import pdf_to_mixed_document

TEXT_FILETYPES = {"txt", "md"}
MULTIMODAL_FILETYPES = {"pdf"}
SUPPORTED_FILETYPES = TEXT_FILETYPES | MULTIMODAL_FILETYPES


def _load_source(path: Path) -> Union[str, list]:
    """Load source content from file, handling both text and PDF files."""
    if path.suffix.lower() == ".pdf":
        return pdf_to_mixed_document(path).pages
    else:
        return path.read_text()


def extract(
    source: Path, attributes: list[Attribute], with_reasoning: bool = False
) -> ExtractionResult:
    """
    Extract structured attributes from a source file (text or PDF).

    Automatically handles text files (txt, md) and PDFs, converting PDFs
    to mixed text/image representations when needed.

    :param source: path to the source file to extract attributes from
    :param attributes: list of attributes defining what to extract
    :param with_reasoning: whether to use chain-of-thought reasoning
    :return: an ExtractionResult wrapping the DSPy Prediction
    """
    source = Path(source)
    content = _load_source(source)
    is_multimodal = source.suffix.lower() == ".pdf"

    signature = extraction_signature_builder(attributes, multimodal=is_multimodal)
    extractor = Extract(signature)
    return ExtractionResult(
        prediction=extractor(content, with_reasoning=with_reasoning),
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
    collecting results across all matches. Automatically handles text files
    (txt, md) and PDFs, converting PDFs to mixed text/image representations.
    Can optionally traverse subdirectories recursively while preserving
    the directory structure in result names.

    :param folder_path: path to folder containing files
    :param attributes: list of attributes defining what to extract
    :param filetypes: list of file types to extract (e.g., ["txt", "md", "pdf"])
    :param with_reasoning: whether to use chain-of-thought reasoning
    :param max_concurrent: maximum number of concurrent extractions (default 8)
    :param recursive: whether to recursively traverse subdirectories (default False)
    :return: list of (relative_path, ExtractionResult) tuples
    """
    folder_path = Path(folder_path)
    has_pdf = any(ft in MULTIMODAL_FILETYPES for ft in filetypes)

    signature = extraction_signature_builder(attributes, multimodal=has_pdf)
    extractor = Extract(signature)

    all_results = []
    for filetype in filetypes:
        pattern = f"**/*.{filetype}" if recursive else f"*.{filetype}"
        files = sorted(folder_path.glob(pattern))

        if not files:
            continue

        examples = [
            dspy.Example(
                source=_load_source(f), with_reasoning=with_reasoning
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
