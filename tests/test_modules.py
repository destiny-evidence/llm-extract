import dspy
from llm_extract.modules import ExtractionResult, NOT_FOUND, _format_value


def test_format_value_none_returns_not_found() -> None:
    assert _format_value(None) == NOT_FOUND


def test_format_value_string_strips_double_quotes() -> None:
    assert _format_value('"Aeron Chair"') == "Aeron Chair"


def test_format_value_string_strips_single_quotes() -> None:
    assert _format_value("'Aeron Chair'") == "Aeron Chair"


def test_format_value_plain_string_unchanged() -> None:
    assert _format_value("Aeron Chair") == "Aeron Chair"


def test_format_value_list_json_serialised() -> None:
    assert _format_value([1, 2, 3]) == "[1, 2, 3]"


def test_format_value_dict_json_serialised() -> None:
    assert _format_value({"width": 68.5}) == '{"width": 68.5}'


def test_format_value_primitives_unchanged() -> None:
    assert _format_value(42) == 42
    assert _format_value(14.99) == 14.99
    assert _format_value(True) is True


def test_to_csv_rows_has_header() -> None:
    result = ExtractionResult(prediction=dspy.Prediction(product_name="Widget"))
    assert result.to_csv_rows()[0] == ["name", "value"]


def test_to_csv_rows_contains_extracted_values() -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", price=14.99)
    )
    rows = result.to_csv_rows()
    assert ["product_name", "Widget"] in rows
    assert ["price", 14.99] in rows


def test_to_csv_rows_none_value_becomes_not_found() -> None:
    result = ExtractionResult(prediction=dspy.Prediction(product_name=None))
    assert ["product_name", NOT_FOUND] in result.to_csv_rows()


def test_to_csv_rows_no_reasoning_row_when_absent() -> None:
    result = ExtractionResult(prediction=dspy.Prediction(product_name="Widget"))
    names = [row[0] for row in result.to_csv_rows()]
    assert "_reasoning_" not in names


def test_to_csv_rows_reasoning_appended_as_last_row() -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", reasoning="Found in line 1.")
    )
    assert result.to_csv_rows()[-1] == ["_reasoning_", "Found in line 1."]


def test_write_csv_creates_file(tmp_path) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", price=14.99)
    )
    output = tmp_path / "results.csv"
    result.write_csv(output)
    assert output.exists()


def test_write_csv_content(tmp_path) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", price=14.99)
    )
    output = tmp_path / "results.csv"
    result.write_csv(output)
    content = output.read_text()
    assert "product_name" in content
    assert "Widget" in content
    assert "price" in content
    assert "14.99" in content


def test_display_prints_aligned_columns(capsys) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", price=14.99)
    )
    result.display()
    output = capsys.readouterr().out
    assert "product_name" in output
    assert "Widget" in output
    assert "price" in output
    assert "14.99" in output


def test_to_csv_rows_reasoning_excluded_from_regular_rows() -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", reasoning="Found in line 1.")
    )
    regular_names = [row[0] for row in result.to_csv_rows()[1:-1]]
    assert "reasoning" not in regular_names
