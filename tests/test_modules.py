import dspy
from llm_extract.modules import ExtractionResult, NOT_FOUND


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
