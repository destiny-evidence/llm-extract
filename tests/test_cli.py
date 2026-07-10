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
def source_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "sources"
    folder.mkdir()
    (folder / "file1.txt").write_text("First document.")
    (folder / "file2.txt").write_text("Second document.")
    (folder / "file3.md").write_text("Markdown document.")
    return folder


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

    mock_attrs = MagicMock()

    with (
        patch("llm_extract.cli.file.configure_dspy") as mock_configure,
        patch("llm_extract.cli.common.load_csv") as mock_load,
        patch(
            "llm_extract.cli.common.build_attributes_from_csv", return_value=mock_attrs
        ) as mock_build_csv,
        patch("llm_extract.cli.file.extract", return_value=mock_result) as mock_extract,
    ):
        yield {
            "configure": mock_configure,
            "load": mock_load,
            "build_csv": mock_build_csv,
            "extract": mock_extract,
            "result": mock_result,
            "attrs": mock_attrs,
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
        patch("llm_extract.cli.file.configure_dspy") as mock_configure,
        patch("llm_extract.cli.common.load_workbook") as mock_load_sheets,
        patch("llm_extract.cli.common.build_attributes_from_workbook") as mock_build,
        patch("llm_extract.cli.file.extract", return_value=mock_result) as mock_extract,
    ):
        yield {
            "configure": mock_configure,
            "load_sheets": mock_load_sheets,
            "build": mock_build,
            "extract": mock_extract,
            "result": mock_result,
        }


@pytest.fixture
def mock_folder_pipeline():
    """Patch the folder extraction pipeline so no LLM calls are made."""
    mock_result = MagicMock()
    mock_result.write_csv = MagicMock()

    with (
        patch("llm_extract.cli.folder.configure_dspy") as mock_configure,
        patch("llm_extract.cli.common.load_csv") as mock_load,
        patch(
            "llm_extract.cli.folder.extract_folder",
            return_value=[("file1", mock_result), ("file2", mock_result)],
        ) as mock_extract_folder,
        patch(
            "llm_extract.cli.folder.write_extraction_results_to_folder"
        ) as mock_write,
    ):
        yield {
            "configure": mock_configure,
            "load": mock_load,
            "extract_folder": mock_extract_folder,
            "write": mock_write,
            "result": mock_result,
        }


# ============================================================================
# FILE SUBCOMMAND TESTS
# ============================================================================


def test_file_happy_path(source_file, attrs_file, mock_pipeline) -> None:
    result = runner.invoke(
        app, ["file", "--source", str(source_file), "--attrs", str(attrs_file)]
    )

    assert result.exit_code == 0
    mock_pipeline["configure"].assert_called_once_with(env_file=None, multimodal=False)
    mock_pipeline["load"].assert_called_once_with(attrs_file)
    mock_extract_call = mock_pipeline["extract"].call_args
    assert mock_extract_call[0] == (source_file, mock_pipeline["attrs"])
    assert mock_extract_call[1]["with_reasoning"] is False
    assert "on_progress" in mock_extract_call[1]


def test_file_with_reasoning(source_file, attrs_file, mock_pipeline) -> None:
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--with-reasoning",
        ],
    )

    assert result.exit_code == 0
    mock_extract_call = mock_pipeline["extract"].call_args
    assert mock_extract_call[0] == (source_file, mock_pipeline["attrs"])
    assert mock_extract_call[1]["with_reasoning"] is True
    assert "on_progress" in mock_extract_call[1]


def test_file_defaults_output_dir_to_cwd(
    source_file, attrs_file, mock_pipeline
) -> None:
    result = runner.invoke(
        app, ["file", "--source", str(source_file), "--attrs", str(attrs_file)]
    )

    assert result.exit_code == 0
    expected = Path.cwd() / "source-extracted.csv"
    mock_pipeline["result"].write_csv.assert_called_once_with(expected)


def test_file_writes_csv_to_output_dir(
    source_file, attrs_file, tmp_path, mock_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    expected = tmp_path / "source-extracted.csv"
    mock_pipeline["result"].write_csv.assert_called_once_with(expected)


def test_file_writes_excel_to_output_dir_when_attrs_is_excel(
    source_file, excel_attrs_file, tmp_path, mock_excel_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(source_file),
            "--attrs",
            str(excel_attrs_file),
            "--type",
            "Study",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    expected = tmp_path / "source-extracted.xlsx"
    mock_excel_pipeline["result"].write_excel.assert_called_once_with(expected)
    mock_excel_pipeline["result"].write_csv.assert_not_called()


def test_file_without_json_flag_does_not_write_json(
    source_file, attrs_file, tmp_path, mock_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    mock_pipeline["result"].write_json.assert_not_called()


def test_file_json_flag_writes_json_alongside_output(
    source_file, attrs_file, tmp_path, mock_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--output-dir",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    mock_pipeline["result"].write_csv.assert_called_once_with(
        tmp_path / "source-extracted.csv"
    )
    mock_pipeline["result"].write_json.assert_called_once_with(
        tmp_path / "source-extracted.json"
    )


def test_file_json_flag_defaults_to_cwd_when_no_output_dir(
    source_file, attrs_file, mock_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--json",
        ],
    )

    assert result.exit_code == 0
    expected = Path.cwd() / "source-extracted.json"
    mock_pipeline["result"].write_json.assert_called_once_with(expected)


def test_file_nonexistent_output_dir(source_file, attrs_file, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--output-dir",
            str(tmp_path / "nonexistent" / "nested"),
        ],
    )
    assert result.exit_code != 0


def test_file_path_as_output_dir_errors(
    source_file, attrs_file, tmp_path, mock_pipeline
) -> None:
    output_file = tmp_path / "results.csv"
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--output-dir",
            str(output_file),
        ],
    )

    assert result.exit_code != 0
    mock_pipeline["extract"].assert_not_called()


