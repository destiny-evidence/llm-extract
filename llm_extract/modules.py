import dspy


class Extract(dspy.Module):
    """DSPy module that extracts structured attributes from a source text."""

    def __init__(self, signature: dspy.Signature) -> None:
        self.signature = signature

    def forward(self, source: str, with_reasoning: bool = False) -> dspy.Prediction:
        """
        Run extraction on the source text.

        :param source: the source text to extract attributes from
        :param with_reasoning: whether to use ChainOfThought (True) or Predict (False)
        :return: a DSPy Prediction containing the extracted attribute values
        """
        if with_reasoning:
            extractor = dspy.ChainOfThought(self.signature)
        else:
            extractor = dspy.Predict(self.signature)
        return extractor(source=source)
