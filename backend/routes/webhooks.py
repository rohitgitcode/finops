import os
from fastapi import APIRouter, UploadFile, File, Header, HTTPException, status, BackgroundTasks, Request
from services.file_service import save_temp_file, cleanup_temp_dir
from services.agent_service import execute_full_invoice_pipeline
from services.notification_service import send_quarantined_invoice_alert

try:
    from limiter import limiter
except (ImportError, ModuleNotFoundError):
    from backend.limiter import limiter

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

@router.post("/inbound-invoice", summary="Inbound invoice webhook ingestion")
@limiter.limit("10/minute")
async def inbound_invoice_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_webhook_secret: str = Header(None, alias="X-Webhook-Secret")
):
    """
    Automated webhook receiver for programmatic or third-party invoice pushes.
    Requires valid X-Webhook-Secret header to guard against spam and quota exhaustion.
    Buffers incoming PDF, runs full FinOps multi-agent pipeline, dispatches high-risk alerts,
    and returns audit resolution.
    """
    expected_secret = os.getenv("WEBHOOK_SECRET")
    if expected_secret:
        if not x_webhook_secret or x_webhook_secret.strip() != expected_secret.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Invalid or missing webhook secret."
            )

    temp_file_path, temp_dir = save_temp_file(file)

    try:
        # Buffer PDF bytes into memory before cleanup for email attachment
        with open(temp_file_path, "rb") as f:
            pdf_bytes = list(f.read())

        pipeline_output = execute_full_invoice_pipeline(
            file_path=temp_file_path,
            context_label=f"Inbound webhook ingestion: {file.filename}"
        )

        extracted_data = pipeline_output.get("extracted_data", {})
        audit_report = pipeline_output.get("audit_report", {})
        resolution = pipeline_output.get("resolution", {})

        risk_score = audit_report.get("risk_score", 0)
        status_val = resolution.get("final_status", "") or audit_report.get("recommended_status", "")

        is_quarantined = status_val.upper() in ["QUARANTINED", "PENDING_APPROVAL", "FLAGGED", "NEEDS_REVIEW"]
        
        # Dispatch alert if quarantined or risk threshold breached
        if is_quarantined or risk_score >= 70:
            flags_list = audit_report.get("audit_flags", [])
            flag_reason = " | ".join(flags_list) if flags_list else (audit_report.get("flag_reason") or "Audit risk threshold exceeded")
            invoice_id = resolution.get("invoice_id")
            background_tasks.add_task(
                send_quarantined_invoice_alert,
                invoice_data=extracted_data,
                flag_reason=flag_reason,
                risk_score=risk_score,
                pdf_bytes=pdf_bytes,
                filename=file.filename,
                invoice_id=invoice_id
            )

        return {
            "success": True,
            "channel": "webhook",
            "filename": file.filename,
            **pipeline_output
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook pipeline failure: {str(exc)}"
        )
    finally:
        cleanup_temp_dir(temp_dir)