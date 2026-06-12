import openpyxl
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
def excel_attrs_file(tmp_path: Path) -> Path:
    f = tmp_path / "attrs.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Study"
    sheet.append(["name", "type", "description"])
    sheet.append(["product_name", "str", "The product name"])
    workbook.save(f)
    return f


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    f = tmp_path / ".env"
    f.write_text("LLM_EXTRACT_API_KEY=test\n")
    return f


@pytest.fixture
def mock_pipeline():
    """Patch the extraction pipeline so no LLM calls are made."""
    mock_result = MagicMock()
    mock_result.to_csv_rows.return_value = [
        ["name", "value"],
        ["product_name", "Widget"],
    ]

    with (
        patch("llm_extract.cli.configure_dspy") as mock_configure,
        patch("llm_extract.cli.load_attributes_csv") as mock_load,
        patch("llm_extract.cli.extract", return_value=mock_result) as mock_extract,
    ):
        yield {
            "configure": mock_configure,
            "load": mock_load,
            "extract": mock_extract,
            "result": mock_result,
        }


@pytest.fixture
def mock_excel_pipeline():
    """Patch the Excel-based extraction pipeline so no LLM calls are made."""
    mock_result = MagicMock()
    mock_result.to_csv_rows.return_value = [
        ["name", "value"],
        ["product_name", "Widget"],
    ]

    with (
        patch("llm_extract.cli.configure_dspy") as mock_configure,
        patch("llm_extract.cli.load_workbook_sheets") as mock_load_sheets,
        patch("llm_extract.cli.build_attributes_from_sheets") as mock_build,
        patch("llm_extract.cli.extract", return_value=mock_result) as mock_extract,
    ):
        yield {
            "configure": mock_configure,
            "load_sheets": mock_load_sheets,
            "build": mock_build,
            "extract": mock_extract,
            "result": mock_result,
        }


def test_extract_happy_path(source_file, attrs_file, mock_pipeline) -> None:
    result = runner.invoke(
        app, ["--file", str(source_file), "--attrs", str(attrs_file)]
    )

    assert result.exit_code == 0
    mock_pipeline["configure"].assert_called_once_with(env_file=None)
    mock_pipeline["load"].assert_called_once_with(attrs_file)
    mock_pipeline["extract"].assert_called_once_with(
        "Some product description text.",
        mock_pipeline["load"].return_value,
        with_reasoning=False,
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
            "--env",
            str(env_file),
        ],
    )

    assert result.exit_code == 0
    mock_pipeline["configure"].assert_called_once_with(env_file=env_file)


def test_extract_with_reasoning(source_file, attrs_file, mock_pipeline) -> None:
    result = runner.invoke(
        app,
        ["--file", str(source_file), "--attrs", str(attrs_file), "--with-reasoning"],
    )

    assert result.exit_code == 0
    mock_pipeline["extract"].assert_called_once_with(
        "Some product description text.",
        mock_pipeline["load"].return_value,
        with_reasoning=True,
    )


def test_extract_calls_display_when_no_output(
    source_file, attrs_file, mock_pipeline
) -> None:
    result = runner.invoke(
        app, ["--file", str(source_file), "--attrs", str(attrs_file)]
    )

    assert result.exit_code == 0
    mock_pipeline["result"].display.assert_called_once()
    mock_pipeline["result"].write_csv.assert_not_called()


def test_extract_calls_write_csv_when_output_given(
    source_file, attrs_file, tmp_path, mock_pipeline
) -> None:
    output = tmp_path / "results.csv"
    result = runner.invoke(
        app,
        [
            "--file",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    mock_pipeline["result"].write_csv.assert_called_once_with(output)
    mock_pipeline["result"].display.assert_not_called()


def test_extract_auto_names_file_when_output_is_directory(
    source_file, attrs_file, tmp_path, mock_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "--file",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    expected = tmp_path / "source-extracted.csv"
    mock_pipeline["result"].write_csv.assert_called_once_with(expected)


def test_extract_nonexistent_output_dir(source_file, attrs_file, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--file",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--output",
            str(tmp_path / "nonexistent" / "results.csv"),
        ],
    )
    assert result.exit_code != 0


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
            "--env",
            str(tmp_path / "ghost.env"),
        ],
    )
    assert result.exit_code != 0


def test_extract_with_excel_attrs_and_type(
    source_file, excel_attrs_file, mock_excel_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "--file",
            str(source_file),
            "--attrs",
            str(excel_attrs_file),
            "--type",
            "Study",
        ],
    )

    assert result.exit_code == 0
    mock_excel_pipeline["load_sheets"].assert_called_once_with(excel_attrs_file)
    mock_excel_pipeline["build"].assert_called_once_with(
        mock_excel_pipeline["load_sheets"].return_value, "Study"
    )
    mock_excel_pipeline["extract"].assert_called_once_with(
        "Some product description text.",
        mock_excel_pipeline["build"].return_value,
        with_reasoning=False,
    )


def test_extract_with_excel_attrs_missing_type_errors(
    source_file, excel_attrs_file
) -> None:
    with patch("llm_extract.cli.configure_dspy"):
        result = runner.invoke(
            app, ["--file", str(source_file), "--attrs", str(excel_attrs_file)]
        )

    assert result.exit_code != 0
