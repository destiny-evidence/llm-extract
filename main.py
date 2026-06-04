from config import configure_dspy
from loader import load_attributes_csv
from factory import extraction_signature_builder
from modules import Extract


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
