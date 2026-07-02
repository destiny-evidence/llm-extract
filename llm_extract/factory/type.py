import builtins
import re
import typing

from llm_extract.models import TypeExpr, ALLOWED_TYPES

DISALLOWED_NAMES = {"source"}


def build_type_from_string(
    string: str, type_context: dict[str, TypeExpr] | None = None
) -> TypeExpr:
    """
    Parse a type expression string into a Python type wrapped in Optional.

    :param string: type expression string, e.g. 'list[int]' or 'float'
    :param type_context: extra named types that may be referenced in the type expression
    :return: the corresponding Optional-wrapped Python type
    """
    type_context = type_context or {}
    normalised = normalise_literal_type(string)
    without_strings = remove_quoted_strings(normalised)
    identifiers = set(re.findall(r"[a-zA-Z]\w*", without_strings))
    allowed = ALLOWED_TYPES | set(type_context)
    if not identifiers <= allowed:
        raise ValueError(f"Disallowed types: {identifiers - allowed}")
    return eval(
        f"Optional[{normalised}]",
        {**vars(typing), **vars(builtins), **type_context},
    )


def normalise_literal_type(type_str: str) -> str:
    """
    Normalise Literal types by quoting unquoted identifiers.

    :param type_str: type expression string, e.g. 'Literal[a, b]' or 'Literal["x"]'
    :return: normalised type with all Literal values quoted
    """

    def replace_literal_content(match: re.Match) -> str:
        content = match.group(1)
        values = [v.strip() for v in content.split(",")]
        quoted_values = []
        for val in values:
            if val and (val[0] in ('"', "'") or ord(val[0]) in (0x201C, 0x201D)):
                raise ValueError(
                    "Literal values must not be quoted. "
                    "Use Literal[a, b, c] instead of Literal['a', 'b', 'c']"
                )
            else:
                quoted_values.append(f'"{val}"')
        return f"Literal[{', '.join(quoted_values)}]"

    # Regex: Literal[...] with flexible whitespace
    # Captures comma-separated values
    return re.sub(r"Literal\s*\[\s*([^\]]+)\s*\]", replace_literal_content, type_str)


def remove_quoted_strings(type_str: str) -> str:
    """
    Remove all quoted strings from a type expression.

    :param type_str: type expression string that may contain quoted values
    :return: type expression with all quoted strings removed
    """
    # Regex: Match any quoted string (single or double quotes)
    # Removes entire quoted values including delimiters
    return re.sub(r'["\']([^"\']*)["\']', "", type_str)
