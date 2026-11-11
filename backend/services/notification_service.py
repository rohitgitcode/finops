import os
from pathlib import Path
import resend
from dotenv import load_dotenv

# Ensure environment variables are loaded regardless of how or where module is imported
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")

def send_quarantined_invoice_alert(
    invoice_data: dict,
    flag_reason: str,
    risk_score: int,
    pdf_bytes: list = None,
    filename: str = None,
    invoice_id: int = None
):
    """
    Sends an automated email notification via Resend with the flagged PDF attached
    whenever an invoice is quarantined or exceeds risk thresholds.
    Includes cryptographically signed One-Click Decision action buttons.
    """
    # Re-verify credentials in case env loaded dynamically
    api_key = os.getenv("RESEND_API_KEY")
    recipient = os.getenv("MANAGER_ALERT_EMAIL")

    if not api_key:
        print("[Notification Error] RESEND_API_KEY is missing from environment.")
        return None

    if not recipient:
        print("[Notification Error] MANAGER_ALERT_EMAIL is missing from environment.")
        return None

    resend.api_key = api_key

    invoice_data = invoice_data or {}
    vendor = invoice_data.get("vendor_name", "Unknown Vendor")
    inv_num = invoice_data.get("invoice_number", "N/A")
    amount = invoice_data.get("amount", 0.0)

    try:
        formatted_amount = f"INR {float(amount):,.2f}"
    except (ValueError, TypeError):
        formatted_amount = f"INR {amount}"

    flag_text = flag_reason or "Audit risk threshold exceeded"

    # Generate one-click action buttons if invoice ID is available
    resolved_id = invoice_id or invoice_data.get("id") or invoice_data.get("invoice_id")
    action_block = ""
    if resolved_id:
        try:
            from services.token_service import generate_action_token
        except (ImportError, ModuleNotFoundError):
            from backend.services.token_service import generate_action_token

        base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        approve_token = generate_action_token(resolved_id, "APPROVE")
        reject_token = generate_action_token(resolved_id, "REJECT")
        approve_url = f"{base_url}/api/v1/invoices/action?token={approve_token}"
        reject_url = f"{base_url}/api/v1/invoices/action?token={reject_token}"

        action_block = f"""
        <div style="margin: 24px 0 16px 0; padding: 20px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; text-align: center;">
            <p style="margin: 0 0 14px 0; font-size: 13px; font-weight: 600; color: #334155; text-transform: uppercase; letter-spacing: 0.5px;">
                One-Click Human-in-the-Loop Action
            </p>
            <div style="display: inline-block;">
                <a href="{approve_url}" target="_blank" style="display: inline-block; padding: 10px 24px; margin-right: 12px; background-color: #166534; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px;">
                    Approve Invoice
                </a>
                <a href="{reject_url}" target="_blank" style="display: inline-block; padding: 10px 24px; background-color: #991b1b; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px;">
                    Reject Invoice
                </a>
            </div>
            <p style="margin: 14px 0 0 0; font-size: 11px; color: #64748b;">
                Links are securely signed and valid for 72 hours. Clicking immediately commits the audit resolution.
            </p>
        </div>
        """

    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 24px; border: 1px solid #e0e0e0; border-radius: 8px; max-width: 600px; color: #202124;">
        <h2 style="color: #d93025; margin-top: 0; font-size: 20px;">[Risk Alert] High-Risk Invoice Quarantined</h2>
        <p style="font-size: 14px; line-height: 1.5; color: #3c4043;">
            The Autonomous FinOps Auditor has intercepted and quarantined an inbound invoice requiring manual governance review.
        </p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
            <tr style="border-bottom: 1px solid #eeeeee;">
                <td style="padding: 10px 0; font-weight: bold; width: 140px; color: #5f6368;">Invoice Number:</td>
                <td style="padding: 10px 0; font-weight: bold;">{inv_num}</td>
            </tr>
            <tr style="border-bottom: 1px solid #eeeeee;">
                <td style="padding: 10px 0; font-weight: bold; color: #5f6368;">Vendor:</td>
                <td style="padding: 10px 0;">{vendor}</td>
            </tr>
            <tr style="border-bottom: 1px solid #eeeeee;">
                <td style="padding: 10px 0; font-weight: bold; color: #5f6368;">Amount:</td>
                <td style="padding: 10px 0; font-weight: bold;">{formatted_amount}</td>
            </tr>
            <tr style="border-bottom: 1px solid #eeeeee;">
                <td style="padding: 10px 0; font-weight: bold; color: #5f6368;">Risk Score:</td>
                <td style="padding: 10px 0; color: #d93025; font-weight: bold;">{risk_score} / 100</td>
            </tr>
            <tr style="border-bottom: 1px solid #eeeeee;">
                <td style="padding: 10px 0; font-weight: bold; color: #5f6368;">Audit Reason:</td>
                <td style="padding: 10px 0; color: #b00020; font-weight: 500;">{flag_text}</td>
            </tr>
        </table>
        
        {action_block}

        <p style="font-size: 13px; color: #5f6368; line-height: 1.4;">
            The original PDF is attached to this email. Please review and verify this transaction in your LedgerMind dashboard.
        </p>
    </div>
    """

    params = {
        "from": "onboarding@resend.dev",
        "to": [recipient],
        "subject": f"[ALERT] Quarantined Invoice #{inv_num} - {vendor}",
        "html": html_content
    }

    if pdf_bytes:
        params["attachments"] = [
            {
                "filename": filename or f"quarantined_{inv_num}.pdf",
                "content": list(pdf_bytes) if isinstance(pdf_bytes, (bytes, bytearray)) else pdf_bytes
            }
        ]

    try:
        response = resend.Emails.send(params)
        print(f"[Notification Sent] Alert email dispatched to {recipient}. ID: {response.get('id') if isinstance(response, dict) else response}")
        return response
    except Exception as e:
        print(f"[Notification Error] Resend API failed: {str(e)}")
        return None