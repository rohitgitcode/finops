import hashlib
from typing import Dict, Any

try:
    from extractor_agent import process_invoice_file
    from auditor_agent import AuditorAgent
    from resolver_agent import ResolutionAgent
    from ledger_db import get_invoice_by_hash
except (ImportError, ModuleNotFoundError):
    from backend.extractor_agent import process_invoice_file
    from backend.auditor_agent import AuditorAgent
    from backend.resolver_agent import ResolutionAgent
    from backend.ledger_db import get_invoice_by_hash

# Singletons for agent workflows
auditor = AuditorAgent()
resolver = ResolutionAgent()

def execute_full_invoice_pipeline(file_path: str, context_label: str) -> Dict[str, Any]:
    """
    Executes the multi-agent finops pipeline with zero-compute SHA-256 duplicate interception:
    0. Idempotency Check: Computes binary SHA-256 hash. If duplicate exists in ledger,
       bypasses Groq LLM and Extractor Agent completely with Risk Score 100.
    1. Extractor Agent: Ingests PDF and extracts structured data via Groq LLM (if unique).
    2. Auditor Agent: Validates against PostgreSQL ledger policies and duplicate checks.
    3. Resolution Agent: Persists decision to master ledger and creates immutable audit log.

    Returns:
        Dict[str, Any]: {
            "extracted_data": dict,
            "audit_report": dict,
            "resolution": dict,
            "bypassed_llm": bool,
            "file_hash": str
        }
    """
    # 0. Zero-Compute Pre-Perception SHA-256 Binary Check
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    existing_invoice = get_invoice_by_hash(file_hash)
    if existing_invoice:
        # Exact binary match found: Bypass LLM to save token costs and prevent fraud
        extracted_data = {
            "invoice_number": existing_invoice.get("invoice_number", "UNKNOWN_DUPLICATE"),
            "vendor_name": existing_invoice.get("vendor_name", "Unknown Vendor"),
            "category": existing_invoice.get("category", "General Expense"),
            "amount": float(existing_invoice.get("amount", 0.0)),
            "invoice_date": str(existing_invoice.get("invoice_date", "")),
        }

        audit_result = {
            "invoice_number": extracted_data["invoice_number"],
            "vendor_name": extracted_data["vendor_name"],
            "category": extracted_data["category"],
            "amount": extracted_data["amount"],
            "risk_score": 100,
            "recommended_status": "QUARANTINED",
            "audit_flags": [
                f"Exact binary duplicate file detected. SHA-256 match with Ledger Record #{existing_invoice['id']} (Invoice #{existing_invoice['invoice_number']}). Groq LLM extraction bypassed."
            ]
        }

        resolution_result = resolver.record_decision(
            extracted_data=extracted_data,
            audit_result=audit_result,
            raw_text=f"Exact binary duplicate intercepted before LLM extraction. Hash: {file_hash} | {context_label}",
            file_hash=file_hash
        )

        return {
            "extracted_data": extracted_data,
            "audit_report": audit_result,
            "resolution": resolution_result,
            "bypassed_llm": True,
            "file_hash": file_hash
        }

    # Stage 1: Extraction & Perception (Unique file)
    extracted_data = process_invoice_file(file_path)

    # Stage 2: Audit & Policy Validation
    audit_result = auditor.audit_invoice(extracted_data)

    # Stage 3: Resolution & Master Ledger Persistence
    resolution_result = resolver.record_decision(
        extracted_data=extracted_data,
        audit_result=audit_result,
        raw_text=context_label,
        file_hash=file_hash
    )

    return {
        "extracted_data": extracted_data,
        "audit_report": audit_result,
        "resolution": resolution_result,
        "bypassed_llm": False,
        "file_hash": file_hash
    }