def test_file_unsupported_source_filetype_errors(
    attrs_file, tmp_path, mock_pipeline
) -> None:
    unsupported_source = tmp_path / "source.docx"
    unsupported_source.write_text("Some product description text.")
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(unsupported_source),
            "--attrs",
            str(attrs_file),
        ],
    )

    assert result.exit_code != 0
    mock_pipeline["extract"].assert_not_called()


def test_file_missing_source_option(attrs_file) -> None:
    result = runner.invoke(app, ["file", "--attrs", str(attrs_file)])
    assert result.exit_code != 0


def test_file_missing_attrs_option(source_file) -> None:
    result = runner.invoke(app, ["file", "--source", str(source_file)])
    assert result.exit_code != 0


def test_file_nonexistent_source_file(tmp_path, attrs_file) -> None:
    result = runner.invoke(
        app,
        ["file", "--source", str(tmp_path / "ghost.txt"), "--attrs", str(attrs_file)],
    )
    assert result.exit_code != 0


def test_file_nonexistent_attrs_file(source_file, tmp_path) -> None:
    result = runner.invoke(
        app,
        ["file", "--source", str(source_file), "--attrs", str(tmp_path / "ghost.csv")],
    )
    assert result.exit_code != 0


def test_file_nonexistent_env_file(source_file, attrs_file, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(source_file),
            "--attrs",
            str(attrs_file),
            "--env",
            str(tmp_path / "ghost.env"),
        ],
    )
    assert result.exit_code != 0


def test_file_with_excel_attrs_and_type(
    source_file, excel_attrs_file, mock_excel_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
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
    mock_extract_call = mock_excel_pipeline["extract"].call_args
    assert mock_extract_call[0] == (
        source_file,
        mock_excel_pipeline["build"].return_value,
    )
    assert mock_extract_call[1]["with_reasoning"] is False
    assert "on_progress" in mock_extract_call[1]


def test_file_with_excel_attrs_missing_type_errors(
    source_file, excel_attrs_file
) -> None:
    with patch("llm_extract.cli.file.configure_dspy"):
        result = runner.invoke(
            app,
            ["file", "--source", str(source_file), "--attrs", str(excel_attrs_file)],
        )

    assert result.exit_code != 0


# ============================================================================
# FOLDER SUBCOMMAND TESTS
# ============================================================================


def test_folder_happy_path(source_folder, attrs_file, mock_folder_pipeline) -> None:
    result = runner.invoke(
        app, ["folder", "--source", str(source_folder), "--attrs", str(attrs_file)]
    )

    assert result.exit_code == 0
    mock_folder_pipeline["configure"].assert_called_once_with(
        env_file=None, multimodal=False
    )
    mock_folder_pipeline["load"].assert_called_once_with(attrs_file)
    mock_folder_pipeline["extract_folder"].assert_called_once()
    mock_folder_pipeline["write"].assert_called_once()


def test_folder_with_reasoning(source_folder, attrs_file, mock_folder_pipeline) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
            "--with-reasoning",
        ],
    )

    assert result.exit_code == 0
    call_kwargs = mock_folder_pipeline["extract_folder"].call_args[1]
    assert call_kwargs["with_reasoning"] is True


def test_folder_with_single_custom_filetype(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
            "--filetype",
            "md",
        ],
    )

    assert result.exit_code == 0
    call_kwargs = mock_folder_pipeline["extract_folder"].call_args[1]
    assert call_kwargs["filetypes"] == ["md"]


def test_folder_with_multiple_filetypes(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    mock_folder_pipeline["extract_folder"].return_value = [
        ("file1", mock_folder_pipeline["result"])
    ]
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
            "--filetype",
            "txt",
            "--filetype",
            "md",
        ],
    )

    assert result.exit_code == 0
    call_kwargs = mock_folder_pipeline["extract_folder"].call_args[1]
    assert call_kwargs["filetypes"] == ["txt", "md"]


