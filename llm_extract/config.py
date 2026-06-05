import dspy
import os
from pathlib import Path
from dotenv import load_dotenv
from functools import cache
from typing import Optional
from llm_extract.exceptions import MissingEnvironmentVariablesError


_config_dir = (
    Path.home() / "AppData" / "Roaming" / "llm-extract"
    if os.name == "nt"  # in case user is on Windows
    else Path.home() / ".config" / "llm-extract"
)


_REQUIRED_VARS = ["LLM_EXTRACT_API_BASE", "LLM_EXTRACT_API_KEY", "LLM_EXTRACT_MODEL"]


def _load_env(env_file: Optional[Path] = None) -> None:
    """
    Load environment variables from available .env sources in priority order.

    :param env_file: explicit .env file path to load with highest priority
    :return: None
    :raises MissingEnvironmentVariablesError: if any required env vars are absent after loading
    """
    load_dotenv(_config_dir / ".env")  # lowest priority: user config
    load_dotenv()  # CWD .env
    if env_file is not None:
        load_dotenv(env_file, override=True)  # highest priority: explicit file

    missing = [var for var in _REQUIRED_VARS if not os.environ.get(var)]
    if missing:
        raise MissingEnvironmentVariablesError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them in your shell, a .env file, or pass --env-file."
        )


@cache
def get_llm(
    model: Optional[str] = None, cache: bool = True, temperature: float = 0.5
) -> dspy.LM:
    """
    Create a DSPy Language model object from environment variables.

    :param model: model endpoint of the provider
    :param cache: whether the model responses should be cached
    :param temperature: the temperature the model should be ran at
    :return: a dspy.LM object
    """
    if model is None:
        model = os.environ["LLM_EXTRACT_MODEL"]
    lm = dspy.LM(
        model=model,
        api_base=os.environ["LLM_EXTRACT_API_BASE"],
        api_key=os.environ["LLM_EXTRACT_API_KEY"],
        cache=cache,
        temperature=temperature,
    )
    result = lm("Say: 'hello world'", temperature=0.0)
    assert "hello world" in result[0].lower(), result
    return lm


@cache
def configure_dspy(
    lm: Optional[dspy.LM] = None, env_file: Optional[Path] = None
) -> None:
    """
    Configure DSPy with the given or default language model.

    :param lm: a DSPy LM instance to use; if None, creates one from environment variables
    :param env_file: optional path to a .env file to load with highest priority
    :return: None
    """
    _load_env(env_file)
    if lm is None:
        lm = get_llm()
    dspy.configure(lm=lm)
