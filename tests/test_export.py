import typing

import dspy
import openpyxl
from pydantic import Field
from pydantic.dataclasses import dataclass as pydantic_dataclass

from llm_extract.export import ExtractionResult, NOT_FOUND, _format_value
from llm_extract.models import Attribute


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


@pydantic_dataclass
class _InterventionType:
    type_of_intervention: typing.Optional[str] = Field(default=None)


@pydantic_dataclass
class _Intervention:
    group_name: typing.Optional[str] = Field(default=None)
    intervention_type: typing.Optional[_InterventionType] = Field(default=None)


def test_format_value_nested_dataclass_json_serialised() -> None:
    value = _Intervention(
        group_name="Risperidone", intervention_type=_InterventionType("Intervention")
    )
    assert _format_value(value) == (
        '{"group_name": "Risperidone", '
        '"intervention_type": {"type_of_intervention": "Intervention"}}'
    )


def test_format_value_list_of_nested_dataclasses_json_serialised() -> None:
    value = [
        _Intervention(group_name="Risperidone", intervention_type=None),
        _Intervention(group_name="Haloperidol", intervention_type=None),
    ]
    assert _format_value(value) == (
        '[{"group_name": "Risperidone", "intervention_type": null}, '
        '{"group_name": "Haloperidol", "intervention_type": null}]'
    )


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


# --- write_excel ---


@pydantic_dataclass
class _OutcomeCategory:
    value: typing.Optional[str] = Field(default=None)


@pydantic_dataclass
class _Outcome:
    name: typing.Optional[str] = Field(default=None)
    category: typing.Optional[_OutcomeCategory] = Field(default=None)
    sub_interventions: typing.Optional[list[_Intervention]] = Field(default=None)


def test_write_excel_creates_file(tmp_path) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", price=14.99),
        attributes=[
            Attribute(
                name="product_name", attr_type=typing.Optional[str], description=""
            ),
            Attribute(name="price", attr_type=typing.Optional[float], description=""),
        ],
    )
    output = tmp_path / "results.xlsx"
    result.write_excel(output)
    assert output.exists()


def test_write_excel_plain_attrs_in_summary_sheet(tmp_path) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", price=14.99),
        attributes=[
            Attribute(
                name="product_name", attr_type=typing.Optional[str], description=""
            ),
            Attribute(name="price", attr_type=typing.Optional[float], description=""),
        ],
    )
    output = tmp_path / "results.xlsx"
    result.write_excel(output)

    workbook = openpyxl.load_workbook(output)
    assert "Summary" in workbook.sheetnames
    rows = list(workbook["Summary"].iter_rows(values_only=True))
    assert rows[0] == ("name", "value")
    assert ("product_name", "Widget") in rows
    assert ("price", 14.99) in rows


def test_write_excel_reasoning_in_summary_sheet(tmp_path) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", reasoning="Found in line 1."),
        attributes=[
            Attribute(
                name="product_name", attr_type=typing.Optional[str], description=""
            ),
        ],
    )
    output = tmp_path / "results.xlsx"
    result.write_excel(output)

    workbook = openpyxl.load_workbook(output)
    rows = list(workbook["Summary"].iter_rows(values_only=True))
    assert ("_reasoning_", "Found in line 1.") in rows


def test_write_excel_list_of_custom_type_gets_own_sheet(tmp_path) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(
            interventions=[
                _Intervention(
                    group_name="Risperidone",
                    intervention_type=_InterventionType("Intervention"),
                ),
                _Intervention(group_name="Haloperidol", intervention_type=None),
            ]
        ),
        attributes=[
            Attribute(
                name="interventions",
                attr_type=typing.Optional[list[_Intervention]],
                description="",
            ),
        ],
    )
    output = tmp_path / "results.xlsx"
    result.write_excel(output)

    workbook = openpyxl.load_workbook(output)
    assert "interventions" in workbook.sheetnames
    rows = list(workbook["interventions"].iter_rows(values_only=True))
    assert rows[0] == ("group_name", "intervention_type.type_of_intervention")
    assert rows[1] == ("Risperidone", "Intervention")
    assert rows[2] == ("Haloperidol", NOT_FOUND)

    summary_rows = list(workbook["Summary"].iter_rows(values_only=True))
    assert ("interventions", "interventions") in summary_rows
    link_cell = workbook["Summary"]["B2"]
    assert link_cell.hyperlink.target == "#'interventions'!A1"


def test_write_excel_scalar_custom_type_gets_single_row_sheet(tmp_path) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(
            lead_intervention=_Intervention(
                group_name="Risperidone",
                intervention_type=_InterventionType("Intervention"),
            )
        ),
        attributes=[
            Attribute(
                name="lead_intervention",
                attr_type=typing.Optional[_Intervention],
                description="",
            ),
        ],
    )
    output = tmp_path / "results.xlsx"
    result.write_excel(output)

    workbook = openpyxl.load_workbook(output)
    assert "lead_intervention" in workbook.sheetnames
    rows = list(workbook["lead_intervention"].iter_rows(values_only=True))
    assert rows[0] == ("group_name", "intervention_type.type_of_intervention")
    assert rows[1] == ("Risperidone", "Intervention")

    summary_rows = list(workbook["Summary"].iter_rows(values_only=True))
    assert ("lead_intervention", "lead_intervention") in summary_rows


