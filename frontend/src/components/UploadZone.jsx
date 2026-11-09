import React, { useState, useRef } from "react";
import { UploadCloud, FileText, AlertCircle, Loader2, CheckCircle2 } from "lucide-react";
import "./UploadZone.css";

export default function UploadZone({ onFileUpload, isProcessing }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState("");
  const [lastUploadedName, setLastUploadedName] = useState("");
  const fileInputRef = useRef(null);

  const validateAndPassFile = (file) => {
    setValidationError("");

    if (!file) return;

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setValidationError("Unsupported format. Please upload an invoice in PDF format.");
      return;
    }

    // 10MB limit
    const maxSizeBytes = 10 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      setValidationError("File exceeds 10MB limit. Please select a smaller PDF.");
      return;
    }

    setLastUploadedName(file.name);
    onFileUpload(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!isProcessing) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);

    if (isProcessing) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndPassFile(e.dataTransfer.files[0]);
    }
  };

  const handleManualChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndPassFile(e.target.files[0]);
    }
  };

  return (
    <div className="upload-container">
      <div
        className={`upload-zone ${isDragOver ? "drag-active" : ""} ${
          isProcessing ? "processing" : ""
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isProcessing && fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleManualChange}
          accept=".pdf,application/pdf"
          style={{ display: "none" }}
        />

        <div className="upload-content">
          <div className="icon-wrapper">
            {isProcessing ? (
              <Loader2 className="upload-icon animate-spin" size={24} />
            ) : (
              <UploadCloud className="upload-icon" size={24} />
            )}
          </div>

          <div className="text-group">
            {isProcessing ? (
              <>
                <p className="primary-text">Processing {lastUploadedName || "invoice"}...</p>
                <p className="secondary-text">Running multi-agent perception, audit, and ledger settlement</p>
              </>
            ) : (
              <>
                <p className="primary-text">
                  <span className="browse-link">Upload invoice</span> or drag and drop here
                </p>
                <p className="secondary-text">
                  PDF format with vector text, AcroForms, or digital invoices up to 10MB
                </p>
              </>
            )}
          </div>

          {!isProcessing && (
            <div className="upload-badges">
              <span className="badge-chip">PDF Document</span>
              <span className="badge-chip">Max 10MB</span>
              <span className="badge-chip">Automated Audit</span>
            </div>
          )}
        </div>
      </div>

      {validationError && (
        <div className="validation-banner">
          <AlertCircle size={15} className="error-icon" />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  );
}
