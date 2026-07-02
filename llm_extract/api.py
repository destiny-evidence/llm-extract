from pathlib import Path
from typing import Callable

import dspy

from llm_extract.loader import load_source
from llm_extract.models import Attribute, ExtractionStage
from llm_extract.factory import build_extraction_signature
from llm_extract.export import ExtractionResult
from llm_extract.modules import Extract

TEXT_FILETYPES = {"txt", "md", "html"}
MULTIMODAL_FILETYPES = {"pdf"}
SUPPORTED_FILETYPES = TEXT_FILETYPES | MULTIMODAL_FILETYPES


def extract(
    source: Path,
    attributes: list[Attribute],
    with_reasoning: bool = False,
    on_progress: Callable[
        [ExtractionStage, Path, ExtractionResult | None, Exception | None], None
    ]
    | None = None,
) -> ExtractionResult:
    """
    Extract structured attributes from a source file (text or PDF).

    Automatically handles text files (txt, md, html) and PDFs, converting PDFs
    to mixed text/image representations (text for readable pages, images for
    complex layouts like diagrams and tables).

    :param source: path to the source file to extract attributes from
    :param attributes: list of attributes defining what to extract
    :param with_reasoning: whether to use chain-of-thought reasoning
    :param on_progress: optional callback for progress updates. Called with:
                       (stage, source, result=None, error=None) where stage is an ExtractionStage
    :return: an ExtractionResult wrapping the DSPy Prediction
    """
    source = Path(source)
    is_multimodal = source.suffix.lower().lstrip(".") in MULTIMODAL_FILETYPES

    try:
        if on_progress:
            on_progress(ExtractionStage.LOADING_SOURCE, source)

        content = load_source(source)

        if on_progress:
            if is_multimodal:
                on_progress(ExtractionStage.TRANSFORMING_PDF, source)
            else:
                on_progress(ExtractionStage.SOURCE_LOADED, source)

        if on_progress:
            on_progress(ExtractionStage.EXTRACTING, source)

        signature = build_extraction_signature(attributes, multimodal=is_multimodal)
        extractor = Extract(signature)
        result = ExtractionResult(
            prediction=extractor(content, with_reasoning=with_reasoning),
            attributes=attributes,
        )

        if on_progress:
            on_progress(ExtractionStage.COMPLETED, source, result=result)

        return result
    except Exception as exc:
        if on_progress:
            on_progress(ExtractionStage.COMPLETED, source, error=exc)
        raise


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
    (txt, md, html) and PDFs, converting PDFs to mixed text/image representations.
    Can optionally traverse subdirectories recursively while preserving the
    directory structure in result names.

    :param folder_path: path to folder containing files
    :param attributes: list of attributes defining what to extract
    :param filetypes: list of file types to extract (e.g., ["txt", "md", "pdf"])
    :param with_reasoning: whether to use chain-of-thought reasoning
    :param max_concurrent: maximum number of concurrent extractions (default 8)
    :param recursive: whether to recursively traverse subdirectories (default False)
    :return: list of (relative_path, ExtractionResult) tuples
    """
    folder_path = Path(folder_path)
    has_multimodal = any(ft in MULTIMODAL_FILETYPES for ft in filetypes)

    signature = build_extraction_signature(attributes, multimodal=has_multimodal)
    extractor = Extract(signature)

    all_results = []
    for filetype in filetypes:
        pattern = f"**/*.{filetype}" if recursive else f"*.{filetype}"
        files = sorted(folder_path.glob(pattern))

        if not files:
            continue

        examples = [
            dspy.Example(
                source=load_source(f), with_reasoning=with_reasoning
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
