import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """Establish and return a connection to the PostgreSQL database."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in the environment or .env file.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Alias for connection function
get_db_connection = get_connection

def update_invoice_review(invoice_id: int, new_status: str, reviewer_note: str) -> bool:
    """
    Update the verification status of an invoice and append an immutable audit log.
    Action: 'MANUAL_APPROVAL_OVERRIDE' if new_status is 'APPROVED' else 'MANUAL_REJECTION_VOID'.
    Notes: f"Manager Review: {reviewer_note}"
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Update invoice status
        cursor.execute(
            """
            UPDATE invoices 
            SET status = %s 
            WHERE id = %s;
            """,
            (new_status, invoice_id)
        )

        # 2. Append immutable audit log
        action_label = (
            "MANUAL_APPROVAL_OVERRIDE" 
            if new_status == "APPROVED" 
            else "MANUAL_REJECTION_VOID"
        )
        note_clean = reviewer_note.strip() if reviewer_note else "No override justification provided"
        reasoning_text = f"Manager Review: {note_clean}"

        cursor.execute(
            """
            INSERT INTO audit_logs (invoice_id, agent_name, action_taken, action, notes, reasoning)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (invoice_id, "HumanReviewer", action_label, action_label, reasoning_text, reasoning_text)
        )

        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Database error during invoice review update: {str(exc)}")
    finally:
        cursor.close()
        conn.close()

def init_db():
    """
    Locates and reads backend/schema.sql and applies non-destructive DDL
    migrations and index creation to PostgreSQL NeonDB.
    """
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at path: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(schema_sql)
        conn.commit()
        print("[Database] Schema synchronized successfully.")
    except Exception as exc:
        conn.rollback()
        print(f"[Database] Schema synchronization failed: {str(exc)}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_db()
