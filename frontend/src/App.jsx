import React, { useState, useEffect } from "react";
import { 
  Building2, 
  ShieldAlert, 
  FileCheck2, 
  Layers, 
  RefreshCw, 
  X, 
  AlertCircle,
  CheckCircle,
  Database,
  ExternalLink,
  UserCheck,
  Check,
  Ban
} from "lucide-react";

import UploadZone from "./components/UploadZone";
import PipelineTrace from "./components/PipelineTrace";
import LedgerTable from "./components/LedgerTable";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export default function App() {
  const [invoices, setInvoices] = useState([]);
  const [isLoadingLedger, setIsLoadingLedger] = useState(false);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  const [pipelineCurrentStep, setPipelineCurrentStep] = useState(0);
  const [pipelineResult, setPipelineResult] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [globalError, setGlobalError] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  const fetchInvoices = async () => {
    setIsLoadingLedger(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/invoices`);
      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }
      const data = await response.json();
      setInvoices(data.invoices || []);
    } catch (err) {
      console.error("Failed to fetch invoices:", err);
      setGlobalError("Unable to connect to backend ledger. Ensure FastAPI server is running on port 8000.");
    } finally {
      setIsLoadingLedger(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const handleFileUpload = async (file) => {
    setIsProcessingFile(true);
    setPipelineResult(null);
    setPipelineCurrentStep(0);
    setGlobalError("");

    const formData = new FormData();
    formData.append("file", file);

    const stepInterval = setInterval(() => {
      setPipelineCurrentStep((prev) => (prev < 2 ? prev + 1 : prev));
    }, 1200);

    try {
      const response = await fetch(`${API_BASE_URL}/api/invoices/upload`, {
        method: "POST",
        body: formData,
      });

      clearInterval(stepInterval);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Agent pipeline encountered a processing fault.");
      }

      const result = await response.json();
      setPipelineCurrentStep(3);
      setPipelineResult(result);
      await fetchInvoices();
    } catch (err) {
      clearInterval(stepInterval);
      setPipelineResult(null);
      setGlobalError(err.message || "Failed to process the invoice.");
    } finally {
      setIsProcessingFile(false);
    }
  };

  const handleReviewAction = async (action) => {
    if (!selectedInvoice) return;
    setIsSubmittingReview(true);
    setGlobalError("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/invoices/${selectedInvoice.id}/review`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: action,
          notes: reviewNotes,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to record manual review decision.");
      }

      setReviewNotes("");
      setSelectedInvoice(null);
      await fetchInvoices();
    } catch (err) {
      console.error("Error submitting manual review:", err);
      setGlobalError(err.message || "Manual review submission failed.");
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const closeDrawer = () => {
    setReviewNotes("");
    setSelectedInvoice(null);
  };

  const openDrawer = (invoice) => {
    setReviewNotes("");
    setSelectedInvoice(invoice);
  };

  const totalSpend = invoices
    .filter((inv) => inv.status === "APPROVED")
    .reduce((acc, curr) => acc + parseFloat(curr.amount || 0), 0);

  const quarantinedCount = invoices.filter((inv) => inv.status === "QUARANTINED").length;
  const pendingCount = invoices.filter((inv) => inv.status === "PENDING_APPROVAL").length;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-group">
            <div className="brand-icon-box">
              <Building2 size={18} className="brand-icon" />
            </div>
            <div>
              <div className="brand-title-row">
                <h1 className="brand-title">LedgerMind FinOps</h1>
                <span className="env-badge">Production Engine</span>
              </div>
              <span className="brand-subtitle">Autonomous AP Ingestion & Audit Pipeline</span>
            </div>
          </div>

          <div className="header-actions">
            <div className="db-status-pill">
              <span className="status-dot-active" />
              <span>PostgreSQL Connected</span>
            </div>
            <button 
              className="sync-btn" 
              onClick={fetchInvoices} 
              disabled={isLoadingLedger}
              title="Refresh ledger state"
            >
              <RefreshCw size={13} className={isLoadingLedger ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </header>

      {globalError && (
        <div className="global-error-banner">
          <AlertCircle size={15} className="error-icon" />
          <span className="error-text">{globalError}</span>
          <button className="error-close-btn" onClick={() => setGlobalError("")} title="Dismiss">
            <X size={14} />
          </button>
        </div>
      )}

      <main className="app-main">
        {/* KPI Summary Cards */}
        <section className="metrics-grid">
          <div className="metric-card">
            <div className="metric-header">
              <span className="metric-label">Processed Ledger Entries</span>
              <div className="metric-icon-wrap">
                <Layers size={15} />
              </div>
            </div>
            <div className="metric-value">{invoices.length}</div>
            <span className="metric-subtext">Committed to PostgreSQL master ledger</span>
          </div>

          <div className="metric-card">
            <div className="metric-header">
              <span className="metric-label">Audited Approved Spend</span>
              <div className="metric-icon-wrap">
                <FileCheck2 size={15} />
              </div>
            </div>
            <div className="metric-value">
              {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(totalSpend)}
            </div>
            <span className="metric-subtext">Verified within authorized spending limits</span>
          </div>

          <div className="metric-card">
            <div className="metric-header">
              <span className="metric-label">Quarantine & Escalations</span>
              <div className="metric-icon-wrap metric-icon-alert-wrap">
                <ShieldAlert size={15} className="metric-icon-alert" />
              </div>
            </div>
            <div className="metric-value metric-value-alert">{quarantinedCount + pendingCount}</div>
            <span className="metric-subtext">
              {quarantinedCount} duplicate/fraud risks • {pendingCount} policy reviews
            </span>
          </div>
        </section>

        {/* Upload & Agent Pipeline Execution */}
        <section className="pipeline-grid">
          <div className="pipeline-upload-col">
            <UploadZone onFileUpload={handleFileUpload} isProcessing={isProcessingFile} />
          </div>
          <div className="pipeline-trace-col">
            <PipelineTrace 
              currentStep={pipelineCurrentStep} 
              executionResult={pipelineResult} 
              isProcessing={isProcessingFile} 
            />
          </div>
        </section>

        {/* Master Ledger Section */}
        <section className="ledger-section">
          <LedgerTable 
            invoices={invoices} 
            isLoading={isLoadingLedger} 
            onSelectInvoice={(inv) => openDrawer(inv)} 
          />
        </section>
      </main>

      {/* Invoice Detail Inspection Drawer */}
      {selectedInvoice && (
        <div className="drawer-overlay" onClick={closeDrawer}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <span className="drawer-pretitle">Audit Record Details</span>
                <h3 className="drawer-title">
                  {selectedInvoice.invoice_number || `INV-#${selectedInvoice.id}`}
                </h3>
              </div>
              <button 
                className="drawer-close-btn" 
                onClick={closeDrawer}
                title="Close drawer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="drawer-content">
              {/* Highlight summary card */}
              <div className="drawer-summary-card">
                <div className="summary-row">
                  <span className="summary-label">Amount Payable</span>
                  <span className="summary-amount">
                    {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
                      selectedInvoice.amount
                    )}
                  </span>
                </div>
                <div className="summary-row">
                  <span className="summary-label">Status</span>
                  <span className={`summary-status-pill status-${selectedInvoice.status.toLowerCase()}`}>
                    {selectedInvoice.status.replace("_", " ")}
                  </span>
                </div>
              </div>

              <div className="drawer-section">
                <h4 className="drawer-section-heading">Vendor & Invoicing</h4>
                
                <div className="drawer-field-group">
                  <span className="field-label">Vendor Name</span>
                  <span className="field-value">{selectedInvoice.vendor_name}</span>
                </div>

                <div className="drawer-field-group">
                  <span className="field-label">Expense Category</span>
                  <span className="field-value">{selectedInvoice.category}</span>
                </div>

                <div className="drawer-field-group">
                  <span className="field-label">Invoice Date</span>
                  <span className="field-value">{selectedInvoice.invoice_date || "-"}</span>
                </div>
              </div>

              <div className="drawer-section">
                <h4 className="drawer-section-heading">Automated Risk & Policy Audit</h4>

                <div className="drawer-field-group">
                  <span className="field-label">Risk Assessment</span>
                  <div className="drawer-risk-bar-wrap">
                    <div className="drawer-risk-header">
                      <span className="risk-score-text">Risk Score: {selectedInvoice.risk_score} / 100</span>
                      <span className="risk-level-tag">
                        {selectedInvoice.risk_score > 70 ? "High Risk" : selectedInvoice.risk_score > 30 ? "Medium Risk" : "Low Risk"}
                      </span>
                    </div>
                    <div className="risk-track">
                      <div 
                        className={`risk-fill ${
                          selectedInvoice.risk_score > 70
                            ? "fill-high"
                            : selectedInvoice.risk_score > 30
                            ? "fill-medium"
                            : "fill-low"
                        }`}
                        style={{ width: `${Math.min(selectedInvoice.risk_score, 100)}%` }}
                      />
                    </div>
                  </div>
                </div>

                <div className="drawer-field-group">
                  <span className="field-label">Audit Engine Findings</span>
                  <div className="audit-flags-panel">
                    {selectedInvoice.flag_reason || "All compliance, deduplication, and policy limit checks passed."}
                  </div>
                </div>
              </div>

              {selectedInvoice.status !== "APPROVED" && selectedInvoice.status !== "REJECTED" && (
                <div className="drawer-section hitl-governance-section">
                  <div className="hitl-header">
                    <UserCheck size={15} className="hitl-icon" />
                    <h4 className="drawer-section-heading">Human-In-The-Loop Governance</h4>
                  </div>
                  <p className="hitl-description">
                    Manual manager review required. Provide an audit justification note to override or reject this invoice record.
                  </p>

                  <div className="drawer-field-group">
                    <label className="field-label" htmlFor="review-justification">
                      Audit Justification / Override Notes
                    </label>
                    <textarea
                      id="review-justification"
                      className="review-textarea"
                      placeholder="Enter justification or reason for status override..."
                      rows={3}
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      disabled={isSubmittingReview}
                    />
                  </div>

                  <div className="hitl-actions-row">
                    <button
                      type="button"
                      className="btn-review-approve"
                      onClick={() => handleReviewAction("APPROVE")}
                      disabled={isSubmittingReview}
                    >
                      <Check size={14} />
                      <span>{isSubmittingReview ? "Submitting..." : "Force Approve (Override)"}</span>
                    </button>

                    <button
                      type="button"
                      className="btn-review-reject"
                      onClick={() => handleReviewAction("REJECT")}
                      disabled={isSubmittingReview}
                    >
                      <Ban size={14} />
                      <span>{isSubmittingReview ? "Submitting..." : "Reject & Void"}</span>
                    </button>
                  </div>
                </div>
              )}

              <div className="drawer-section">
                <h4 className="drawer-section-heading">System Metadata</h4>
                <div className="drawer-field-group">
                  <span className="field-label">Record ID</span>
                  <span className="field-value-secondary">#{selectedInvoice.id}</span>
                </div>
                <div className="drawer-field-group">
                  <span className="field-label">Created At</span>
                  <span className="field-value-secondary">{selectedInvoice.created_at || "-"}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
