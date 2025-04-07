import spacy
import os
import pdfplumber
import json
from collections import defaultdict
import re
import dateparser
from datetime import datetime
from spacy.language import Language
from spacy.tokens import Doc

# Load spaCy model globally
nlp = spacy.load("en_core_web_sm")

# Add custom Doc attribute
Doc.set_extension("document_type", default="Unknown")

@Language.component("document_type_detector")
def document_type_detector(doc):
    lowered = doc.text.lower()
    match = None

    if "motion to dismiss" in lowered:
        match = "Motion to Dismiss"
    elif "motion" in lowered:
        match = "Motion"
    elif "affidavit" in lowered:
        match = "Affidavit"
    elif "complaint" in lowered:
        match = "Complaint"
    elif "notice of hearing" in lowered:
        match = "Notice of Hearing"
    else:
        match = "Unknown"

    doc._.document_type = match
    print(f"🔍 Detected document type: {match}")
    return doc

# Register component in spaCy pipeline
nlp.add_pipe("document_type_detector", last=True)

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
    
    else:
        raise ValueError("Unsupported file type. Use .txt or .pdf")

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

def process_document(file_path, rename=False):
    text = extract_text(file_path)
    doc = nlp(text)

    entity_summary = defaultdict(list)
    for ent in doc.ents:
        clean = normalize_entity(ent.text)
        if clean:
            entity_summary[ent.label_].append(clean)

    # De-duplicate and sort
    entity_summary = {
        k: sorted(set(v)) for k, v in entity_summary.items()
    }

    summary = build_summary(entity_summary, os.path.basename(file_path), doc._.document_type)

    print(f"\n📘 Processed: {file_path}")
    print("🧾 Entity Summary:\n")
    for label, items in entity_summary.items():
        print(f"{label}: {items}")

    output_name = os.path.splitext(os.path.basename(file_path))[0]
    output_path = f"output/{output_name}_entities.json"
    os.makedirs("output", exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({
            "filename": os.path.basename(file_path),
            "summary": summary,
            "entities": entity_summary
        }, f, indent=2)
    if rename:
        rename_file(file_path, summary)

    print(f"\n📌 Summary: {summary}")
    print(f"💾 Saved structured output to: {output_path}")
    

# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract and save entity summary from a .txt or .pdf document.")
    parser.add_argument("--file", required=True, help="Path to the input file")
    parser.add_argument("--rename", action="store_true", help="Rename the original file using summary metadata")
    args = parser.parse_args()

    process_document(args.file)
