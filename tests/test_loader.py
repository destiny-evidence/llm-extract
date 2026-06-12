import typing
import openpyxl
import pytest
from pathlib import Path
from llm_extract.loader import load_attributes_csv, load_workbook_sheets
from llm_extract.exceptions import LoadingAttributeFromCSVError


def test_load_valid_csv(tmp_path: Path) -> None:
    csv = tmp_path / "attrs.csv"
    csv.write_text(
        "name,type,description\nproduct_name,str,The product name\nprice,float,The price\n"
    )
    attrs = load_attributes_csv(csv)
    assert len(attrs) == 2
    assert attrs[0].name == "product_name"
    assert attrs[0].attr_type == typing.Optional[str]
    assert attrs[1].name == "price"
    assert attrs[1].attr_type == typing.Optional[float]


def test_load_empty_csv_returns_empty_list(tmp_path: Path) -> None:
    csv = tmp_path / "attrs.csv"
    csv.write_text("name,type,description\n")
    assert load_attributes_csv(csv) == []


def test_load_csv_missing_column_raises(tmp_path: Path) -> None:
    csv = tmp_path / "attrs.csv"
    csv.write_text("name,type\nfoo,str\n")
    with pytest.raises(ValueError, match="CSV missing columns"):
        load_attributes_csv(csv)


def test_load_csv_missing_all_required_columns_raises(tmp_path: Path) -> None:
    csv = tmp_path / "attrs.csv"
    csv.write_text("col_a,col_b\nfoo,bar\n")
    with pytest.raises(ValueError, match="CSV missing columns"):
        load_attributes_csv(csv)


def test_load_csv_disallowed_name_raises(tmp_path: Path) -> None:
    csv = tmp_path / "attrs.csv"
    csv.write_text("name,type,description\nsource,str,Reserved name\n")
    with pytest.raises(LoadingAttributeFromCSVError):
        load_attributes_csv(csv)


def test_load_csv_invalid_type_raises(tmp_path: Path) -> None:
    csv = tmp_path / "attrs.csv"
    csv.write_text("name,type,description\nfoo,pathlib.Path,A path\n")
    with pytest.raises(LoadingAttributeFromCSVError):
        load_attributes_csv(csv)


def test_load_csv_accepts_string_path(tmp_path: Path) -> None:
    csv = tmp_path / "attrs.csv"
    csv.write_text("name,type,description\nfoo,str,Foo\n")
    assert load_attributes_csv(csv) == load_attributes_csv(str(csv))


# --- load_workbook_sheets ---


def _write_workbook(path: Path, sheets: dict[str, list[list]]) -> None:
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    workbook.save(path)


def test_load_workbook_sheets_valid(tmp_path: Path) -> None:
    path = tmp_path / "types.xlsx"
    _write_workbook(
        path,
        {
            "Study": [
                ["name", "type", "description"],
                ["title", "str", "The title"],
            ]
        },
    )
    assert load_workbook_sheets(path) == {
        "Study": [{"name": "title", "type": "str", "description": "The title"}]
    }


def test_load_workbook_sheets_multiple_sheets(tmp_path: Path) -> None:
    path = tmp_path / "types.xlsx"
    _write_workbook(
        path,
        {
            "Study": [
                ["name", "type", "description"],
                ["title", "str", "The title"],
            ],
            "Author": [
                ["name", "type", "description"],
                ["full_name", "str", "The author's name"],
            ],
        },
    )
    sheets = load_workbook_sheets(path)
    assert set(sheets) == {"Study", "Author"}
    assert sheets["Author"] == [
        {"name": "full_name", "type": "str", "description": "The author's name"}
    ]


def test_load_workbook_sheets_empty_sheet_returns_empty_list(tmp_path: Path) -> None:
    path = tmp_path / "types.xlsx"
    _write_workbook(path, {"Study": []})
    assert load_workbook_sheets(path) == {"Study": []}


def test_load_workbook_sheets_skips_blank_rows(tmp_path: Path) -> None:
    path = tmp_path / "types.xlsx"
    _write_workbook(
        path,
        {
            "Study": [
                ["name", "type", "description"],
                ["title", "str", "The title"],
                [None, None, None],
            ]
        },
    )
    assert load_workbook_sheets(path) == {
        "Study": [{"name": "title", "type": "str", "description": "The title"}]
    }


def test_load_workbook_sheets_missing_columns_raises(tmp_path: Path) -> None:
    path = tmp_path / "types.xlsx"
    _write_workbook(path, {"Study": [["name", "type"], ["title", "str"]]})
    with pytest.raises(ValueError, match="missing columns"):
        load_workbook_sheets(path)


def test_load_workbook_sheets_accepts_string_path(tmp_path: Path) -> None:
    path = tmp_path / "types.xlsx"
    _write_workbook(
        path,
        {
            "Study": [
                ["name", "type", "description"],
                ["title", "str", "The title"],
            ]
        },
    )
    assert load_workbook_sheets(path) == load_workbook_sheets(str(path))
