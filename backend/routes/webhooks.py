import os
from fastapi import APIRouter, UploadFile, File, Header, HTTPException, status
from services.file_service import save_temp_file, cleanup_temp_dir
from services.agent_service import execute_full_invoice_pipeline

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

@router.post("/inbound-invoice", summary="Inbound invoice webhook ingestion")
async def inbound_invoice_webhook(
    file: UploadFile = File(...),
    x_webhook_secret: str = Header(None, alias="X-Webhook-Secret")
):
    """
    Automated webhook receiver for programmatic or third-party invoice pushes.
    Requires valid X-Webhook-Secret header to guard against spam and quota exhaustion.
    Buffers incoming PDF, runs full FinOps multi-agent pipeline, and returns audit resolution.
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
        pipeline_output = execute_full_invoice_pipeline(
            file_path=temp_file_path,
            context_label=f"Inbound webhook ingestion: {file.filename}"
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
