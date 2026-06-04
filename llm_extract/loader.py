import csv
from llm_extract.models import Attribute
from pathlib import Path
from llm_extract.exceptions import (
    AttributeTypeConversionError,
    LoadingAttributeFromCSVError,
    CannotCreateAttributeWithDisallowedNameError,
)

EXPECTED_COLUMNS = {"name", "type", "description"}
DISALLOWED_NAMES = {"source"}


def load_attributes_csv(path: Path | str) -> list[Attribute]:
    path = Path(path)
    with path.open() as f:
        reader = csv.DictReader(f)
        missing = EXPECTED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing columns: {missing}")
        try:
            attributes = [
                Attribute.from_csv_row(row, disallowed_names=DISALLOWED_NAMES)
                for row in reader
            ]
        except (
            AttributeTypeConversionError,
            CannotCreateAttributeWithDisallowedNameError,
        ) as exc:
            raise LoadingAttributeFromCSVError(
                f"Failed to load attributes from csv: {exc}"
            )
        return attributes
