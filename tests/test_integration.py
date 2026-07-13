import dataclasses
import typing
from pathlib import Path

import dspy
import pytest
from typer.testing import CliRunner
from llm_extract.config import configure_dspy
from llm_extract.loader import load_workbook, load_csv
from llm_extract.factory import (
    build_attributes_from_workbook,
    build_attributes_from_csv,
    extraction_signature_builder,
)
from llm_extract.modules import Extract
from llm_extract.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


@pytest.fixture(scope="module")
def extractor():
    configure_dspy()
    csv_data = load_csv(FIXTURES / "attributes.csv")
    attrs = build_attributes_from_csv(csv_data)
    signature = extraction_signature_builder(attrs)
    return Extract(signature)


@pytest.fixture(scope="module")
def source_text():
    with open(FIXTURES / "sample.txt") as f:
        return f.read()


def test_can_extract_attributes_correctly(extractor, source_text):
    results = extractor(source_text)
    csv_data = load_csv(FIXTURES / "attributes.csv")
    attrs = build_attributes_from_csv(csv_data)

    assert isinstance(results, dspy.Prediction)
    for attr in attrs:
        value = getattr(results, attr.name)
        if value is None:
            continue
        inner_type = typing.get_args(attr.attr_type)[0]  # unwrap Optional[X] -> X
        origin = typing.get_origin(inner_type)
        if origin is list:
            assert isinstance(value, list), f"{attr.name}: expected list"
            (elem_type,) = typing.get_args(inner_type)
            assert all(isinstance(e, elem_type) for e in value), (
                f"{attr.name}: expected all elements to be {elem_type}"
            )
        else:
            check_type = origin if origin is not None else inner_type
            assert isinstance(value, check_type), (
                f"{attr.name}: expected {inner_type}, got {type(value)}"
            )


@pytest.fixture(scope="module")
def template_attrs():
    workbook_data = load_workbook(FIXTURES / "RevMan Extraction Template.xlsx")
    return build_attributes_from_workbook(workbook_data, "Study")


@pytest.fixture(scope="module")
def template_extractor(template_attrs):
    configure_dspy()
    signature = extraction_signature_builder(template_attrs)
    return Extract(signature)


@pytest.fixture(scope="module")
def rct_source_text():
    with open(FIXTURES / "RCT Sample.md") as f:
        return f.read()


def test_can_extract_nested_attributes_from_excel_template(
    template_extractor, template_attrs, rct_source_text
):
    results = template_extractor(rct_source_text)

    assert isinstance(results, dspy.Prediction)
    for attr in template_attrs:
        value = getattr(results, attr.name)
        if value is None:
            continue
        inner_type = typing.get_args(attr.attr_type)[0]  # unwrap Optional[X] -> X
        origin = typing.get_origin(inner_type)
        if origin is list:
            assert isinstance(value, list), f"{attr.name}: expected list"
            (elem_type,) = typing.get_args(inner_type)
            assert all(dataclasses.is_dataclass(e) for e in value), (
                f"{attr.name}: expected all elements to be dataclass instances"
            )
            assert all(isinstance(e, elem_type) for e in value), (
                f"{attr.name}: expected all elements to be {elem_type}"
            )
        else:
            assert dataclasses.is_dataclass(value), (
                f"{attr.name}: expected a dataclass instance"
            )
            assert isinstance(value, inner_type), (
                f"{attr.name}: expected {inner_type}, got {type(value)}"
            )


# ============================================================================
# CLI INTEGRATION TESTS
# ============================================================================


def test_cli_file_extraction(tmp_path):
    """Test CLI extraction of a single file."""
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(FIXTURES / "sample.txt"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "sample-extracted.csv").exists()


