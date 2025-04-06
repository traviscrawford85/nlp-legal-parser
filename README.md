# ⚖️ NLP Legal Document Parser

This project is a modular, NLP-powered tool for parsing legal documents (PDFs or text files), extracting structured information, and automatically renaming the files using a standardized naming convention based on document content.

Built for legal professionals and law firms using tools like **Clio**, this script uses **spaCy**, **pdfplumber**, and **dateparser** to provide structure, metadata, and automation.

---

## 🚀 Features

- ✅ Named Entity Recognition (NER) using spaCy (`en_core_web_sm`)
- ✅ Smart `document_type` detection via custom NLP pipeline component
- ✅ Summary metadata including:
  - Detected document type
  - Involved parties (people or organizations)
  - Earliest valid date
- ✅ Automatic file renaming based on extracted info
- ✅ JSON export of structured metadata for tagging, indexing, and audit trails
- 🔜 Future support for Clio field mapping, YAML output, and batch processing

---

## ✅ Install spaCy Model
```bash
python -m spacy download en_core_web_sm
```
## 🧰 Usage
```bash
python process_file.py --file "./legal/Motion to Vacate.pdf" --rename
```

## Optional flags:
* --rename will rename the input file based on a summary metadata

## 🧾 Example Output
#### Renamed file:
```yaml
Johnathan Mitchell - Motion - Legal - 2022-07-01.pdf
```
## Structured summary (saved to output/*.json):
```json
 {
  "filename": "Motion to Vacate.pdf",
  "summary": {
    "document_type": "Motion",
    "parties_involved": ["Johnathan Mitchell", "Hunter Warfield"],
    "date_filed": "2022-07-01"
  },
  "entities": {
    "PERSON": [...],
    "ORG": [...],
    "DATE": [...],
    ...
  }
}
```

## 📦 Requirements
#### Install dependancies with:
```bash
pip install -r requirements.txt
```

### 📌 Roadmap
 * Clio field sync (e.g. Matter.Client.Name)

 * Batch folder mode

 * YAML export format

 * PDF table parsing for billing/medical records

 * Document classifier model integration

 ## 👤 Author
Travis Crawford <br>
Legal IT Specialist & Automation Developer
solutionpartner@cfelab.com
[LinkedIn](https://www.linkedin.com/in/crawford-t)
