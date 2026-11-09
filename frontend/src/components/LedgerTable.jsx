import React, { useState } from "react";
import { ShieldCheck, AlertOctagon, Clock, ExternalLink } from "lucide-react";
import "./LedgerTable.css";

export default function LedgerTable({ invoices, isLoading, onSelectInvoice }) {
  const [filterStatus, setFilterStatus] = useState("ALL");

  const filteredInvoices = invoices.filter((item) => {
    if (filterStatus === "ALL") return true;
    return item.status === filterStatus;
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case "APPROVED":
        return (
          <span className="badge badge-approved">
            <ShieldCheck size={13} />
            <span>Approved</span>
          </span>
        );
      case "QUARANTINED":
        return (
          <span className="badge badge-quarantined">
            <AlertOctagon size={13} />
            <span>Quarantined</span>
          </span>
        );
      case "PENDING_APPROVAL":
        return (
          <span className="badge badge-pending">
            <Clock size={13} />
            <span>Needs Approval</span>
          </span>
        );
      default:
        return <span className="badge badge-default">{status}</span>;
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="ledger-card">
      <div className="ledger-toolbar">
        <div className="toolbar-left">
          <h3 className="ledger-title">Financial Operations Ledger</h3>
          <span className="ledger-count">
            {filteredInvoices.length} {filteredInvoices.length === 1 ? "record" : "records"}
          </span>
        </div>

        <div className="toolbar-filters">
          {["ALL", "APPROVED", "PENDING_APPROVAL", "QUARANTINED"].map((st) => (
            <button
              key={st}
              className={`filter-btn ${filterStatus === st ? "active" : ""}`}
              onClick={() => setFilterStatus(st)}
            >
              {st === "ALL" ? "All Records" : st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="table-wrapper">
        <table className="ledger-table">
          <thead>
            <tr>
              <th>Invoice Ref</th>
              <th>Vendor</th>
              <th>Category</th>
              <th>Date</th>
              <th className="cell-right">Amount</th>
              <th>Risk Score</th>
              <th>Audit Status</th>
              <th className="cell-center">Action</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan="8" className="empty-cell">
                  Loading ledger entries from PostgreSQL...
                </td>
              </tr>
            ) : filteredInvoices.length === 0 ? (
              <tr>
                <td colSpan="8" className="empty-cell">
                  No invoices found matching criteria.
                </td>
              </tr>
            ) : (
              filteredInvoices.map((inv) => (
                <tr key={inv.id} className="ledger-row">
                  <td className="cell-mono">{inv.invoice_number || `INV-#${inv.id}`}</td>
                  <td className="cell-primary">{inv.vendor_name}</td>
                  <td>
                    <span className="category-tag">{inv.category}</span>
                  </td>
                  <td className="cell-muted">{formatDate(inv.invoice_date)}</td>
                  <td className="cell-right cell-amount">{formatCurrency(inv.amount)}</td>
                  <td>
                    <div className="risk-indicator">
                      <div
                        className={`risk-dot ${
                          inv.risk_score > 70
                            ? "risk-high"
                            : inv.risk_score > 30
                            ? "risk-medium"
                            : "risk-low"
                        }`}
                      />
                      <span>{inv.risk_score}/100</span>
                    </div>
                  </td>
                  <td>{getStatusBadge(inv.status)}</td>
                  <td className="cell-center">
                    <button
                      className="inspect-btn"
                      onClick={() => onSelectInvoice && onSelectInvoice(inv)}
                      title="Inspect full audit trail"
                    >
                      <ExternalLink size={14} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}