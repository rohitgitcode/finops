import os
from typing import Dict, Any, Tuple
from dotenv import load_dotenv
from ledger_db import get_connection

load_dotenv()

class AuditorAgent:
    """
    Autonomous Auditor Agent responsible for cross-referencing extracted invoice
    data against the PostgreSQL ledger and compliance policy rules.
    """

    def __init__(self):
        pass

    def check_duplicate_invoice(self, invoice_number: str, vendor_name: str, amount: float) -> Tuple[bool, str]:
        """
        Check if an exact invoice number exists, or if a duplicate charge 
        (same vendor and exact amount) is already recorded in the database.
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # 1. Exact invoice reference match
            cursor.execute(
                "SELECT id, invoice_number, status FROM invoices WHERE invoice_number = %s;",
                (invoice_number,)
            )
            exact_match = cursor.fetchone()
            if exact_match:
                return True, f"Critical: Duplicate invoice number '{invoice_number}' already exists in ledger (Record ID: {exact_match['id']})."

            # 2. Heuristic duplicate: Same vendor and exact amount
            cursor.execute(
                """
                SELECT id, invoice_number, invoice_date 
                FROM invoices 
                WHERE vendor_name ILIKE %s AND amount = %s AND status = 'APPROVED';
                """,
                (f"%{vendor_name}%", amount)
            )
            heuristic_match = cursor.fetchone()
            if heuristic_match:
                return True, f"Warning: Potential duplicate charge. Vendor '{vendor_name}' already received an identical payment of {amount} on {heuristic_match['invoice_date']}."

            return False, ""
        finally:
            cursor.close()
            conn.close()

    def evaluate_policy_limit(self, category: str, amount: float) -> Tuple[bool, bool, str]:
        """
        Evaluate extracted amount against company expense policies.
        Returns: (is_breached, require_manager_approval, message)
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT max_single_limit, require_manager_approval FROM expense_policies WHERE category = %s;",
                (category,)
            )
            policy = cursor.fetchone()

            if not policy:
                return False, False, f"Notice: No explicit spending limit defined for category '{category}'."

            max_limit = float(policy["max_single_limit"])
            requires_approval = policy["require_manager_approval"]

            if amount > max_limit:
                msg = f"Policy Breach: Amount ({amount}) exceeds allowable limit of {max_limit} for category '{category}'."
                return True, requires_approval, msg

            return False, False, f"Compliant: Amount ({amount}) is within the allowable limit of {max_limit}."
        finally:
            cursor.close()
            conn.close()

    def audit_invoice(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution pipeline for the Auditor Agent:
        Executes duplicate detection, policy evaluations, and risk score calculation.
        """
        invoice_number = extracted_data.get("invoice_number")
        vendor_name = extracted_data.get("vendor_name")
        category = extracted_data.get("category")
        amount = float(extracted_data.get("amount", 0.0))

        flags = []
        risk_score = 0
        recommended_status = "APPROVED"

        # Check 1: Duplicate validation
        is_duplicate, duplicate_msg = self.check_duplicate_invoice(invoice_number, vendor_name, amount)
        if is_duplicate:
            flags.append(duplicate_msg)
            risk_score += 90
            recommended_status = "QUARANTINED"

        # Check 2: Policy limit compliance
        is_breached, req_approval, policy_msg = self.evaluate_policy_limit(category, amount)
        if is_breached:
            flags.append(policy_msg)
            risk_score += 40
            if recommended_status != "QUARANTINED":
                recommended_status = "PENDING_APPROVAL" if req_approval else "FLAGGED"

        # Construct final audit report
        audit_result = {
            "invoice_number": invoice_number,
            "vendor_name": vendor_name,
            "category": category,
            "amount": amount,
            "risk_score": min(risk_score, 100),
            "recommended_status": recommended_status,
            "audit_flags": flags if flags else ["All compliance and duplication checks passed successfully."]
        }

        return audit_result


if __name__ == "__main__":
    auditor = AuditorAgent()

    # Test Case 1: Checking known duplicate (INV-9901 from baseline data)
    print("--- Test 1: Duplicate Invoice Check ---")
    duplicate_payload = {
        "invoice_number": "INV-9901",
        "vendor_name": "Amazon Web Services",
        "category": "Cloud & Infra",
        "amount": 45000.0,
        "invoice_date": "2026-10-15"
    }
    result_dup = auditor.audit_invoice(duplicate_payload)
    print(f"Status: {result_dup['recommended_status']}, Risk Score: {result_dup['risk_score']}")
    print(f"Flags: {result_dup['audit_flags']}\n")

    # Test Case 2: Clean new invoice within policy
    print("--- Test 2: Clean Invoice Check ---")
    clean_payload = {
        "invoice_number": "INV-2026-001",
        "vendor_name": "DigitalOcean LLC",
        "category": "Cloud & Infra",
        "amount": 12000.0,
        "invoice_date": "2026-11-01"
    }
    result_clean = auditor.audit_invoice(clean_payload)
    print(f"Status: {result_clean['recommended_status']}, Risk Score: {result_clean['risk_score']}")
    print(f"Flags: {result_clean['audit_flags']}")