import base64
import re
import string
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import dspy
import pdfplumber


@dataclass
class MixedDocument:
    """Represents a document as a sequence of pages containing text and/or images."""

    pages: list[Union[str, dspy.Image]]
    text_page_count: int = 0
    image_page_count: int = 0


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

    :param text: extracted text from PDF page
    :param min_coverage: minimum ratio of valid characters to total characters
    :param max_whitespace: maximum ratio of whitespace to reject (e.g., 0.8 = 80% whitespace)
    :return: True if text should be used; False if page should be rendered to image
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

    # Heuristic 5: Layout preservation check (detect likely tables/structured content)
    # If we see patterns suggesting structured data (multiple aligned spaces, pipes, etc.),
    # it's safer to use the image to preserve layout
    structured_patterns = [
        r"\|.*\|",  # pipe-delimited columns
        r"---+\s+---+",  # markdown/ASCII tables
        r"^\s{4,}\S+\s{4,}\S+",  # multiple indented columns on same line
    ]
    for pattern in structured_patterns:
        if re.search(pattern, text, re.MULTILINE):
            return False

    return True


def render_page_to_image(page: pdfplumber.PDF, temp_dir: str, dpi: int = 150) -> str:
    """
    Render a pdfplumber page to PNG and return base64 data URL.

    :param page: pdfplumber page object
    :param temp_dir: temporary directory for storing image files
    :param dpi: resolution for rendering (default 150)
    :return: base64 data URL for the rendered image
    """
    image = page.to_image(resolution=dpi)
    image_path = str(Path(temp_dir) / f"page_{page.page_number}.png")
    image.save(image_path)
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{image_data}"


def pdf_to_mixed_document(pdf_path: str | Path) -> MixedDocument:
    """
    Convert a PDF to a MixedDocument containing text and/or images.

    For each page, attempts to extract text. If the extracted text passes
    quality checks, uses it; otherwise renders the page to an image.

    :param pdf_path: path to the PDF file
    :return: MixedDocument with pages and page count metadata
    """
    pdf_path = Path(pdf_path)
    pages: list[Union[str, dspy.Image]] = []
    text_page_count = 0
    image_page_count = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()

                if is_high_quality_text(text):
                    pages.append(text)
                    text_page_count += 1
                else:
                    image_url = render_page_to_image(page, temp_dir)
                    pages.append(dspy.Image(url=image_url))
                    image_page_count += 1

    return MixedDocument(
        pages=pages,
        text_page_count=text_page_count,
        image_page_count=image_page_count,
    )
