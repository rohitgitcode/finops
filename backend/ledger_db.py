import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """Establish and return a connection to the PostgreSQL database."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in the environment or .env file.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    """Initialize database tables and seed baseline verification records."""
    print("[1/4] Connecting to Neon PostgreSQL...")
    conn = get_connection()
    cursor = conn.cursor()

    print("[2/4] Dropping existing tables if any...")
    cursor.execute("DROP TABLE IF EXISTS audit_logs;")
    cursor.execute("DROP TABLE IF EXISTS invoices;")
    cursor.execute("DROP TABLE IF EXISTS expense_policies;")

    print("[3/4] Creating enterprise schema...")
    
    # 1. Expense Policies Table
    cursor.execute("""
    CREATE TABLE expense_policies (
        id SERIAL PRIMARY KEY,
        category VARCHAR(100) NOT NULL UNIQUE,
        max_single_limit NUMERIC(12, 2) NOT NULL,
        require_manager_approval BOOLEAN DEFAULT FALSE
    );
    """)

    # 2. Invoices Master Table
    cursor.execute("""
    CREATE TABLE invoices (
        id SERIAL PRIMARY KEY,
        invoice_number VARCHAR(100) NOT NULL,
        vendor_name VARCHAR(255) NOT NULL,
        category VARCHAR(100) NOT NULL,
        amount NUMERIC(12, 2) NOT NULL,
        invoice_date DATE NOT NULL,
        status VARCHAR(50) DEFAULT 'PENDING_AUDIT',
        risk_score INT DEFAULT 0,
        flag_reason TEXT DEFAULT '',
        raw_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Immutable Audit Trail
    cursor.execute("""
    CREATE TABLE audit_logs (
        id SERIAL PRIMARY KEY,
        invoice_id INT REFERENCES invoices(id) ON DELETE CASCADE,
        agent_name VARCHAR(50) NOT NULL,
        action_taken VARCHAR(100) NOT NULL,
        reasoning TEXT,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    print("[4/4] Seeding default policies and historical baseline records...")

    # Company expense rules
    policies = [
        ("Meals", 2000.0, False),
        ("Travel", 15000.0, True),
        ("Software", 25000.0, True),
        ("Cloud & Infra", 50000.0, True),
        ("Office Supplies", 5000.0, False),
    ]
    cursor.executemany("""
    INSERT INTO expense_policies (category, max_single_limit, require_manager_approval)
    VALUES (%s, %s, %s);
    """, policies)

    # Historical invoice records used for duplicate and baseline auditing
    historical_invoices = [
        ("INV-9901", "Amazon Web Services", "Cloud & Infra", 45000.0, "2026-10-15", "APPROVED", 0, "Approved recurring cloud spend"),
        ("INV-9902", "GitHub Inc", "Software", 1800.0, "2026-10-18", "APPROVED", 0, "Team developer licenses"),
        ("INV-9903", "Uber India", "Travel", 750.0, "2026-10-20", "APPROVED", 0, "Approved client transit"),
        ("INV-9904", "Swiggy Corporate", "Meals", 1200.0, "2026-10-22", "APPROVED", 0, "Approved team lunch"),
    ]
    cursor.executemany("""
    INSERT INTO invoices (invoice_number, vendor_name, category, amount, invoice_date, status, risk_score, flag_reason)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """, historical_invoices)

    conn.commit()
    cursor.close()
    conn.close()
    print("[SUCCESS] Production database initialized successfully on Neon PostgreSQL.")

if __name__ == "__main__":
    init_db()