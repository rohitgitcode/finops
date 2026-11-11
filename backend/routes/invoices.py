from fastapi import APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks, Request, Query
from fastapi.responses import HTMLResponse

try:
    from schemas import ReviewRequest, DecisionNote
    from services.file_service import save_temp_file, cleanup_temp_dir
    from services.agent_service import execute_full_invoice_pipeline
    from services.notification_service import send_quarantined_invoice_alert
    from services.token_service import verify_action_token
    from ledger_db import get_connection, update_invoice_review, get_invoice_by_id
    from limiter import limiter
except (ImportError, ModuleNotFoundError):
    from backend.schemas import ReviewRequest, DecisionNote
    from backend.services.file_service import save_temp_file, cleanup_temp_dir
    from backend.services.agent_service import execute_full_invoice_pipeline
    from backend.services.notification_service import send_quarantined_invoice_alert
    from backend.services.token_service import verify_action_token
    from backend.ledger_db import get_connection, update_invoice_review, get_invoice_by_id
    from backend.limiter import limiter

router = APIRouter(tags=["Invoices"])

def render_action_html(
    title: str,
    status_label: str,
    status_color: str,
    message: str,
    invoice: dict = None
) -> str:
    inv_num = invoice.get("invoice_number", "N/A") if invoice else "N/A"
    vendor = invoice.get("vendor_name", "N/A") if invoice else "N/A"
    amount = invoice.get("amount", 0.0) if invoice else 0.0
    try:
        formatted_amount = f"INR {float(amount):,.2f}"
    except (ValueError, TypeError):
        formatted_amount = f"INR {amount}"

    details_table = ""
    if invoice:
        details_table = f"""
        <table style="width: 100%; border-collapse: collapse; margin: 24px 0; font-size: 14px; text-align: left;">
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 10px 0; color: #64748b; font-weight: 500;">Invoice Number</td>
                <td style="padding: 10px 0; font-weight: 600; color: #0f172a;">{inv_num}</td>
            </tr>
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 10px 0; color: #64748b; font-weight: 500;">Vendor</td>
                <td style="padding: 10px 0; color: #0f172a;">{vendor}</td>
            </tr>
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 10px 0; color: #64748b; font-weight: 500;">Amount</td>
                <td style="padding: 10px 0; font-weight: 600; color: #0f172a;">{formatted_amount}</td>
            </tr>
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 10px 0; color: #64748b; font-weight: 500;">Decision</td>
                <td style="padding: 10px 0; font-weight: 600; color: {status_color};">{status_label}</td>
            </tr>
        </table>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - LedgerMind FinOps</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8fafc;
            margin: 0;
            padding: 40px 20px;
            color: #0f172a;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 80vh;
        }}
        .card {{
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            max-width: 500px;
            width: 100%;
            padding: 36px 32px;
            text-align: center;
        }}
        .badge {{
            display: inline-block;
            padding: 6px 16px;
            font-size: 12px;
            font-weight: 700;
            border-radius: 20px;
            color: #ffffff;
            background-color: {status_color};
            margin-bottom: 16px;
            letter-spacing: 0.5px;
        }}
        .title {{
            font-size: 20px;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 10px 0;
        }}
        .message {{
            font-size: 14px;
            color: #475569;
            line-height: 1.6;
            margin: 0 0 16px 0;
        }}
        .footer-note {{
            font-size: 12px;
            color: #94a3b8;
            margin-top: 24px;
            border-top: 1px solid #f1f5f9;
            padding-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">{status_label}</span>
        <h1 class="title">{title}</h1>
        <p class="message">{message}</p>
        {details_table}
        <div class="footer-note">
            LedgerMind Autonomous FinOps &bull; Immutable Audit Trail Committed
        </div>
    </div>
</body>
</html>"""

@router.get("", summary="Retrieve all ledger invoices")
@router.get("/", include_in_schema=False)
@limiter.limit("60/minute")
def get_all_invoices(request: Request):
    """Retrieve all logged invoices and their current verification status from PostgreSQL."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, invoice_number, vendor_name, category, amount, 
                   invoice_date, status, risk_score, flag_reason, file_hash, created_at 
            FROM invoices 
            ORDER BY id DESC;
        """)
        records = cursor.fetchall()
        return {"total": len(records), "invoices": records}
    finally:
        cursor.close()
        conn.close()

