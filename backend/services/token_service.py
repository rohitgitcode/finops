import os
import hmac
import hashlib
import json
import base64
import time
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

SECRET_KEY = os.getenv("WEBHOOK_SECRET") or os.getenv("SECRET_KEY", "ledger_finops_token_secret_key_99x")

def generate_action_token(invoice_id: int, action: str, expires_in: int = 259200) -> str:
    """
    Generates a cryptographically signed URL-safe token encoding
    the invoice ID, desired review action (APPROVE/REJECT), and expiration.
    Default validity: 72 hours (259200 seconds).
    """
    data = {
        "invoice_id": int(invoice_id),
        "action": action.strip().upper(),
        "exp": int(time.time()) + expires_in
    }
    payload_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    
    return f"{payload_b64}.{sig_b64}"

def verify_action_token(token: str) -> dict | None:
    """
    Verifies the HMAC-SHA256 signature and expiration timestamp of an action token.
    Returns the parsed payload dict if valid, or None if tampered/expired.
    """
    try:
        if not token or "." not in token:
            return None

        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, sig_b64 = parts

        # Re-pad base64 strings
        payload_pad = payload_b64 + "=" * (-len(payload_b64) % 4)
        sig_pad = sig_b64 + "=" * (-len(sig_b64) % 4)

        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).digest()
        provided_sig = base64.urlsafe_b64decode(sig_pad)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = base64.urlsafe_b64decode(payload_pad)
        data = json.loads(payload_bytes.decode("utf-8"))

        if time.time() > data.get("exp", 0):
            return None

        return data
    except Exception:
        return None

