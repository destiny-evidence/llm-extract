import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from llm_extract.cli import app

runner = CliRunner()


@pytest.fixture
def source_file(tmp_path: Path) -> Path:
    f = tmp_path / "source.txt"
    f.write_text("Some product description text.")
    return f


@pytest.fixture
def attrs_file(tmp_path: Path) -> Path:
    f = tmp_path / "attrs.csv"
    f.write_text("name,type,description\nproduct_name,str,The product name\n")
    return f


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    f = tmp_path / ".env"
    f.write_text("LLM_EXTRACT_API_KEY=test\n")
    return f


@pytest.fixture
def mock_pipeline():
    """Patch the extraction pipeline so no LLM calls are made."""
    mock_prediction = MagicMock()
    mock_prediction.__str__ = lambda self: "Prediction(product_name='Widget')"

    with (
        patch("llm_extract.cli.configure_dspy") as mock_configure,
        patch("llm_extract.cli.load_attributes_csv") as mock_load,
        patch("llm_extract.cli.extract", return_value=mock_prediction) as mock_extract,
    ):
        yield {
            "configure": mock_configure,
            "load": mock_load,
            "extract": mock_extract,
            "prediction": mock_prediction,
        }


def test_extract_happy_path(source_file, attrs_file, mock_pipeline) -> None:
    result = runner.invoke(
        app, ["--file", str(source_file), "--attrs", str(attrs_file)]
    )

    assert result.exit_code == 0
    mock_pipeline["configure"].assert_called_once_with(env_file=None)
    mock_pipeline["load"].assert_called_once_with(attrs_file)
    mock_pipeline["extract"].assert_called_once_with(
        "Some product description text.", mock_pipeline["load"].return_value
    )


def test_extract_with_env_file(
    source_file, attrs_file, env_file, mock_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "--file",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--env-file",
            str(env_file),
        ],
    )

    assert result.exit_code == 0
    mock_pipeline["configure"].assert_called_once_with(env_file=env_file)


def test_extract_output_contains_prediction(
    source_file, attrs_file, mock_pipeline
) -> None:
    result = runner.invoke(
        app, ["--file", str(source_file), "--attrs", str(attrs_file)]
    )

    assert result.exit_code == 0
    assert "Widget" in result.output


def test_extract_missing_file_option(attrs_file) -> None:
    result = runner.invoke(app, ["--attrs", str(attrs_file)])
    assert result.exit_code != 0


def test_extract_missing_attrs_option(source_file) -> None:
    result = runner.invoke(app, ["--file", str(source_file)])
    assert result.exit_code != 0


def test_extract_nonexistent_source_file(tmp_path, attrs_file) -> None:
    result = runner.invoke(
        app, ["--file", str(tmp_path / "ghost.txt"), "--attrs", str(attrs_file)]
    )
    assert result.exit_code != 0


def test_extract_nonexistent_attrs_file(source_file, tmp_path) -> None:
    result = runner.invoke(
        app, ["--file", str(source_file), "--attrs", str(tmp_path / "ghost.csv")]
    )
    assert result.exit_code != 0


def test_extract_nonexistent_env_file(source_file, attrs_file, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--file",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--env-file",
            str(tmp_path / "ghost.env"),
        ],
    )
    assert result.exit_code != 0
