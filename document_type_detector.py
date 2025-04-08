from pathlib import Path
import spacy
import os
import pdfplumber
import json
import yaml
from collections import defaultdict
import re
import dateparser
from datetime import datetime
from spacy.language import Language
from spacy.tokens import Doc
import warnings
warnings.filterwarnings("ignore", message="CropBox missing from /Page")


# Load spaCy model globally
nlp = spacy.load("en_core_web_sm")

# Add custom Doc attribute
Doc.set_extension("document_type", default="Unknown")

# Load keyword-based document type rules from YAML
RULES_PATH = os.path.join(os.path.dirname(__file__), "document_rules.yml")

def load_rules():
    if os.path.exists(RULES_PATH):
        with open(RULES_PATH, "r") as f:
            return yaml.safe_load(f).get("document_types", {})
    return {}

document_type_rules = load_rules()

@Language.component("document_type_detector")
def document_type_detector(doc):
    lowered = doc.text.lower()
    detected_type = "Unknown"

    for doc_type, keywords in document_type_rules.items():
        if all(keyword.lower() in lowered for keyword in keywords):
            detected_type = doc_type
            break
        elif any(keyword.lower() in lowered for keyword in keywords):
            detected_type = doc_type  # partial match if no exact match

    doc._.document_type = detected_type
    print(f"🔍 Detected document type: {detected_type}")
    return doc

# Register component in spaCy pipeline
if "document_type_detector" not in nlp.pipe_names:
    nlp.add_pipe("document_type_detector", last=True)

# Register component in spaCy pipeline

def slugify(text):
    return re.sub(r"[^\w]+", "_", text.strip()).strip("_")

def rename_file(file_path, summary):
    base_dir = os.path.dirname(file_path)
    ext = os.path.splitext(file_path)[1]

    client = summary.get("parties_involved", ["Unknown"])[0].replace(" ", "_")
    doc_type = slugify(summary.get("document_type", "Doc"))
    date_str = summary.get("date_filed", "NoDate")
    practice = "Legal"  # You can infer or customize this later

    new_filename = f"{client} - {doc_type} - {practice} - {date_str}{ext}"
    new_path = os.path.join(base_dir, new_filename)

    try:
        os.rename(file_path, new_path)
        print(f"\n📁 Renamed file to: {new_filename}")
        return new_path
    except Exception as e:
        print(f"❌ Could not rename file: {e}")
        return file_path

def extract_text(path):
    ext = os.path.splitext(path)[1].lower()

    if ext == ".txt":
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    elif ext == ".pdf":
        with pdfplumber.open(path) as pdf:
            return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

    elif ext in [".png", ".jpg", ".jpeg"]:
        from PIL import Image
        import pytesseract
        return pytesseract.image_to_string(Image.open(path))

    else:
        raise ValueError("Unsupported file type. Use .txt, .pdf, or image")


def normalize_entity(text):
    return re.sub(r"\s+", " ", text.strip().replace("\n", " ")).strip(",. ")

def build_summary(entities, filename, doc_type_from_nlp):
    # Use NLP-tagged document type
    doc_type = doc_type_from_nlp

    # Extract two parties
    parties = []
    for label in ["PERSON", "ORG"]:
        for item in entities.get(label, []):
            if len(item.split()) >= 2:
                parties.append(item)
            if len(parties) == 2:
                break
        if len(parties) == 2:
            break

    # Parse & filter valid dates
    filing_date = None
    parsed_dates = []
    for raw_date in entities.get("DATE", []):
        parsed = dateparser.parse(raw_date)
        if parsed and parsed.year >= 1900:
            parsed_dates.append(parsed)

    if parsed_dates:
        filing_date = min(parsed_dates).date().isoformat()

    return {
        "document_type": doc_type,
        "parties_involved": parties,
        "date_filed": filing_date
    }

def analyze_document(file_path):
    from pdfplumber import open as open_pdf
    from pdf2image import convert_from_path
    from pytesseract import image_to_string
    from PIL import Image
    import mimetypes

    ext = Path(file_path).suffix.lower()
    text = ""

    if ext == ".pdf":
        try:
            with open_pdf(file_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except:
            images = convert_from_path(file_path)
            text = "\n".join([image_to_string(img) for img in images])
    elif ext in [".png", ".jpg", ".jpeg"]:
        text = image_to_string(Image.open(file_path))
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

    doc = nlp(text)
    entity_summary = {}
    for ent in doc.ents:
        label = ent.label_
        entity_summary.setdefault(label, []).append(ent.text.strip())

    summary = {
        "document_type": doc._.document_type,
        "date_filed": next((ent.text for ent in doc.ents if ent.label_ == "DATE"), None),
        "entities": entity_summary
    }

    return {
        "text": text,
        "summary": summary,
        "entities": entity_summary
    }

def process_document(file_path, rename=False):
    result = analyze_document(file_path)
    summary = result["summary"]
    entities = result["entities"]

    print(f"\n📘 Processed: {file_path}")
    print("🧾 Entity Summary:\n")
    for label, items in entities.items():
        print(f"{label}: {items}")

    output_name = os.path.splitext(os.path.basename(file_path))[0]
    output_path = f"output/{output_name}_entities.json"
    os.makedirs("output", exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({
            "filename": os.path.basename(file_path),
            "summary": summary,
            "entities": entities
        }, f, indent=2)

    if rename:
        rename_file(file_path, summary)

    print(f"\n📌 Summary: {summary}")
    print(f"💾 Saved structured output to: {output_path}")

    return result

# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract and save entity summary from a .txt or .pdf document.")
    parser.add_argument("--file", required=True, help="Path to the input file")
    parser.add_argument("--rename", action="store_true", help="Rename the original file using summary metadata")
    args = parser.parse_args()

    process_document(args.file, args.rename)