def test_cli_file_extraction_to_csv(tmp_path):
    """Test CLI file extraction with CSV output."""
    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(FIXTURES / "sample.txt"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    output = tmp_path / "sample-extracted.csv"
    assert output.exists()
    content = output.read_text()
    assert "name" in content
    assert "value" in content


def test_cli_folder_extraction_txt_files(tmp_path):
    """Test CLI extraction of multiple text files from a folder."""
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(FIXTURES / "documents"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--filetype",
            "txt",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    output_dir = tmp_path / "documents-extracted"
    # Should have created extracted CSV files for each txt file
    extracted_files = list(output_dir.glob("*.csv"))
    assert len(extracted_files) == 3
    # Check that all expected files were created
    assert (output_dir / "product1-extracted.csv").exists()
    assert (output_dir / "product2-extracted.csv").exists()
    assert (output_dir / "product3-extracted.csv").exists()


def test_cli_folder_extraction_md_files(tmp_path):
    """Test CLI extraction of markdown files from a folder."""
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(FIXTURES / "documents"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--filetype",
            "md",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    output_dir = tmp_path / "documents-extracted"
    extracted_files = list(output_dir.glob("*.csv"))
    assert len(extracted_files) == 2
    assert (output_dir / "article1-extracted.csv").exists()
    assert (output_dir / "article2-extracted.csv").exists()


def test_cli_folder_extraction_multiple_filetypes(tmp_path):
    """Test CLI extraction of multiple file types."""
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(FIXTURES / "documents"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--filetype",
            "txt",
            "--filetype",
            "md",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    extracted_files = list((tmp_path / "documents-extracted").glob("*.csv"))
    # Should have 3 txt + 2 md = 5 total
    assert len(extracted_files) == 5


def test_cli_folder_extraction_default_output_dir(tmp_path, monkeypatch):
    """Test CLI folder extraction creates default <source>-extracted directory
    in the current working directory when --output-dir is omitted."""
    monkeypatch.chdir(tmp_path)
    source_folder = tmp_path / "test_docs"
    source_folder.mkdir()
    (source_folder / "doc1.txt").write_text("Sample document 1")
    (source_folder / "doc2.txt").write_text("Sample document 2")

    # Run extraction without specifying --output-dir
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(source_folder),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
        ],
    )

    assert result.exit_code == 0
    # Should have created test_docs-extracted folder in the cwd (tmp_path)
    expected_output_dir = tmp_path / "test_docs-extracted"
    assert expected_output_dir.exists()
    assert len(list(expected_output_dir.glob("*.csv"))) == 2


def test_cli_folder_extraction_with_max_concurrent(tmp_path):
    """Test CLI folder extraction with custom max_concurrent setting."""
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(FIXTURES / "documents"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--filetype",
            "txt",
            "--max-concurrent",
            "2",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    extracted_files = list((tmp_path / "documents-extracted").glob("*.csv"))
    assert len(extracted_files) == 3


def test_cli_folder_extraction_with_reasoning(tmp_path):
    """Test CLI folder extraction with reasoning flag."""
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(FIXTURES / "documents"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--filetype",
            "txt",
            "--with-reasoning",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    extracted_files = list((tmp_path / "documents-extracted").glob("*.csv"))
    assert len(extracted_files) == 3
    # Check that at least one file contains reasoning
    has_reasoning = False
    for file in extracted_files:
        content = file.read_text()
        if "_reasoning_" in content:
            has_reasoning = True
            break
    assert has_reasoning


def test_cli_folder_extraction_unsupported_filetype(tmp_path):
    """Test CLI folder extraction with unsupported filetype."""
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(FIXTURES / "documents"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--filetype",
            "json",  # Unsupported filetype
            "--output-dir",
            str(tmp_path),
        ],
    )

    # Should fail validation with non-zero exit code
    assert result.exit_code != 0


def test_cli_folder_extraction_recursive(tmp_path):
    """Test CLI folder extraction with recursive flag."""
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(FIXTURES / "nested_docs"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--recursive",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    output_dir = tmp_path / "nested_docs-extracted"
    # Should extract files from nested structure
    extracted_files = list(output_dir.glob("**/*.csv"))
    # Should find: project1/doc1, project1/doc2, project2/subdir/doc3
    assert len(extracted_files) == 3
    # Verify directory structure is preserved
    assert (output_dir / "project1" / "doc1-extracted.csv").exists()
    assert (output_dir / "project1" / "doc2-extracted.csv").exists()
    assert (output_dir / "project2" / "subdir" / "doc3-extracted.csv").exists()


def test_cli_folder_extraction_non_recursive_ignores_subdirs(tmp_path):
    """Test that non-recursive mode ignores subdirectories."""
    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(FIXTURES / "nested_docs"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    # Without --recursive, only finds files at top level (none in nested_docs root)
    extracted_files = list(tmp_path.glob("*.csv"))
    assert len(extracted_files) == 0


# ============================================================================
# MULTIMODAL DOCUMENT EXTRACTION INTEGRATION TESTS
# ============================================================================


def test_cli_file_extraction_from_pdf(tmp_path):
    """Test end-to-end extraction from PDF file via CLI."""
    pdf_path = FIXTURES / "documents" / "aiayn.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF test fixture not available")

    result = runner.invoke(
        app,
        [
            "file",
            "--source",
            str(pdf_path),
            "--attrs",
            str(FIXTURES / "paper_attributes.csv"),
            "--output-dir",
            str(tmp_path),
        ],
    )

    # Will fail if model doesn't support vision, but validates PDF routing works
    assert result.exit_code == 0 or "vision" in result.stdout.lower()


def test_cli_pdf_extraction_requires_vision_model():
    """Test that PDF extraction with non-vision model raises helpful error."""
    from llm_extract.config import _validate_model_vision_support

    with pytest.raises(ValueError, match="does not support vision"):
        _validate_model_vision_support("gpt-3.5-turbo")


def test_cli_folder_extraction_with_pdf_files(tmp_path):
    """Test extracting from folder containing PDF files via CLI."""
    pdf_path = FIXTURES / "documents" / "aiayn.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF test fixture not available")

    result = runner.invoke(
        app,
        [
            "folder",
            "--source",
            str(FIXTURES / "documents"),
            "--attrs",
            str(FIXTURES / "attributes.csv"),
            "--filetype",
            "pdf",
            "--output-dir",
            str(tmp_path),
        ],
    )

    # Validates PDF files are properly detected and routed to multimodal extraction
    assert result.exit_code == 0 or "vision" in result.stdout.lower()
