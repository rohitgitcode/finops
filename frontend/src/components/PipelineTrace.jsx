import React from "react";
import { CheckCircle2, Clock, AlertTriangle, ShieldCheck, Database, FileSearch } from "lucide-react";
import "./PipelineTrace.css";

export default function PipelineTrace({ currentStep, executionResult, isProcessing }) {
  if (!isProcessing && !executionResult) {
    return null;
  }

  const steps = [
    {
      id: "extraction",
      stepNumber: 1,
      title: "Perception & Extraction",
      agent: "Extractor Agent (PyMuPDF + Groq)",
      icon: FileSearch,
      details: executionResult?.extracted_data
        ? `Identified Invoice #${executionResult.extracted_data.invoice_number} by ${executionResult.extracted_data.vendor_name} for $${executionResult.extracted_data.amount}`
        : "Extracting AcroForm annotations, reading order, and key financial metadata..."
    },
    {
      id: "audit",
      stepNumber: 2,
      title: "Ledger Verification & Compliance",
      agent: "Auditor Agent (PostgreSQL Guardrails)",
      icon: ShieldCheck,
      details: executionResult?.audit_report
        ? `Audit completed. Risk score: ${executionResult.audit_report.risk_score}/100. Status recommendation: ${executionResult.audit_report.recommended_status}`
        : "Cross-referencing historical invoices, duplication checks, and spending thresholds..."
    },
    {
      id: "resolution",
      stepNumber: 3,
      title: "Ledger Settlement & Logging",
      agent: "Resolution Agent (State Machine)",
      icon: Database,
      details: executionResult?.resolution
        ? `Committed record #${executionResult.resolution.invoice_id} with immutable audit log: ${executionResult.resolution.action_logged}`
        : "Committing state transition and appending tamper-proof audit trail..."
    }
  ];

  const getStepStatus = (index) => {
    if (executionResult) return "completed";
    if (index === currentStep) return "active";
    if (index < currentStep) return "completed";
    return "pending";
  };

  return (
    <div className="trace-card">
      <div className="trace-header">
        <h3 className="trace-title">Agent Execution Pipeline</h3>
        <span className={`status-pill ${executionResult ? "status-finished" : "status-running"}`}>
          {executionResult ? "Execution Complete" : "Pipeline Active"}
        </span>
      </div>

      <div className="trace-steps">
        {steps.map((step, index) => {
          const status = getStepStatus(index);
          const IconComponent = step.icon;

          return (
            <div key={step.id} className={`trace-step-item step-${status}`}>
              <div className="step-indicator-col">
                <div className="step-icon-box">
                  {status === "completed" ? (
                    <CheckCircle2 size={18} className="icon-success" />
                  ) : status === "active" ? (
                    <Clock size={18} className="icon-active animate-spin" />
                  ) : (
                    <IconComponent size={18} className="icon-pending" />
                  )}
                </div>
                {index < steps.length - 1 && <div className="step-connector-line" />}
              </div>

              <div className="step-details-col">
                <div className="step-meta">
                  <span className="step-agent">{step.agent}</span>
                  <span className="step-badge">{`Step 0${step.stepNumber}`}</span>
                </div>
                <h4 className="step-name">{step.title}</h4>
                <p className="step-description">{step.details}</p>
              </div>
            </div>
          );
        })}
      </div>

      {executionResult?.audit_report?.audit_flags?.length > 0 && (
        <div className="trace-flags-box">
          <div className="flags-header">
            <AlertTriangle size={15} />
            <span>Audit Findings & Flags</span>
          </div>
          <ul className="flags-list">
            {executionResult.audit_report.audit_flags.map((flag, i) => (
              <li key={i}>{flag}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}