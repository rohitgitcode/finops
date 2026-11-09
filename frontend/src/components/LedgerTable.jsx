import React, { useState, useMemo } from "react";
import { 
  ShieldCheck, 
  AlertOctagon, 
  Clock, 
  Search, 
  X, 
  SlidersHorizontal,
  ChevronRight,
  FileText,
  Ban
} from "lucide-react";
import "./LedgerTable.css";

export default function LedgerTable({ invoices, isLoading, onSelectInvoice }) {
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const counts = useMemo(() => {
    return {
      ALL: invoices.length,
      APPROVED: invoices.filter((i) => i.status === "APPROVED").length,
      PENDING_APPROVAL: invoices.filter((i) => i.status === "PENDING_APPROVAL").length,
      QUARANTINED: invoices.filter((i) => i.status === "QUARANTINED").length,
      REJECTED: invoices.filter((i) => i.status === "REJECTED").length,
    };
  }, [invoices]);

  const filteredInvoices = useMemo(() => {
    return invoices.filter((item) => {
      const matchesStatus = filterStatus === "ALL" || item.status === filterStatus;
      if (!matchesStatus) return false;

      if (!searchQuery.trim()) return true;

      const q = searchQuery.toLowerCase();
      const invNum = (item.invoice_number || "").toLowerCase();
      const vendor = (item.vendor_name || "").toLowerCase();
      const category = (item.category || "").toLowerCase();
      const amount = String(item.amount || "");

      return (
        invNum.includes(q) ||
        vendor.includes(q) ||
        category.includes(q) ||
        amount.includes(q)
      );
    });
  }, [invoices, filterStatus, searchQuery]);

  const getStatusBadge = (status) => {
    switch (status) {
      case "APPROVED":
        return (
          <span className="badge badge-approved">
            <ShieldCheck size={12} />
            <span>Approved</span>
          </span>
        );
      case "QUARANTINED":
        return (
          <span className="badge badge-quarantined">
            <AlertOctagon size={12} />
            <span>Quarantined</span>
          </span>
        );
      case "REJECTED":
        return (
          <span className="badge badge-quarantined">
            <Ban size={12} />
            <span>Rejected</span>
          </span>
        );
      case "PENDING_APPROVAL":
        return (
          <span className="badge badge-pending">
            <Clock size={12} />
            <span>Needs Review</span>
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
          <div className="title-group">
            <h3 className="ledger-title">Financial Operations Ledger</h3>
            <span className="ledger-count-pill">{filteredInvoices.length} of {invoices.length}</span>
          </div>

          <div className="search-box">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              placeholder="Search vendor, invoice #, category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            {searchQuery && (
              <button 
                className="search-clear-btn" 
                onClick={() => setSearchQuery("")}
                title="Clear search"
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        <div className="toolbar-filters">
          {[
            { id: "ALL", label: "All" },
            { id: "APPROVED", label: "Approved" },
            { id: "PENDING_APPROVAL", label: "Needs Review" },
            { id: "QUARANTINED", label: "Quarantined" },
            { id: "REJECTED", label: "Rejected" }
          ].map((st) => (
            <button
              key={st.id}
              className={`filter-tab ${filterStatus === st.id ? "active" : ""}`}
              onClick={() => setFilterStatus(st.id)}
            >
              <span>{st.label}</span>
              <span className="filter-count">{counts[st.id] ?? 0}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="table-wrapper">
        <table className="ledger-table">
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Vendor</th>
              <th>Category</th>
              <th>Issue Date</th>
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
                  <div className="loading-state">
                    <span className="loading-spinner animate-spin" />
                    <span>Loading ledger records from PostgreSQL...</span>
                  </div>
                </td>
              </tr>
            ) : filteredInvoices.length === 0 ? (
              <tr>
                <td colSpan="8" className="empty-cell">
                  <div className="empty-state">
                    <FileText size={24} className="empty-icon" />
                    <p className="empty-text">No invoices match the selected filter or search query.</p>
                    {searchQuery && (
                      <button className="clear-filter-btn" onClick={() => setSearchQuery("")}>
                        Clear search filter
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              filteredInvoices.map((inv) => (
                <tr 
                  key={inv.id} 
                  className="ledger-row"
                  onClick={() => onSelectInvoice && onSelectInvoice(inv)}
                >
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
                  <td className="cell-center" onClick={(e) => e.stopPropagation()}>
                    <button
                      className="inspect-btn"
                      onClick={() => onSelectInvoice && onSelectInvoice(inv)}
                      title="Inspect full audit record"
                    >
                      <span>View</span>
                      <ChevronRight size={13} />
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
