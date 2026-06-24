import React, { useState, useEffect } from "react";
import { getSettingsPath, setSettingsPath } from "../services/api";

export default function Settings() {
  const [path, setPath] = useState("");
  const [originalPath, setOriginalPath] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSettingsPath()
      .then((data) => {
        setPath(data.path);
        setOriginalPath(data.path);
      })
      .catch((err) => setError(err.message));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const data = await setSettingsPath(path);
      setOriginalPath(data.path);
      setMessage("Timesheet path updated successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const hasChanged = path !== originalPath;

  return (
    <div className="settings-container">
      <div className="settings-card">
        <h2>Timesheet Folder Path</h2>
        <p className="settings-desc">
          Set the SharePoint or OneDrive folder path where your timesheet JSON
          and Excel documents are stored.
        </p>

        <div className="form-group">
          <label htmlFor="ts-path">Folder Path</label>
          <input
            id="ts-path"
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/Timesheets"
          />
          <span className="form-hint">
            Example: <code>/Shared Documents/TimeSheet</code> or <code>/Timesheets</code>
          </span>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {message && <div className="alert alert-success">{message}</div>}

        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving || !hasChanged}
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}
