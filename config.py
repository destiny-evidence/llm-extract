import dspy
import os
from dotenv import load_dotenv
from functools import cache
from typing import Optional


load_dotenv()

API_BASE = os.environ["OPENAI_API_BASE"]
API_KEY = os.environ["OPENAI_API_KEY"]
LLM_MODEL = os.environ["LLM_MODEL"]


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
        model = LLM_MODEL
    lm = dspy.LM(
        model=model,
        api_base=API_BASE,
        api_key=API_KEY,
        cache=cache,
        temperature=temperature,
    )
    result = lm("Say: 'hello world'", temperature=0.0)
    assert "hello world" in result[0].lower(), result
    return lm


@cache
def configure_dspy(lm: Optional[dspy.LM] = None):
    if lm is None:
        lm = get_llm()
    dspy.configure(lm=lm)
