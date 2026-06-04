import dspy

class Extract(dspy.Module):
    def __init__(self, signature: dspy.Signature):
        self.signature = signature

    def forward(self, source: str, with_reasoning: bool = True):
        if with_reasoning:
            extractor = dspy.ChainOfThought(self.signature)
        else:
            extractor = dspy.Predict(self.signature)
        return extractor(source=source)
