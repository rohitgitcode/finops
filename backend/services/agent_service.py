from typing import Dict, Any
from extractor_agent import process_invoice_file
from auditor_agent import AuditorAgent
from resolver_agent import ResolutionAgent

# Singletons for agent workflows
auditor = AuditorAgent()
resolver = ResolutionAgent()

def execute_full_invoice_pipeline(file_path: str, context_label: str) -> Dict[str, Any]:
    """
    Executes the multi-agent finops pipeline:
    1. Extractor Agent: Ingests PDF and extracts structured data via Groq LLM.
    2. Auditor Agent: Validates against PostgreSQL ledger policies and duplicate checks.
    3. Resolution Agent: Persists decision to master ledger and creates immutable audit log.

    Returns:
        Dict[str, Any]: {
            "extracted_data": dict,
            "audit_report": dict,
            "resolution": dict
        }
    """
    # Stage 1: Extraction & Perception
    extracted_data = process_invoice_file(file_path)

    # Stage 2: Audit & Policy Validation
    audit_result = auditor.audit_invoice(extracted_data)

    # Stage 3: Resolution & Master Ledger Persistence
    resolution_result = resolver.record_decision(
        extracted_data=extracted_data,
        audit_result=audit_result,
        raw_text=context_label
    )

    return {
        "extracted_data": extracted_data,
        "audit_report": audit_result,
        "resolution": resolution_result
    }