def test_write_excel_missing_custom_type_has_not_found_in_summary_and_no_sheet(
    tmp_path,
) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(interventions=None),
        attributes=[
            Attribute(
                name="interventions",
                attr_type=typing.Optional[list[_Intervention]],
                description="",
            ),
        ],
    )
    output = tmp_path / "results.xlsx"
    result.write_excel(output)

    workbook = openpyxl.load_workbook(output)
    assert "interventions" not in workbook.sheetnames
    summary_rows = list(workbook["Summary"].iter_rows(values_only=True))
    assert ("interventions", NOT_FOUND) in summary_rows


def test_write_excel_empty_list_custom_type_has_not_found_in_summary_and_no_sheet(
    tmp_path,
) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(interventions=[]),
        attributes=[
            Attribute(
                name="interventions",
                attr_type=typing.Optional[list[_Intervention]],
                description="",
            ),
        ],
    )
    output = tmp_path / "results.xlsx"
    result.write_excel(output)

    workbook = openpyxl.load_workbook(output)
    assert "interventions" not in workbook.sheetnames
    summary_rows = list(workbook["Summary"].iter_rows(values_only=True))
    assert ("interventions", NOT_FOUND) in summary_rows


def test_write_excel_deep_nesting_falls_back_to_json(tmp_path) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(
            outcomes=[
                _Outcome(
                    name="BPRS score",
                    category=_OutcomeCategory("Mental Health Outcome"),
                    sub_interventions=[
                        _Intervention(group_name="Risperidone", intervention_type=None)
                    ],
                )
            ]
        ),
        attributes=[
            Attribute(
                name="outcomes",
                attr_type=typing.Optional[list[_Outcome]],
                description="",
            ),
        ],
    )
    output = tmp_path / "results.xlsx"
    result.write_excel(output)

    workbook = openpyxl.load_workbook(output)
    rows = list(workbook["outcomes"].iter_rows(values_only=True))
    assert rows[0] == ("name", "category.value", "sub_interventions")
    assert rows[1][0:2] == ("BPRS score", "Mental Health Outcome")
    assert rows[1][2] == ('[{"group_name": "Risperidone", "intervention_type": null}]')


# --- display with attribute metadata ---


def test_display_without_attributes_falls_back_to_csv_rows(capsys) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", price=14.99)
    )
    result.display()
    output = capsys.readouterr().out
    assert "product_name" in output
    assert "Widget" in output
    assert "price" in output
    assert "14.99" in output


def test_display_with_attributes_prints_plain_values(capsys) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(product_name="Widget", price=14.99),
        attributes=[
            Attribute(
                name="product_name", attr_type=typing.Optional[str], description=""
            ),
            Attribute(name="price", attr_type=typing.Optional[float], description=""),
        ],
    )
    result.display()
    output = capsys.readouterr().out
    assert "product_name" in output
    assert "Widget" in output
    assert "price" in output
    assert "14.99" in output


def test_display_with_custom_type_prints_table(capsys) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(
            interventions=[
                _Intervention(
                    group_name="Risperidone",
                    intervention_type=_InterventionType("Intervention"),
                ),
                _Intervention(group_name="Haloperidol", intervention_type=None),
            ]
        ),
        attributes=[
            Attribute(
                name="interventions",
                attr_type=typing.Optional[list[_Intervention]],
                description="",
            ),
        ],
    )
    result.display()
    output = capsys.readouterr().out

    assert "interventions" in output
    assert "see 'interventions' table below" in output
    assert "group_name" in output
    assert "intervention_type.type_of_intervention" in output
    assert "Risperidone" in output
    assert "Intervention" in output
    assert "Haloperidol" in output
    assert NOT_FOUND in output


def test_display_with_missing_custom_type_shows_not_found(capsys) -> None:
    result = ExtractionResult(
        prediction=dspy.Prediction(interventions=None),
        attributes=[
            Attribute(
                name="interventions",
                attr_type=typing.Optional[list[_Intervention]],
                description="",
            ),
        ],
    )
    result.display()
    output = capsys.readouterr().out

    lines = output.splitlines()
    assert any(line.startswith("interventions") and NOT_FOUND in line for line in lines)


def test_display_truncates_long_cell_values(capsys) -> None:
    long_value = "x" * 100
    result = ExtractionResult(
        prediction=dspy.Prediction(
            interventions=[_Intervention(group_name=long_value, intervention_type=None)]
        ),
        attributes=[
            Attribute(
                name="interventions",
                attr_type=typing.Optional[list[_Intervention]],
                description="",
            ),
        ],
    )
    result.display()
    output = capsys.readouterr().out

    for line in output.splitlines():
        assert len(line) < len(long_value)
