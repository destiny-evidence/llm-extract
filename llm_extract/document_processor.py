import base64
import re
import string
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import dspy
import markitdown
from PIL import Image as PILImage


@dataclass
class MixedDocument:
    """Represents a document as a sequence of pages containing text and/or images."""

    pages: list[Union[str, dspy.Image]]
    text_page_count: int = 0
    image_page_count: int = 0
    source_type: str = "unknown"


def is_high_quality_text(
    text: str, min_coverage: float = 0.15, max_whitespace: float = 0.8
) -> bool:
    """
    Assess if extracted text is of sufficient quality to use directly.

    Applies multiple heuristics to detect extraction failures:
    - Character coverage: ensures text isn't mostly gibberish
    - Control character ratio: detects encoding issues or OCR artifacts
    - Word length statistics: flags nonsensical character sequences
    - Whitespace ratio: detects mostly-blank pages or diagram-heavy content

    :param text: extracted text from document
    :param min_coverage: minimum ratio of valid characters to total characters
    :param max_whitespace: maximum ratio of whitespace to reject (e.g., 0.8 = 80% whitespace)
    :return: True if text should be used; False if fallback to image is needed
    """
    if not text or len(text.strip()) < 10:
        return False

    # Heuristic 1: Character coverage (gibberish detection)
    total_chars = len(text)
    valid_chars = sum(
        1 for c in text if c.isalnum() or c.isspace() or c in string.punctuation
    )
    coverage = valid_chars / total_chars if total_chars > 0 else 0
    if coverage < min_coverage:
        return False

    # Heuristic 2: Control character ratio (encoding issues)
    control_chars = sum(1 for c in text if ord(c) < 32 and c not in "\n\t\r")
    if control_chars / total_chars > 0.1:
        return False

    # Heuristic 3: Word length validation (nonsense detection)
    words = text.split()
    if len(words) > 5:
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len < 2 or avg_word_len > 20:
            return False

    # Heuristic 4: Whitespace ratio (blank/diagram-heavy pages)
    whitespace_chars = sum(1 for c in text if c.isspace())
    whitespace_ratio = whitespace_chars / total_chars if total_chars > 0 else 0
    if whitespace_ratio > max_whitespace:
        return False

    # Heuristic 5: Markdown table detection (preserve layout)
    # Markdown tables are better handled as images to preserve structure
    if "|" in text and re.search(r"\|.*\|", text):
        return False

    return True


def file_to_image_url(
    file_path: Path, page_num: int | None = None, temp_dir: str | None = None
) -> str:
    """
    Convert a document or image file to base64 data URL.

    :param file_path: path to the file
    :param page_num: page number (for logging/naming)
    :param temp_dir: temporary directory to store rendered image
    :return: base64 data URL for the image
    """
    if temp_dir is None:
        temp_dir = tempfile.gettempdir()

    # If it's already an image, just encode it
    if file_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/{file_path.suffix.lstrip('.')};base64,{image_data}"

    # Otherwise render document to image using Pillow
    try:
        img = PILImage.open(str(file_path))
        image_path = Path(temp_dir) / f"page_{page_num or 1}.png"
        img.save(image_path, "PNG")
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{image_data}"
    except Exception as e:
        raise ValueError(f"Could not render {file_path} to image: {e}")


def document_to_mixed(file_path: str | Path) -> MixedDocument:
    """
    Convert a document to a MixedDocument containing text and/or images.

    Uses markitdown for text extraction. If extraction quality is low, falls
    back to rendering the document as images.

    :param file_path: path to the document file
    :return: MixedDocument with pages and metadata
    """
    file_path = Path(file_path)

    # Extract using markitdown
    try:
        converter = markitdown.MarkItDown()
        result = converter.convert_local(str(file_path))
        md_content = result.text_content
    except Exception as e:
        raise ValueError(f"Failed to extract {file_path}: {e}")

    pages: list[Union[str, dspy.Image]] = []
    text_page_count = 0
    image_page_count = 0

    # Markitdown converts entire document to markdown in one go
    # (already handles multi-page documents)
    if is_high_quality_text(md_content):
        pages.append(md_content)
        text_page_count = 1
    else:
        # Fall back to rendering as image
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                image_url = file_to_image_url(file_path, page_num=1, temp_dir=temp_dir)
                pages.append(dspy.Image(url=image_url))
                image_page_count = 1
            except ValueError:
                # If rendering fails, use markdown anyway (better than nothing)
                pages.append(md_content)
                text_page_count = 1

    return MixedDocument(
        pages=pages,
        text_page_count=text_page_count,
        image_page_count=image_page_count,
        source_type=file_path.suffix.lstrip(".").lower(),
    )
