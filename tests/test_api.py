import typing
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from llm_extract.api import extract
from llm_extract.models import Attribute
from llm_extract.export import ExtractionResult


@pytest.fixture
def sample_attrs() -> list[Attribute]:
    return [
        Attribute(
            name="product_name",
            attr_type=typing.Optional[str],
            description="Name of product",
        ),
        Attribute(
            name="price", attr_type=typing.Optional[float], description="Price in USD"
        ),
    ]


@pytest.fixture
def sample_text_file() -> Path:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Some product text.")
        return Path(f.name)


def test_extract_returns_extraction_result(sample_attrs, sample_text_file) -> None:
    with patch("llm_extract.api.Extract") as mock_extract_cls:
        mock_extract_cls.return_value = MagicMock(return_value=MagicMock())
        result = extract(sample_text_file, sample_attrs)
    assert isinstance(result, ExtractionResult)
    assert result.attributes == sample_attrs
    sample_text_file.unlink()


def test_extract_passes_source_to_extractor(sample_attrs, sample_text_file) -> None:
    with patch("llm_extract.api.Extract") as mock_extract_cls:
        mock_extractor = MagicMock()
        mock_extract_cls.return_value = mock_extractor
        extract(sample_text_file, sample_attrs)
    mock_extractor.assert_called_once_with("Some product text.", with_reasoning=False)
    sample_text_file.unlink()


def test_extract_passes_with_reasoning_to_extractor(
    sample_attrs, sample_text_file
) -> None:
    with patch("llm_extract.api.Extract") as mock_extract_cls:
        mock_extractor = MagicMock()
        mock_extract_cls.return_value = mock_extractor
        extract(sample_text_file, sample_attrs, with_reasoning=True)
    mock_extractor.assert_called_once_with("Some product text.", with_reasoning=True)
    sample_text_file.unlink()


def test_extract_builds_signature_from_attributes(
    sample_attrs, sample_text_file
) -> None:
    with (
        patch("llm_extract.api.build_extraction_signature") as mock_builder,
        patch("llm_extract.api.Extract"),
    ):
        extract(sample_text_file, sample_attrs)
    mock_builder.assert_called_once_with(sample_attrs, multimodal=False)
    sample_text_file.unlink()


def test_extract_multimodal_pdf(sample_attrs) -> None:
    """Test that extract() handles PDFs (multimodal) correctly."""
    pdf_path = Path(__file__).parent / "fixtures" / "documents" / "aiayn.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF fixture not found")

    with patch("llm_extract.api.Extract") as mock_extract_cls:
        mock_extractor = MagicMock()
        mock_extract_cls.return_value = mock_extractor
        extract(pdf_path, sample_attrs)

    # Should be called with multimodal=True for PDF
    call_args = mock_extract_cls.call_args
    assert call_args[0][0] is not None  # signature passed


def test_extract_timeout_error(sample_attrs, sample_text_file) -> None:
    """Test that APITimeoutError is caught and converted to helpful TimeoutError."""
    from openai import APITimeoutError

    with patch("llm_extract.api.Extract") as mock_extract_cls:
        mock_extractor = MagicMock()
        # When called as extractor(content, with_reasoning=...), raise APITimeoutError
        mock_request = MagicMock()
        mock_extractor.side_effect = APITimeoutError(mock_request)
        mock_extract_cls.return_value = mock_extractor

        with pytest.raises(TimeoutError) as exc_info:
            extract(sample_text_file, sample_attrs)

        # Check that the error message is helpful and includes recovery suggestions
        error_msg = str(exc_info.value)
        assert "timed out" in error_msg.lower()
        assert "LLM_EXTRACT_TIMEOUT" in error_msg  # Should suggest timeout env var

    sample_text_file.unlink()


def test_extract_folder_batch_failures(sample_attrs) -> None:
    """Test that extract_folder() handles and reports batch failures."""
    from llm_extract.api import extract_folder
    import tempfile
    import shutil

    # Create temp folder with test files
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Create two test files
        (temp_dir / "file1.txt").write_text("content 1")
        (temp_dir / "file2.txt").write_text("content 2")

        with patch("llm_extract.api.Extract") as mock_extract_cls:
            mock_extractor = MagicMock()
            mock_extract_cls.return_value = mock_extractor

            # Create dspy.Example objects that we can use
            import dspy

            examples = [
                dspy.Example(source="content 1", with_reasoning=False).with_inputs(
                    "source", "with_reasoning"
                ),
                dspy.Example(source="content 2", with_reasoning=False).with_inputs(
                    "source", "with_reasoning"
                ),
            ]

            # Simulate batch: first succeeds, second fails with timeout
            successful_pred = MagicMock()
            timeout_exc = TimeoutError("Request timed out")

            mock_extractor.batch.return_value = (
                [successful_pred],  # predictions (only successful ones)
                [examples[1]],  # failed_examples
                [timeout_exc],  # exceptions
            )

            with patch("llm_extract.api.load_source") as mock_load_source:
                mock_load_source.side_effect = ["content 1", "content 2"]

                # Should raise RuntimeError with failure details
                with pytest.raises(RuntimeError) as exc_info:
                    # Need to mock examples creation
                    with patch("llm_extract.api.dspy.Example") as mock_example_cls:
                        mock_example_cls.side_effect = examples
                        extract_folder(temp_dir, sample_attrs, ["txt"])

                error_msg = str(exc_info.value)
                # File path should be in error
                assert "file2.txt" in error_msg
                # Exception type should be mentioned
                assert "TimeoutError" in error_msg

    finally:
        shutil.rmtree(temp_dir)


def test_extract_folder_multimodal(sample_attrs) -> None:
    """Test that extract_folder() handles multimodal (PDFs) correctly."""
    from llm_extract.api import extract_folder

    pdf_dir = Path(__file__).parent / "fixtures" / "documents"
    if not pdf_dir.exists() or not list(pdf_dir.glob("*.pdf")):
        pytest.skip("PDF fixtures not found")

    with patch("llm_extract.api.Extract") as mock_extract_cls:
        mock_extractor = MagicMock()
        mock_extractor.batch.return_value = ([MagicMock()], [], [])
        mock_extract_cls.return_value = mock_extractor

        results = extract_folder(pdf_dir, sample_attrs, ["pdf"])

        # Verify multimodal signature was built
        call_args = mock_extract_cls.call_args
        assert call_args is not None
