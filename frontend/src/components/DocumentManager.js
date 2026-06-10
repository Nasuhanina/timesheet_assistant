import React, { useState, useEffect, useRef } from "react";
import {
  getDocumentInfo,
  downloadDocument,
  generateDocument,
  uploadDocumentTemplate,
  previewDocument,
} from "../services/api";

export default function DocumentManager() {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const fileRef = useRef(null);

  const loadInfo = async () => {
    try {
      const data = await getDocumentInfo();
      setInfo(data);
    } catch {
      setInfo(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadInfo();
  }, []);

  const handleDownload = async () => {
    try {
      const blob = await downloadDocument();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = info?.document_name || "timesheet.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    setMessage("");
    try {
      await generateDocument();
      setMessage("Document regenerated successfully!");
      await loadInfo();
    } catch (err) {
      setError(err.message);
    }
    setGenerating(false);
  };

  const handlePreview = async () => {
    setPreviewLoading(true);
    setError("");
    try {
      const data = await previewDocument();
      setPreview(data);
    } catch (err) {
      setError(err.message);
    }
    setPreviewLoading(false);
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.name.endsWith(".xlsx") && !file.name.endsWith(".xlsm")) {
      setError("Please select an .xlsx or .xlsm file");
      return;
    }
    setUploading(true);
    setError("");
    setMessage("");
    try {
      await uploadDocumentTemplate(file);
      setMessage(`"${file.name}" uploaded — entries written into it.`);
      await loadInfo();
    } catch (err) {
      setError(err.message);
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  const formatDate = (iso) => {
    if (!iso) return "N/A";
    return new Date(iso).toLocaleString();
  };

  const formatSize = (bytes) => {
    if (!bytes) return "N/A";
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  if (loading) {
    return <div className="loading-card">Loading document info...</div>;
  }

  return (
    <div className="document-manager">
      <div className="document-info-panel">
        <h2>Timesheet Document</h2>
        <p className="doc-desc">
          Your timesheet entries are written directly into the uploaded Excel file.
          Upload a .xlsm/.xlsx template with your preferred headers &amp; macros.
          Entries are matched to columns by header name and written starting row 2.
        </p>

        <div className="doc-status">
          <div className="doc-status-row">
            <span className="doc-label">Status:</span>
            <span className={`doc-value ${info?.has_document ? "status-ok" : "status-missing"}`}>
              {info?.has_document ? "Available" : "Not yet generated"}
            </span>
          </div>
          <div className="doc-status-row">
            <span className="doc-label">Entries:</span>
            <span className="doc-value">{info?.entries_count ?? 0}</span>
          </div>
          {info?.has_document && (
            <>
              <div className="doc-status-row">
                <span className="doc-label">Size:</span>
                <span className="doc-value">{formatSize(info.document_size)}</span>
              </div>
              <div className="doc-status-row">
                <span className="doc-label">Last Modified:</span>
                <span className="doc-value">{formatDate(info.document_modified)}</span>
              </div>
            </>
          )}
          <div className="doc-status-row">
            <span className="doc-label">Template:</span>
            <span className={`doc-value ${info?.has_template ? "status-ok" : "status-missing"}`}>
              {info?.has_template ? "Custom template" : "Default format"}
            </span>
          </div>
        </div>

        {message && <div className="success">{message}</div>}
        {error && <div className="error">{error}</div>}

        <div className="doc-actions">
          <button className="btn btn-primary" onClick={handleDownload} disabled={!info?.has_document}>
            Download Excel
          </button>
          <button
            className="btn btn-outline"
            onClick={handlePreview}
            disabled={previewLoading || (info?.entries_count ?? 0) === 0}
          >
            {previewLoading ? "Loading..." : "Preview"}
          </button>
          <button
            className="btn btn-outline"
            onClick={handleGenerate}
            disabled={generating || (info?.entries_count ?? 0) === 0}
          >
            {generating ? "Generating..." : "Regenerate Now"}
          </button>
        </div>
      </div>

      <div className="document-upload-panel">
        <h2>Upload Excel &amp; Write Entries</h2>
        <p className="doc-desc">
          Upload your .xlsm / .xlsx file. Entries will be written directly into it,
          preserving all macros, formatting, and existing sheets. Download to get the filled file.
        </p>
        <div className="upload-area">
          <input
            type="file"
            accept=".xlsx,.xlsm"
            onChange={handleUpload}
            ref={fileRef}
            disabled={uploading}
            id="template-upload"
            className="file-input"
          />
          <label htmlFor="template-upload" className="file-label">
            {uploading ? "Uploading..." : "Choose .xlsx / .xlsm file"}
          </label>
        </div>
      </div>

      {preview && (
        <div className="modal-overlay" onClick={() => setPreview(null)}>
          <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
            <div className="preview-header">
              <h2>Document Preview</h2>
              <button className="btn btn-sm" onClick={() => setPreview(null)}>Close</button>
            </div>
            <div className="preview-table-wrap">
              <table className="preview-table">
                <thead>
                  <tr>
                    {preview.headers.map((h, i) => (
                      <th key={i}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.length === 0 ? (
                    <tr><td colSpan={preview.headers.length} className="empty-cell">No data rows</td></tr>
                  ) : (
                    preview.rows.map((row, ri) => (
                      <tr key={ri}>
                        {row.map((cell, ci) => (
                          <td key={ci}>{cell ?? ""}</td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
