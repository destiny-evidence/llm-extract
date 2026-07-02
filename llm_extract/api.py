from pathlib import Path
from typing import Callable

import dspy

from llm_extract.loader import load_source, MULTIMODAL_FILETYPES
from llm_extract.models import Attribute, ExtractionStage, MixedDocument
from llm_extract.factory import build_extraction_signature
from llm_extract.export import ExtractionResult
from llm_extract.modules import Extract


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

        content_or_doc = load_source(source)
        if isinstance(content_or_doc, MixedDocument):
            content = content_or_doc.pages
        else:
            content = content_or_doc

        if on_progress:
            if is_multimodal:
                on_progress(
                    ExtractionStage.TRANSFORMING_PDF, source, doc=content_or_doc
                )
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

        examples = []
        for f in files:
            source = load_source(f)
            if isinstance(source, MixedDocument):
                source = source.pages
            examples.append(
                dspy.Example(source=source, with_reasoning=with_reasoning).with_inputs(
                    "source", "with_reasoning"
                )
            )

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
