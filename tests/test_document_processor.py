"""Unit tests for document_processor module."""

from pathlib import Path

import pytest

from llm_extract.document_processor import (
    is_high_quality_text,
)
from llm_extract.models import MixedDocument


class TestQualityHeuristics:
    """Test quality heuristics for text validation."""

    def test_good_text_passes(self):
        """Well-formed text should pass quality checks."""
        text = (
            "This is a well-formed document with proper English text and punctuation."
        )
        assert is_high_quality_text(text) is True

    def test_very_short_text_fails(self):
        """Text below minimum length should fail."""
        assert is_high_quality_text("Hi") is False
        assert is_high_quality_text("") is False

    def test_whitespace_heavy_text_fails(self):
        """Text with >80% whitespace should fail."""
        text = "word\n\n\n\n\n" + " " * 100
        assert is_high_quality_text(text) is False

    def test_gibberish_text_fails(self):
        """Text with high control character ratio should fail."""
        text = "hello\x00\x01\x02world\x03\x04\x05" * 10
        assert is_high_quality_text(text) is False

    def test_markdown_tables_trigger_fallback(self):
        """Markdown tables should be flagged for image rendering."""
        text = "| Header 1 | Header 2 |\n| --- | --- |\n| Cell 1 | Cell 2 |"
        assert is_high_quality_text(text) is False

    def test_nonsensical_word_length_fails(self):
        """Text with abnormal word lengths should fail."""
        # Very short words (avg < 2 chars)
        text = "a b c d e f g h i j" * 10
        assert is_high_quality_text(text) is False

        # Very long words (avg > 20 chars)
        long_word = "x" * 30
        text = f"{long_word} " * 10
        assert is_high_quality_text(text) is False


class TestMixedDocumentStructure:
    """Test MixedDocument dataclass structure."""

    def test_mixed_document_creation(self):
        """MixedDocument should be creatable with required fields."""
        doc = MixedDocument(
            pages=["page 1", "page 2"],
            text_page_count=2,
            image_page_count=0,
        )

        assert doc.text_page_count == 2
        assert doc.image_page_count == 0
        assert len(doc.pages) == 2

    def test_mixed_document_defaults(self):
        """MixedDocument should have sensible defaults."""
        doc = MixedDocument(pages=["content"])

        assert doc.text_page_count == 0
        assert doc.image_page_count == 0

    def test_page_counts_consistency(self):
        """Total pages should equal sum of text and image pages."""
        doc = MixedDocument(
            pages=["text", "image", "text"],
            text_page_count=2,
            image_page_count=1,
        )

        assert doc.text_page_count + doc.image_page_count == len(doc.pages)
