import React from "react";
import { CheckCircle2, Clock, AlertTriangle, ShieldCheck, Database, FileSearch, ArrowRight, Activity } from "lucide-react";
import "./PipelineTrace.css";

export default function PipelineTrace({ currentStep, executionResult, isProcessing }) {
  const steps = [
    {
      id: "extraction",
      stepNumber: 1,
      title: "Perception & Extraction",
      agent: "Extractor Agent",
      subtext: "PyMuPDF + Groq Schema",
      icon: FileSearch,
      details: executionResult?.extracted_data
        ? `Extracted Invoice #${executionResult.extracted_data.invoice_number} from ${executionResult.extracted_data.vendor_name} for $${executionResult.extracted_data.amount}`
        : "Extracts AcroForm text fields, reading layout, and financial fields strictly into JSON."
    },
    {
      id: "audit",
      stepNumber: 2,
      title: "Ledger Verification & Compliance",
      agent: "Auditor Agent",
      subtext: "PostgreSQL Guardrails",
      icon: ShieldCheck,
      details: executionResult?.audit_report
        ? `Audit completed. Risk score: ${executionResult.audit_report.risk_score}/100. Status: ${executionResult.audit_report.recommended_status}`
        : "Evaluates duplicate invoices, policy limits, and assigns risk scores in PostgreSQL."
    },
    {
      id: "resolution",
      stepNumber: 3,
      title: "Settlement & Immutable Logging",
      agent: "Resolution Agent",
      subtext: "State Machine",
      icon: Database,
      details: executionResult?.resolution
        ? `Committed record #${executionResult.resolution.invoice_id} with audit action: ${executionResult.resolution.action_logged}`
        : "Persists verified record into master ledger and writes tamper-proof audit trails."
    }
  ];

  const getStepStatus = (index) => {
    if (executionResult) return "completed";
    if (!isProcessing) return "idle";
    if (index === currentStep) return "active";
    if (index < currentStep) return "completed";
    return "pending";
  };

  return (
    <div className="trace-card">
      <div className="trace-header">
        <div className="trace-header-left">
          <Activity size={16} className="trace-header-icon" />
          <div>
            <h3 className="trace-title">Multi-Agent Workflow</h3>
            <span className="trace-subtitle">Autonomous AP Pipeline</span>
          </div>
        </div>
        <span
          className={`status-pill ${
            executionResult
              ? "status-finished"
              : isProcessing
              ? "status-running"
              : "status-standby"
          }`}
        >
          {executionResult
            ? "Settlement Finished"
            : isProcessing
            ? "Agents Processing"
            : "Ready for Ingestion"}
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
                    <CheckCircle2 size={16} className="icon-success" />
                  ) : status === "active" ? (
                    <Clock size={16} className="icon-active animate-spin" />
                  ) : (
                    <IconComponent size={15} className="icon-idle" />
                  )}
                </div>
                {index < steps.length - 1 && <div className="step-connector-line" />}
              </div>

              <div className="step-details-col">
                <div className="step-meta">
                  <span className="step-agent">{step.agent}</span>
                  <span className="step-subtext">{step.subtext}</span>
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
