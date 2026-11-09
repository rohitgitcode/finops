import React, { useState, useEffect } from "react";
import { 
  Building2, 
  ShieldAlert, 
  FileCheck2, 
  Layers, 
  RefreshCw, 
  X, 
  AlertCircle 
} from "lucide-react";

import UploadZone from "./components/UploadZone";
import PipelineTrace from "./components/PipelineTrace";
import LedgerTable from "./components/LedgerTable";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function App() {
  const [invoices, setInvoices] = useState([]);
  const [isLoadingLedger, setIsLoadingLedger] = useState(false);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  const [pipelineCurrentStep, setPipelineCurrentStep] = useState(0);
  const [pipelineResult, setPipelineResult] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [globalError, setGlobalError] = useState("");

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
      setGlobalError("Unable to connect to the backend ledger. Ensure FastAPI server is running.");
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
              <h1 className="brand-title">LedgerMind FinOps</h1>
              <span className="brand-subtitle">Autonomous AP Ingestion & Audit Engine</span>
            </div>
          </div>

          <div className="header-actions">
            <button 
              className="sync-btn" 
              onClick={fetchInvoices} 
              disabled={isLoadingLedger}
              title="Refresh ledger state"
            >
              <RefreshCw size={14} className={isLoadingLedger ? "animate-spin" : ""} />
              <span>Refresh Ledger</span>
            </button>
          </div>
        </div>
      </header>

      {globalError && (
        <div className="global-error-banner">
          <AlertCircle size={16} />
          <span>{globalError}</span>
          <button className="error-close-btn" onClick={() => setGlobalError("")}>
            <X size={14} />
          </button>
        </div>
      )}

      <main className="app-main">
        <section className="metrics-grid">
          <div className="metric-card">
            <div className="metric-header">
              <span className="metric-label">Processed Ledger Entries</span>
              <Layers size={16} className="metric-icon" />
            </div>
            <div className="metric-value">{invoices.length}</div>
            <span className="metric-subtext">Committed to PostgreSQL</span>
          </div>

          <div className="metric-card">
            <div className="metric-header">
              <span className="metric-label">Audited Approved Spend</span>
              <FileCheck2 size={16} className="metric-icon" />
            </div>
            <div className="metric-value">
              {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(totalSpend)}
            </div>
            <span className="metric-subtext">Within authorized policy thresholds</span>
          </div>

          <div className="metric-card">
            <div className="metric-header">
              <span className="metric-label">Quarantine & Escalations</span>
              <ShieldAlert size={16} className="metric-icon metric-icon-alert" />
            </div>
            <div className="metric-value metric-value-alert">{quarantinedCount + pendingCount}</div>
            <span className="metric-subtext">
              {quarantinedCount} duplicate/fraud risks, {pendingCount} policy reviews
            </span>
          </div>
        </section>

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

        <section className="ledger-section">
          <LedgerTable 
            invoices={invoices} 
            isLoading={isLoadingLedger} 
            onSelectInvoice={(inv) => setSelectedInvoice(inv)} 
          />
        </section>
      </main>

      {selectedInvoice && (
        <div className="drawer-overlay" onClick={() => setSelectedInvoice(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <h3 className="drawer-title">Invoice Audit Inspection</h3>
                <span className="drawer-subtitle">
                  {selectedInvoice.invoice_number || `Record #${selectedInvoice.id}`}
                </span>
              </div>
              <button className="drawer-close-btn" onClick={() => setSelectedInvoice(null)}>
                <X size={16} />
              </button>
            </div>

            <div className="drawer-content">
              <div className="drawer-field-group">
                <span className="field-label">Vendor Name</span>
                <span className="field-value">{selectedInvoice.vendor_name}</span>
              </div>

              <div className="drawer-field-group">
                <span className="field-label">Expense Category</span>
                <span className="field-value">{selectedInvoice.category}</span>
              </div>

              <div className="drawer-field-group">
                <span className="field-label">Payable Amount</span>
                <span className="field-value">
                  {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
                    selectedInvoice.amount
                  )}
                </span>
              </div>

              <div className="drawer-field-group">
                <span className="field-label">Assessed Risk Score</span>
                <span className="field-value">{selectedInvoice.risk_score} / 100</span>
              </div>

              <div className="drawer-field-group">
                <span className="field-label">Audit Engine Verdict</span>
                <div className="audit-flags-panel">
                  {selectedInvoice.flag_reason || "All compliance and duplication checks passed successfully."}
                </div>
              </div>

              <div className="drawer-field-group">
                <span className="field-label">Recorded At</span>
                <span className="field-value-secondary">{selectedInvoice.created_at}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}