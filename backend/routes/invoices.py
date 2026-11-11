from fastapi import APIRouter, UploadFile, File, HTTPException, status
from schemas import ReviewRequest
from services.file_service import save_temp_file, cleanup_temp_dir
from services.agent_service import execute_full_invoice_pipeline
from ledger_db import get_connection, update_invoice_review

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

@router.get("", summary="Retrieve all ledger invoices")
@router.get("/", include_in_schema=False)
def get_all_invoices():
    """Retrieve all logged invoices and their current verification status from PostgreSQL."""
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

@router.post("/upload", summary="Upload and process invoice PDF")
async def upload_and_process_invoice(file: UploadFile = File(...)):
    """
    Complete multi-agent invoice ingestion pipeline:
    1. Ingestion: Buffers incoming PDF via file_service.
    2. Execution: Runs extraction, audit, and resolution via agent_service.
    3. Cleanup: Safely removes temporary file artifact.
    """
    temp_file_path, temp_dir = save_temp_file(file)

    try:
        pipeline_output = execute_full_invoice_pipeline(
            file_path=temp_file_path,
            context_label=f"Processed binary file: {file.filename}"
        )

        return {
            "success": True,
            "filename": file.filename,
            **pipeline_output
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent pipeline failure: {str(exc)}"
        )
    finally:
        cleanup_temp_dir(temp_dir)

@router.post("/{invoice_id}/review", summary="Human-in-the-loop review decision")
def review_invoice(invoice_id: int, payload: ReviewRequest):
    """
    Human-in-the-Loop review endpoint:
    Allows finops managers to manually override or reject invoices.
    Maps 'APPROVE' -> 'APPROVED' and 'REJECT' -> 'REJECTED'.
    """
    action_clean = payload.action.strip().upper()
    if action_clean not in ("APPROVE", "REJECT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review action. Allowed values are strictly 'APPROVE' or 'REJECT'."
        )

    new_status = "APPROVED" if action_clean == "APPROVE" else "REJECTED"

    try:
        update_invoice_review(
            invoice_id=invoice_id,
            new_status=new_status,
            reviewer_note=payload.notes
        )
        return {
            "success": True,
            "invoice_id": invoice_id,
            "new_status": new_status,
            "notes": payload.notes
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record manual review: {str(exc)}"
        )

