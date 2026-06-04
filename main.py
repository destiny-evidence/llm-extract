from llm_extract.config import configure_dspy
from llm_extract.loader import load_attributes_csv
from llm_extract.factory import extraction_signature_builder
from llm_extract.modules import Extract


def main():
    configure_dspy()
    attrs = load_attributes_csv("attributes.csv")
    custom_signature = extraction_signature_builder(attrs)
    extractor = Extract(custom_signature)
    with open("sample.txt", "r") as f:
        source = f.read()
    results = extractor(source)
    print(results)


if __name__ == "__main__":
    main()
