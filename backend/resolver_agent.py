import json
from typing import Dict, Any
from ledger_db import get_connection

class ResolutionAgent:
    """
    Action and settlement agent responsible for persisting finalized invoice 
    evaluations into the PostgreSQL database and committing an immutable audit trail.
    """

    def __init__(self):
        pass

    def record_decision(self, extracted_data: Dict[str, Any], audit_result: Dict[str, Any], raw_text: str = "", file_hash: str = None) -> Dict[str, Any]:
        """
        Persists the invoice state and records the decision history in the audit logs.
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            status = audit_result.get("recommended_status", "PENDING_AUDIT")
            risk_score = audit_result.get("risk_score", 0)
            flag_reasons = " | ".join(audit_result.get("audit_flags", []))

            # 1. Insert into invoices table
            insert_invoice_query = """
            INSERT INTO invoices (
                invoice_number, 
                vendor_name, 
                category, 
                amount, 
                invoice_date, 
                status, 
                risk_score, 
                flag_reason, 
                raw_text,
                file_hash
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, invoice_number, status, created_at;
            """
            cursor.execute(
                insert_invoice_query,
                (
                    extracted_data["invoice_number"],
                    extracted_data["vendor_name"],
                    extracted_data["category"],
                    extracted_data["amount"],
                    extracted_data["invoice_date"],
                    status,
                    risk_score,
                    flag_reasons,
                    raw_text,
                    file_hash
                )
            )
            new_invoice = cursor.fetchone()
            invoice_id = new_invoice["id"]

            # 2. Record immutable audit log
            action_label = "INVOICE_APPROVED" if status == "APPROVED" else f"INVOICE_{status}"
            insert_log_query = """
            INSERT INTO audit_logs (invoice_id, agent_name, action_taken, reasoning)
            VALUES (%s, %s, %s, %s);
            """
            reasoning_summary = json.dumps({
                "risk_score": risk_score,
                "flags": audit_result.get("audit_flags", [])
            })
            cursor.execute(
                insert_log_query,
                (invoice_id, "Auditor+ResolverPipeline", action_label, reasoning_summary)
            )

            conn.commit()

            return {
                "success": True,
                "invoice_id": invoice_id,
                "invoice_number": new_invoice["invoice_number"],
                "final_status": new_invoice["status"],
                "risk_score": risk_score,
                "action_logged": action_label,
                "flags": audit_result.get("audit_flags", [])
            }

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Database transaction failure during invoice resolution: {str(e)}")
        finally:
            cursor.close()
            conn.close()