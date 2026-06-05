import typing
import pytest
from pathlib import Path
from llm_extract.loader import load_attributes_csv
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