@router.post("/upload", summary="Upload and process invoice PDF")
@limiter.limit("10/minute")
async def upload_and_process_invoice(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Complete multi-agent invoice ingestion pipeline:
    1. Ingestion: Buffers incoming PDF via file_service.
    2. Execution: Runs extraction, audit, and resolution via agent_service.
    3. Notification: Dispatches high-risk / quarantined alerts via background tasks.
    4. Cleanup: Safely removes temporary file artifact.
    """
    temp_file_path, temp_dir = save_temp_file(file)

    try:
        pdf_bytes = None
        try:
            with open(temp_file_path, "rb") as f:
                pdf_bytes = list(f.read())
        except Exception as read_err:
            print(f"[File Buffer Warning] Could not buffer PDF for attachment: {read_err}")

        pipeline_output = execute_full_invoice_pipeline(
            file_path=temp_file_path,
            context_label=f"Processed binary file: {file.filename}"
        )

        extracted_data = pipeline_output.get("extracted_data", {})
        audit_report = pipeline_output.get("audit_report", {})
        resolution = pipeline_output.get("resolution", {})

        risk_score = audit_report.get("risk_score", 0)
        status_val = resolution.get("final_status", "") or audit_report.get("recommended_status", "")

        is_quarantined = status_val.upper() in ["QUARANTINED", "PENDING_APPROVAL", "FLAGGED", "NEEDS_REVIEW"]

        # Dispatch automated alert if quarantined or critical risk score exceeded
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

@router.get("/action", response_class=HTMLResponse, summary="One-click email review action")
@limiter.limit("30/minute")
def execute_email_action(request: Request, token: str = Query(...)):
    """
    Validates cryptographically signed action token and commits decision.
    Renders enterprise confirmation HTML page in manager's browser.
    """
    token_data = verify_action_token(token)
    if not token_data:
        return HTMLResponse(
            content=render_action_html(
                title="Action Link Invalid or Expired",
                status_label="INVALID TOKEN",
                status_color="#dc2626",
                message="This review token is corrupted, invalid, or expired (72-hour validity window exceeded). Please review the invoice directly from your LedgerMind dashboard."
            ),
            status_code=400
        )

    invoice_id = token_data.get("invoice_id")
    action = token_data.get("action", "").upper()

    invoice = get_invoice_by_id(invoice_id)
    if not invoice:
        return HTMLResponse(
            content=render_action_html(
                title="Invoice Record Not Found",
                status_label="NOT FOUND",
                status_color="#dc2626",
                message=f"No invoice matching Record ID #{invoice_id} could be found in the PostgreSQL ledger."
            ),
            status_code=404
        )

    current_status = invoice.get("status", "").upper()
    if current_status in ("APPROVED", "REJECTED"):
        return HTMLResponse(
            content=render_action_html(
                title="Invoice Already Settled",
                status_label=f"ALREADY {current_status}",
                status_color="#0284c7",
                message=f"Invoice #{invoice.get('invoice_number')} has already been finalized with status '{current_status}'. No redundant modifications were performed.",
                invoice=invoice
            ),
            status_code=200
        )

    new_status = "APPROVED" if action == "APPROVE" else "REJECTED"
    badge_color = "#16a34a" if new_status == "APPROVED" else "#dc2626"

    try:
        update_invoice_review(
            invoice_id=invoice_id,
            new_status=new_status,
            reviewer_note=f"Manager one-click action via secure email link ({action})"
        )
        invoice["status"] = new_status
        return HTMLResponse(
            content=render_action_html(
                title=f"Invoice Successfully {new_status}",
                status_label=new_status,
                status_color=badge_color,
                message=f"The status for invoice #{invoice.get('invoice_number')} has been committed to the master ledger and recorded in the immutable audit log.",
                invoice=invoice
            ),
            status_code=200
        )
    except Exception as exc:
        return HTMLResponse(
            content=render_action_html(
                title="Database Settlement Failed",
                status_label="SYSTEM ERROR",
                status_color="#dc2626",
                message=f"Failed to record review action in database: {str(exc)}",
                invoice=invoice
            ),
            status_code=500
        )

@router.post("/{invoice_id}/approve", summary="Direct programmatic invoice approval")
@limiter.limit("30/minute")
def approve_invoice_direct(
    request: Request,
    invoice_id: int,
    payload: DecisionNote = None
):
    """
    Direct REST endpoint to approve an invoice:
    Sets status to 'APPROVED' and records immutable audit log.
    """
    notes = payload.notes if payload and payload.notes else "Direct API Approval Decision"
    try:
        update_invoice_review(
            invoice_id=invoice_id,
            new_status="APPROVED",
            reviewer_note=notes
        )
        return {
            "success": True,
            "invoice_id": invoice_id,
            "new_status": "APPROVED",
            "action": "APPROVE",
            "notes": notes
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve invoice: {str(exc)}"
        )

@router.post("/{invoice_id}/reject", summary="Direct programmatic invoice rejection")
@limiter.limit("30/minute")
def reject_invoice_direct(
    request: Request,
    invoice_id: int,
    payload: DecisionNote = None
):
    """
    Direct REST endpoint to reject an invoice:
    Sets status to 'REJECTED' and records immutable audit log.
    """
    notes = payload.notes if payload and payload.notes else "Direct API Rejection Decision"
    try:
        update_invoice_review(
            invoice_id=invoice_id,
            new_status="REJECTED",
            reviewer_note=notes
        )
        return {
            "success": True,
            "invoice_id": invoice_id,
            "new_status": "REJECTED",
            "action": "REJECT",
            "notes": notes
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject invoice: {str(exc)}"
        )

@router.post("/{invoice_id}/review", summary="Human-in-the-loop review decision")
@limiter.limit("30/minute")
def review_invoice(request: Request, invoice_id: int, payload: ReviewRequest):
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

