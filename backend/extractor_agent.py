import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader

# Load .env from backend directory or parent
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not defined in the environment or .env file.")

client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "openai/gpt-oss-120b"

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_number": {
            "type": "string",
            "description": "Invoice number or identifier found in the document. Default to 'N/A' if completely missing."
        },
        "vendor_name": {
            "type": "string",
            "description": "The issuing company, vendor, or service provider name (NOT the customer/billed-to person)."
        },
        "category": {
            "type": "string",
            "enum": ["Cloud & Infra", "Software", "Travel", "Meals", "Office Supplies", "Other"],
            "description": "Primary expense category based on line items."
        },
        "amount": {
            "type": "number",
            "description": "Final total payable invoice amount as a numeric float. Strip all currency signs ($ or INR) and commas."
        },
        "invoice_date": {
            "type": "string",
            "description": "Date of the invoice normalized strictly into YYYY-MM-DD format."
        }
    },
    "required": ["invoice_number", "vendor_name", "category", "amount", "invoice_date"],
    "additionalProperties": False
}

def parse_pdf_to_text(pdf_path: str) -> str:
    """
    Robust multi-tiered text extraction across all pages of a PDF:
    Tier 1: PyMuPDF (pymupdf) with sort=True. Preserves 2D layout and extracts
            interactive AcroForm/Widget fields (crucial for fillable invoices).
    Tier 2: pypdf with both content streams and reader.get_form_text_fields().
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found at path: {pdf_path}")

    # Tier 1: Try PyMuPDF
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        pages = []
        for page in doc:
            t = page.get_text("text", sort=True)
            if t and t.strip():
                pages.append(t)
        full_text = "\n\n".join(pages).strip()
        if full_text and len(full_text) > 30:
            return full_text
    except Exception:
        pass

    # Tier 2: Fallback to pypdf (with interactive AcroForm field support)
    try:
        reader = PdfReader(pdf_path)
        extracted_pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_pages.append(text)

        # Extract interactive form fields if present
        try:
            form_fields = reader.get_form_text_fields()
            if form_fields:
                form_text = "\n".join([f"{k}: {v}" for k, v in form_fields.items() if v])
                extracted_pages.append(f"\n--- Form Fields ---\n{form_text}")
        except Exception:
            pass

        full_text = "\n".join(extracted_pages).strip()
        if full_text:
            return full_text
    except Exception:
        pass

    return ""

def extract_invoice_data(raw_text: str) -> dict:
    """
    Parse unstructured invoice text into a verified structured dictionary
    using Groq's constrained JSON schema.
    """
    system_prompt = (
        "You are an enterprise Accounts Payable and Document Perception Agent. "
        "Your task is to carefully extract 5 core invoice parameters from messy OCR/PDF text:\n"
        "1. invoice_number: Locate strings following 'Invoice No', 'Invoice Number', or isolated numerical identifiers.\n"
        "2. vendor_name: Identify the company issuing the bill (issuer/vendor), NOT the client listed in 'Billed To'.\n"
        "3. category: Classify the spend into one of: 'Cloud & Infra', 'Software', 'Travel', 'Meals', 'Office Supplies', 'Other'.\n"
        "4. amount: Find the final 'Total' or 'Invoice Total'. Output pure numeric value without currency symbols.\n"
        "5. invoice_date: Convert dates like '03/31/2026' or 'March 31 2026' to ISO standard 'YYYY-MM-DD'.\n\n"
        "Do not leave fields blank. Extract accurately from the text."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Invoice Document Content:\n{raw_text}"}
    ]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "invoice_extraction",
                "schema": EXTRACTION_SCHEMA,
                "strict": True
            }
        },
        temperature=0.1
    )

    return json.loads(response.choices[0].message.content)

def process_invoice_file(file_path: str) -> dict:
    """End-to-end ingestion pipeline."""
    raw_text = parse_pdf_to_text(file_path)
    if not raw_text.strip():
        raise ValueError("No extractable text found in the PDF.")
    
    return extract_invoice_data(raw_text)