import json
import typing

from pydantic_core import to_jsonable_python

NOT_FOUND = "NOT_FOUND"


def format_value(value: object) -> object:
    """
    Format a single extracted value for presentation in CSV/Excel.

    :param value: the value to format
    :return: NOT_FOUND if `value` is None; `value` stripped of surrounding
             quotes if it's a string; `value` JSON-encoded (via
             `to_jsonable_python`) if it's a list or dict; otherwise `value`
             unchanged
    """
    if value is None:
        return NOT_FOUND
    if isinstance(value, str):
        return value.strip("\"'")
    if isinstance(value, (list, dict)):
        # e.g. a list[type] value from a plain CSV attrs file - to_jsonable_python
        # handles any nesting consistently before json.dumps.
        return json.dumps(to_jsonable_python(value))
    return value


def apply_not_found_sentinel(value: object) -> object:
    """
    Recursively replace `None` with the NOT_FOUND sentinel, matching the
    missing-value convention CSV/Excel already apply via `format_value`.

    :param value: a plain JSON-able value (e.g. from `to_jsonable_python`),
                   possibly containing `None` at any nesting depth
    :return: the same structure with every `None` replaced by NOT_FOUND
    """
    if value is None:
        return NOT_FOUND
    if isinstance(value, list):
        return [apply_not_found_sentinel(v) for v in value]
    if isinstance(value, dict):
        return {k: apply_not_found_sentinel(v) for k, v in value.items()}
    return value


def unwrap_optional(type_: object) -> object:
    """
    Unwrap an `Optional[X]` annotation to `X`.

    :param type_: a type annotation, possibly `Optional[X]`
    :return: `X` if `type_` is `Optional[X]`, otherwise `type_` unchanged
    """
    args = typing.get_args(type_)
    if type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return type_
