import os
import pytest
from pathlib import Path
from llm_extract.config import _load_env
from llm_extract.exceptions import MissingEnvironmentVariablesError

REQUIRED_VARS = ["LLM_EXTRACT_API_BASE", "LLM_EXTRACT_API_KEY", "LLM_EXTRACT_MODEL"]


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    for var in REQUIRED_VARS:
        monkeypatch.delenv(var, raising=False)
    # Prevent file-based .env sources from polluting the test environment
    monkeypatch.setattr("llm_extract.config.load_dotenv", lambda *a, **kw: None)


def test_raises_when_all_vars_missing() -> None:
    with pytest.raises(MissingEnvironmentVariablesError) as exc_info:
        _load_env()
    for var in REQUIRED_VARS:
        assert var in str(exc_info.value)


def test_raises_when_some_vars_missing(monkeypatch) -> None:
    monkeypatch.setenv("LLM_EXTRACT_API_BASE", "http://localhost")
    monkeypatch.setenv("LLM_EXTRACT_API_KEY", "key")
    with pytest.raises(MissingEnvironmentVariablesError) as exc_info:
        _load_env()
    assert "LLM_EXTRACT_MODEL" in str(exc_info.value)
    assert "LLM_EXTRACT_API_BASE" not in str(exc_info.value)


def test_succeeds_when_all_vars_set(monkeypatch) -> None:
    for var in REQUIRED_VARS:
        monkeypatch.setenv(var, "test_value")
    _load_env()  # should not raise


def test_env_file_is_loaded_with_override(tmp_path: Path, monkeypatch) -> None:
    from dotenv import load_dotenv as real_load_dotenv

    monkeypatch.setattr("llm_extract.config.load_dotenv", real_load_dotenv)
    for var in REQUIRED_VARS:
        monkeypatch.setenv(var, "original")

    env_file = tmp_path / ".env"
    env_file.write_text("LLM_EXTRACT_API_BASE=http://overridden\n")

    _load_env(env_file=env_file)
    assert os.environ["LLM_EXTRACT_API_BASE"] == "http://overridden"
