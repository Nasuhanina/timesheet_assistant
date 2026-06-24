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

  useEffect(() => {
    loadInfo();
  }, []);

  const loadInfo = async () => {
    try {
      const data = await getDocumentInfo();
      setInfo(data);
    } catch {
      setInfo(null);
    }
    setLoading(false);
  };

  const handleDownload = async () => {
    try {
      const blob = await downloadDocument();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = info?.document_name || "timesheet.xlsm";
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
      setMessage("Entries written into template successfully!");
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
    const isExcel = /\.(xlsm|xlsx)$/i.test(file.name);
    if (!isExcel) {
      setError("Please select an .xlsm or .xlsx file");
      return;
    }
    setUploading(true);
    setError("");
    setMessage("");
    try {
      await uploadDocumentTemplate(file);
      setMessage(`"${file.name}" uploaded — entries written into template.`);
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
      <div className="doc-layout">
        <div className="doc-main-panel">
          <h2>Timesheet Document</h2>
          <p className="doc-desc">
            Upload your own timesheet template (.xlsm or .xlsx). Your entries
            will be written directly into the template while preserving its
            original formatting, headers, and layout.
          </p>

          <div className="upload-area">
            <div className="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="upload-text">
              {info?.has_template
                ? "Upload a new template to replace the current one"
                : "Drop your Excel template here or click to browse"}
            </p>
            <p className="upload-hint">Supports .xlsm and .xlsx files</p>
            <input
              type="file"
              accept=".xlsm,.xlsx,application/vnd.ms-excel.sheet.macroEnabled.12,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={handleUpload}
              ref={fileRef}
              disabled={uploading}
              id="template-upload"
              className="file-input"
            />
            <label htmlFor="template-upload" className="file-label">
              {uploading ? "Uploading..." : "Choose Template File"}
            </label>
          </div>

          {message && <div className="success">{message}</div>}
          {error && <div className="error">{error}</div>}

          <div className="doc-status">
            <div className="doc-status-row">
              <span className="doc-label">Template:</span>
              <span className={`doc-value ${info?.has_template ? "status-ok" : "status-missing"}`}>
                {info?.has_template ? "Uploaded" : "Not uploaded"}
              </span>
            </div>
            <div className="doc-status-row">
              <span className="doc-label">Entries:</span>
              <span className="doc-value">{info?.entries_count ?? 0}</span>
            </div>
            {info?.has_document && (
              <>
                <div className="doc-status-row">
                  <span className="doc-label">Generated File:</span>
                  <span className="doc-value status-ok">{info.document_name}</span>
                </div>
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
          </div>

          <div className="doc-actions">
            <button
              className="btn btn-primary"
              onClick={handleGenerate}
              disabled={generating || !info?.has_template || (info?.entries_count ?? 0) === 0}
            >
              {generating ? "Writing..." : "Write Entries to Template"}
            </button>
            <button
              className="btn btn-outline"
              onClick={handleDownload}
              disabled={!info?.has_document}
            >
              Download Excel
            </button>
            <button
              className="btn btn-outline"
              onClick={handlePreview}
              disabled={previewLoading || (info?.entries_count ?? 0) === 0}
            >
              {previewLoading ? "Loading..." : "Preview"}
            </button>
          </div>
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