def test_folder_with_custom_max_concurrent(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
            "--max-concurrent",
            "4",
        ],
    )

    assert result.exit_code == 0
    call_kwargs = mock_folder_pipeline["extract_folder"].call_args[1]
    assert call_kwargs["max_concurrent"] == 4


def test_folder_with_custom_output_dir(
    source_folder, attrs_file, tmp_path, mock_folder_pipeline
) -> None:
    output = tmp_path / "my_results"
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
            "--output-dir",
            str(output),
        ],
    )

    assert result.exit_code == 0
    call_args = mock_folder_pipeline["write"].call_args[0]
    assert call_args[0] == output


def test_folder_defaults_to_extracted_folder_in_cwd(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
        ],
    )

    assert result.exit_code == 0
    call_args = mock_folder_pipeline["write"].call_args[0]
    expected_output = Path.cwd() / f"{source_folder.name}-extracted"
    assert call_args[0] == expected_output


def test_folder_with_excel_attrs(
    source_folder, excel_attrs_file, mock_folder_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(excel_attrs_file),
            "--type",
            "Study",
        ],
    )

    assert result.exit_code == 0
    mock_folder_pipeline["extract_folder"].assert_called_once()
    # Check that use_excel=True was passed
    call_kwargs = mock_folder_pipeline["write"].call_args[1]
    assert call_kwargs["use_excel"] is True


def test_folder_without_json_flag_passes_also_json_false(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    result = runner.invoke(
        app, ["folder", "--source", str(source_folder), "--attrs", str(attrs_file)]
    )

    assert result.exit_code == 0
    call_kwargs = mock_folder_pipeline["write"].call_args[1]
    assert call_kwargs["also_json"] is False


def test_folder_json_flag_passes_also_json_true(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
            "--json",
        ],
    )

    assert result.exit_code == 0
    call_kwargs = mock_folder_pipeline["write"].call_args[1]
    assert call_kwargs["also_json"] is True


def test_folder_no_files_found_for_any_filetype(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    mock_folder_pipeline["extract_folder"].return_value = []
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
            "--filetype",
            "txt",
            "--filetype",
            "md",
        ],
    )

    assert result.exit_code == 0
    assert "No files matching" in result.stdout
    assert ".txt" in result.stdout and ".md" in result.stdout


def test_folder_partial_files_found(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    mock_result = MagicMock()
    # Return only one file (md) even though multiple filetypes were requested
    mock_folder_pipeline["extract_folder"].return_value = [("file1", mock_result)]
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
            "--filetype",
            "txt",
            "--filetype",
            "md",
        ],
    )

    assert result.exit_code == 0
    assert "Extracted 1 files" in result.stdout
    mock_folder_pipeline["write"].assert_called_once()


def test_folder_unsupported_filetype(source_folder, attrs_file) -> None:
    with patch("llm_extract.cli.folder.configure_dspy"):
        result = runner.invoke(
            app,
            [
                "folder",
                "--source",
                str(source_folder),
                "--attrs",
                str(attrs_file),
                "--filetype",
                "unsupported",
            ],
        )

    assert result.exit_code != 0
    assert (
        "Unsupported file type" in result.stdout
        or "Unsupported file type" in result.stderr
    )


def test_folder_missing_source_option(attrs_file) -> None:
    result = runner.invoke(app, ["folder", "--attrs", str(attrs_file)])
    assert result.exit_code != 0


def test_folder_missing_attrs_option(source_folder) -> None:
    result = runner.invoke(app, ["folder", "--source", str(source_folder)])
    assert result.exit_code != 0


def test_folder_nonexistent_source_folder(tmp_path, attrs_file) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(tmp_path / "ghost_folder"),
            "--attrs",
            str(attrs_file),
        ],
    )
    assert result.exit_code != 0


def test_folder_nonexistent_attrs_file(source_folder, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(tmp_path / "ghost.csv"),
        ],
    )
    assert result.exit_code != 0


def test_folder_file_path_as_output_errors(source_folder, attrs_file, tmp_path) -> None:
    output_file = tmp_path / "results.csv"
    with (
        patch("llm_extract.cli.folder.configure_dspy"),
        patch("llm_extract.cli.common.load_csv") as mock_load,
    ):
        mock_load.return_value = []
        result = runner.invoke(
            app,
            [
                "folder",
                "--source",
                str(source_folder),
                "--attrs",
                str(attrs_file),
                "--output-dir",
                str(output_file),
            ],
        )

    assert result.exit_code != 0


def test_folder_with_recursive_flag(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
            "--recursive",
        ],
    )

    assert result.exit_code == 0
    call_kwargs = mock_folder_pipeline["extract_folder"].call_args[1]
    assert call_kwargs["recursive"] is True


def test_folder_recursive_default_false(
    source_folder, attrs_file, mock_folder_pipeline
) -> None:
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(attrs_file),
        ],
    )

    assert result.exit_code == 0
    call_kwargs = mock_folder_pipeline["extract_folder"].call_args[1]
    assert call_kwargs["recursive"] is False
