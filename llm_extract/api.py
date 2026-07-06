from pathlib import Path
from typing import Callable

import dspy

from llm_extract.loader import load_source, MULTIMODAL_FILETYPES
from llm_extract.models import Attribute, ExtractionStage, MixedDocument
from llm_extract.factory import build_extraction_signature
from llm_extract.export import ExtractionResult
from llm_extract.modules import Extract

try:
    from openai import APITimeoutError
except ImportError:
    APITimeoutError = TimeoutError  # fallback for other API providers


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

        try:
            prediction = extractor(content, with_reasoning=with_reasoning)
        except APITimeoutError as e:
            timeout_msg = (
                f"LLM extraction timed out after the configured timeout period. "
                f"This often happens with large documents and many extraction fields. "
                f"Try: (1) reducing the number of fields, (2) increasing LLM_EXTRACT_TIMEOUT "
                f"environment variable, or (3) splitting the document into smaller chunks."
            )
            raise TimeoutError(timeout_msg) from e

        result = ExtractionResult(
            prediction=prediction,
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
    on_progress: Callable[[str, int, int], None] | None = None,
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
    :param on_progress: optional callback (stage, current, total) for progress updates
    :return: list of (relative_path, ExtractionResult) tuples
    """
    folder_path = Path(folder_path)
    has_multimodal = any(ft in MULTIMODAL_FILETYPES for ft in filetypes)

    signature = build_extraction_signature(attributes, multimodal=has_multimodal)
    extractor = Extract(signature)

    all_results = []
    all_failures = []

    for filetype in filetypes:
        pattern = f"**/*.{filetype}" if recursive else f"*.{filetype}"
        files = sorted(folder_path.glob(pattern))

        if not files:
            continue

        # Load sources with progress
        # Create examples in order (DSPy batch preserves order, so index[i] corresponds to files[i])
        examples = []
        for i, f in enumerate(files):
            if on_progress:
                on_progress("loading_source", i, len(files))
            source = load_source(f)
            if isinstance(source, MixedDocument):
                source = source.pages
            examples.append(
                dspy.Example(source=source, with_reasoning=with_reasoning).with_inputs(
                    "source", "with_reasoning"
                )
            )

        # Batch processing (show progress bar only if on_progress callback is provided)
        predictions, failed_examples, exceptions = extractor.batch(
            examples,
            num_threads=max_concurrent,
            disable_progress_bar=(on_progress is None),
            return_failed_examples=True,
        )

        # Map results back using natural index correspondence
        failed_indices = {examples.index(ex) for ex in failed_examples}
        successful_count = 0

        for i, example in enumerate(examples):
            if i not in failed_indices:
                f = files[i]
                all_results.append(
                    (
                        str(f.relative_to(folder_path).with_suffix("")),
                        ExtractionResult(predictions[successful_count], attributes),
                    )
                )
                successful_count += 1
            else:
                # Track this failure
                f = files[i]
                exc_idx = failed_examples.index(example)
                all_failures.append(
                    (
                        str(f.relative_to(folder_path)),
                        exceptions[exc_idx],
                    )
                )

    # If there were failures, raise an exception with details
    if all_failures:
        failure_msg = "Extraction failed for the following files:\n"
        for filepath, exc in all_failures:
            error_type = type(exc).__name__
            error_msg = str(exc)
            failure_msg += f"  • {filepath}: {error_type}: {error_msg}\n"
        raise RuntimeError(failure_msg.rstrip())

    return all_results
