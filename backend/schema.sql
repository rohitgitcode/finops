-- =============================================================================
-- Financial Operations Ledger Database Schema
-- Target: PostgreSQL (NeonDB)
-- Description: Core tables, constraints, and performance indexes for invoices,
--              audit trails, and compliance policies.
-- =============================================================================

-- Master Invoices Table
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(100) NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) DEFAULT 'General Expense',
    amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    invoice_date DATE,
    risk_score INT DEFAULT 0 CHECK (risk_score >= 0 AND risk_score <= 100),
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'QUARANTINED', 'PENDING_APPROVAL', 'REJECTED')),
    flag_reason TEXT DEFAULT '',
    raw_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Immutable Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    invoice_id INT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL DEFAULT 'SYSTEM_AUDIT',
    notes TEXT,
    agent_name VARCHAR(50) DEFAULT 'SystemAgent',
    action_taken VARCHAR(100),
    reasoning TEXT,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Expense Policies Table (Used by Auditor Agent for compliance checks)
CREATE TABLE IF NOT EXISTS expense_policies (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL UNIQUE,
    max_single_limit NUMERIC(12, 2) NOT NULL,
    require_manager_approval BOOLEAN DEFAULT FALSE
);

-- Non-destructive backward compatibility column checks
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS flag_reason TEXT DEFAULT '';
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS raw_text TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS action VARCHAR(100) DEFAULT 'SYSTEM_AUDIT';
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS agent_name VARCHAR(50) DEFAULT 'SystemAgent';
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS action_taken VARCHAR(100);
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS reasoning TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_invoice_id ON audit_logs(invoice_id);

