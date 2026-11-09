import React, { useState, useRef } from "react";
import { UploadCloud, FileText, AlertCircle } from "lucide-react";
import "./UploadZone.css";

export default function UploadZone({ onFileUpload, isProcessing }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState("");
  const fileInputRef = useRef(null);

  const validateAndPassFile = (file) => {
    setValidationError("");

    if (!file) return;

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setValidationError("Unsupported format. Please upload a valid PDF invoice.");
      return;
    }

    // Limit to 10MB
    const maxSizeBytes = 10 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      setValidationError("Document exceeds 10MB limit. Select a smaller file.");
      return;
    }

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
          isProcessing ? "disabled" : ""
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
            <UploadCloud className="upload-icon" size={28} />
          </div>

          <div className="text-group">
            <p className="primary-text">
              <span className="action-link">Click to upload</span> or drag and drop invoice PDF
            </p>
            <p className="secondary-text">Standard AcroForm, digital bills, and system invoices up to 10MB</p>
          </div>
        </div>
      </div>

      {validationError && (
        <div className="validation-banner">
          <AlertCircle size={16} className="error-icon" />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  );
}