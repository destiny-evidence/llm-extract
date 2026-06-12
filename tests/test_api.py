import typing
import pytest
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


def test_extract_returns_extraction_result(sample_attrs) -> None:
    with patch("llm_extract.api.Extract") as mock_extract_cls:
        mock_extract_cls.return_value = MagicMock(return_value=MagicMock())
        result = extract("Some product text.", sample_attrs)
    assert isinstance(result, ExtractionResult)
    assert result.attributes == sample_attrs


def test_extract_passes_source_to_extractor(sample_attrs) -> None:
    with patch("llm_extract.api.Extract") as mock_extract_cls:
        mock_extractor = MagicMock()
        mock_extract_cls.return_value = mock_extractor
        extract("Some product text.", sample_attrs)
    mock_extractor.assert_called_once_with("Some product text.", with_reasoning=False)


def test_extract_passes_with_reasoning_to_extractor(sample_attrs) -> None:
    with patch("llm_extract.api.Extract") as mock_extract_cls:
        mock_extractor = MagicMock()
        mock_extract_cls.return_value = mock_extractor
        extract("Some product text.", sample_attrs, with_reasoning=True)
    mock_extractor.assert_called_once_with("Some product text.", with_reasoning=True)


def test_extract_builds_signature_from_attributes(sample_attrs) -> None:
    with (
        patch("llm_extract.api.extraction_signature_builder") as mock_builder,
        patch("llm_extract.api.Extract"),
    ):
        extract("Some text.", sample_attrs)
    mock_builder.assert_called_once_with(sample_attrs)
