import os
import shutil
import tempfile
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from extractor_agent import process_invoice_file
from auditor_agent import AuditorAgent
from resolver_agent import ResolutionAgent
from ledger_db import get_connection

app = FastAPI(
    title="LedgerMind Autonomous FinOps Engine",
    description="Multi-agent invoice extraction, audit, and reconciliation pipeline.",
    version="1.0.0"
)

# Enable CORS for local and staging frontends (e.g., Vue 3 dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auditor = AuditorAgent()
resolver = ResolutionAgent()

@app.get("/")
def health_check():
    return {
        "status": "online",
        "system": "LedgerMind FinOps Engine",
        "database": "PostgreSQL (Neon Connected)"
    }

@app.get("/api/invoices")
def get_all_invoices():
    """Retrieve all logged invoices and their current verification status."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, invoice_number, vendor_name, category, amount, 
                   invoice_date, status, risk_score, flag_reason, created_at 
            FROM invoices 
            ORDER BY id DESC;
        """)
        records = cursor.fetchall()
        return {"total": len(records), "invoices": records}
    finally:
        cursor.close()
        conn.close()

@app.post("/api/invoices/upload")
async def upload_and_process_invoice(file: UploadFile = File(...)):
    """
    Complete end-to-end multi-agent orchestration pipeline:
    1. Ingestion: Reads incoming PDF.
    2. Extractor Agent: Extracts structured JSON via Groq LLM schema.
    3. Auditor Agent: Validates against PostgreSQL ledger & spending policies.
    4. Resolution Agent: Persists verified record and writes immutable audit logs.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents are supported."
        )

    # Save uploaded file to a temporary secure path for processing
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Stage 1: Extraction
        extracted_data = process_invoice_file(temp_file_path)

        # Stage 2: Audit & Cross-referencing
        audit_result = auditor.audit_invoice(extracted_data)

        # Stage 3: Resolution & Persistence
        resolution_result = resolver.record_decision(
            extracted_data=extracted_data,
            audit_result=audit_result,
            raw_text=f"Processed binary file: {file.filename}"
        )

        return {
            "success": True,
            "filename": file.filename,
            "extracted_data": extracted_data,
            "audit_report": audit_result,
            "resolution": resolution_result
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent pipeline failure: {str(exc)}"
        )
    finally:
        # Clean up temporary file artifact
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)