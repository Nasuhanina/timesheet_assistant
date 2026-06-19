import React, { useState, useEffect } from "react";
import { getEntries, addEntry, updateEntry, deleteEntry, getUser } from "../services/api";
import CalendarView from "./CalendarView";

export default function TimesheetForm({ onSaved, refreshKey, activeTab }) {
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState("");
  const [formTab, setFormTab] = useState("document");
  const today = () => new Date().toISOString().split("T")[0];
  const [form, setForm] = useState({
    activity_type: "document",
    user_name: "",
    date: today(),
    project_id: "",
    doc_task_type: "",
    doc_id: "",
    doc_version: "",
    doc_type: "",
    work_time: "",
    reviewer_time: "",
    doc_status: "",
    activity_code: "",
    activity_time: "",
    work_location: "",
    leave_travel_type: "",
    time: 8.5,
  });
  const [editingId, setEditingId] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    getUser().then((data) => {
      if (data.user) {
        setForm((prev) => ({ ...prev, user_name: data.user.displayName || data.user.email }));
      }
    }).catch(() => {});
    loadEntries();
  }, [refreshKey, activeTab]);

  const loadEntries = async () => {
    try {
      const data = await getEntries();
      setEntries(data);
    } catch {
      setError("Failed to load entries");
    }
  };

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const switchTab = (tab) => {
    setFormTab(tab);
    setForm((prev) => ({ ...prev, activity_type: tab }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (formTab === "document") {
      if (!form.project_id || !form.doc_task_type || !form.work_time) {
        setError("Project ID, Task Type, and Work Time are required.");
        return;
      }
    } else if (formTab === "other") {
      if (!form.activity_code || !form.activity_time) {
        setError("Activity Code and Activity Time are required.");
        return;
      }
    } else if (formTab === "leave_travel") {
      if (!form.leave_travel_type) {
        setError("Travel/Work type is required.");
        return;
      }
    }

    setSubmitting(true);
    try {
      let result;
      if (editingId) {
        result = await updateEntry(editingId, form);
      } else {
        result = await addEntry(form);
      }
      setForm((prev) => ({
        activity_type: formTab,
        user_name: prev.user_name,
        date: today(),
        project_id: "",
        doc_task_type: "",
        doc_id: "",
        doc_version: "",
        doc_type: "",
        work_time: "",
        reviewer_time: "",
        doc_status: "",
        activity_code: "",
        activity_time: "",
        work_location: "",
        leave_travel_type: "",
      time: prev.time || 0,
      }));
      setEditingId(null);
      setEntries(result.entries);
      setTimeout(() => loadEntries(), 1000);
      if (onSaved) onSaved();
    } catch (err) {
      setError(err.message);
    }
    setSubmitting(false);
  };

  const handleEdit = (entry) => {
    const t = entry.activity_type === "other" ? "other" : entry.activity_type === "leave_travel" ? "leave_travel" : "document";
    setFormTab(t);
    setForm({
      activity_type: t,
      user_name: entry.user_name || "",
      date: entry.date || today(),
      project_id: entry.project_id || "",
      doc_task_type: entry.doc_task_type || "",
      doc_id: entry.doc_id || "",
      doc_version: entry.doc_version || "",
      doc_type: entry.doc_type || "",
      work_time: String(entry.work_time || ""),
      reviewer_time: String(entry.reviewer_time || ""),
      doc_status: entry.doc_status || "",
      activity_code: entry.activity_code || "",
      activity_time: String(entry.activity_time || ""),
      work_location: entry.work_location || "",
      leave_travel_type: entry.leave_travel_type || "",
      time: 8.5,
    });
    setEditingId(entry.id);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this entry?")) return;
    setDeleting(true);
    try {
      const result = await deleteEntry(id);
      setEntries(result.entries);
      setTimeout(() => loadEntries(), 1000);
      if (onSaved) onSaved();
    } catch (err) {
      setError(err.message);
    }
    setDeleting(false);
  };

  const handleCancelEdit = () => {
    setForm((prev) => ({
      activity_type: formTab,
      user_name: prev.user_name,
      date: today(),
      project_id: "",
      doc_task_type: "",
      doc_id: "",
      doc_version: "",
      doc_type: "",
      work_time: "",
      reviewer_time: "",
      doc_status: "",
      activity_code: "",
      activity_time: "",
      work_location: "",
      leave_travel_type: "",
      time: 8.5,
    }));
    setEditingId(null);
  };

  const totalWorkTime = entries.reduce((sum, e) => sum + (
    e.activity_type === "other" ? e.activity_time :
    e.activity_type === "leave_travel" ? (e.time || 0) :
    e.work_time || 0
  ), 0);

  const displayEntries = selectedDate
    ? entries.filter(e => e.date === selectedDate)
    : entries;
  const calTotal = selectedDate
    ? displayEntries.reduce((sum, e) => sum + (
        e.activity_type === "other" ? e.activity_time :
        e.activity_type === "leave_travel" ? (e.time || 0) :
        (e.work_time || 0) + (e.reviewer_time || 0)
      ), 0)
    : 0;

  return (
    <div className="timesheet-form-container">
      <div className="form-panel">
        <h2>{editingId ? "Edit Entry" : "Add Entry"}</h2>
        <div className="form-tabs">
          <button
            className={`tab-btn ${formTab === "document" ? "active" : ""}`}
            onClick={() => !editingId && switchTab("document")}
          >
            Project Document Work
          </button>
          <button
            className={`tab-btn ${formTab === "other" ? "active" : ""}`}
            onClick={() => !editingId && switchTab("other")}
          >
            Other Activity
          </button>
          <button
            className={`tab-btn ${formTab === "leave_travel" ? "active" : ""}`}
            onClick={() => !editingId && switchTab("leave_travel")}
          >
            Leave/Travel
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              name="user_name"
              value={form.user_name}
              readOnly
              className="readonly-field"
            />
          </div>
          <div className="form-group">
            <label>Date</label>
            <input
              type="date"
              name="date"
              value={form.date}
              onChange={handleChange}
              required
            />
          </div>
          {formTab === "document" ? (
            <>
              <div className="form-group">
                <label>Project ID</label>
                <select name="project_id" value={form.project_id} onChange={handleChange} required>
                  <option value="">-- Select --</option>
                  <option value="1904-NSCR">1904-NSCR</option>
                  <option value="2010-IPS">2010-IPS</option>
                  <option value="2011-DRT">2011-DRT</option>
                  <option value="2103-PSDS">2103-PSDS</option>
                  <option value="2108-OISA">2108-OISA</option>
                  <option value="2111-SDC">2111-SDC</option>
                  <option value="2112-IVV">2112-IVV</option>
                  <option value="2114-ES">2114-ES</option>
                  <option value="2201-DDC">2201-DDC</option>
                  <option value="2202-SPC2">2202-SPC2</option>
                  <option value="2203-RTS">2203-RTS</option>
                  <option value="2204-SPC1">2204-SPC1</option>
                  <option value="2206-DEMV">2206-DEMV</option>
                  <option value="2208-DMRT">2208-DMRT</option>
                  <option value="2302-ISA">2302-ISA</option>
                  <option value="2307-3PV">2307-3PV</option>
                  <option value="2401-MLLRT">2401-MLLRT</option>
                  <option value="2404-PMC">2404-PMC</option>
                  <option value="2407-CM">2407-CM</option>
                  <option value="2408-HCM">2408-HCM</option>
                  <option value="2409-TWK">2409-TWK</option>
                  <option value="2410-DX">2410-DX</option>
                  <option value="2411-CMRL">2411-CMRL</option>
                  <option value="2414-SSKL">2414-SSKL</option>
                  <option value="2415-MLRT">2415-MLRT</option>
                  <option value="2501-DRR">2501-DRR</option>
                  <option value="2502-MLIT">2502-MLIT</option>
                  <option value="2503-MRL">2503-MRL</option>
                  <option value="2504-BR">2504-BR</option>
                  <option value="2505-TRG">2505-TRG</option>
                  <option value="2507-HSR">2507-HSR</option>
                  <option value="2508-TRNB">2508-TRNB</option>
                  <option value="2509-SIG">2509-SIG</option>
                  <option value="2602-JRE">2602-JRE</option>
                  <option value="2603-SSKL">2603-SSKL</option>
                  <option value="2604-UTMY">2604-UTMY</option>
                  <option value="2605-GCRR">2605-GCRR</option>
                  <option value="2606-TMRL">2606-TMRL</option>
                  <option value="2607-3IRP">2607-3IRP</option>
                  <option value="2608-PBJB">2608-PBJB</option>
                  <option value="2609-MMSP">2609-MMSP</option>
                </select>
              </div>
              <div className="form-group">
                <label>Document Task Type</label>
                <select name="doc_task_type" value={form.doc_task_type} onChange={handleChange} required>
                  <option value="">-- Select --</option>
                  <option value="P">P - Prepare</option>
                  <option value="C">C - Check</option>
                </select>
              </div>
              <div className="form-group">
                <label>Doc ID</label>
                <input
                  type="text"
                  name="doc_id"
                  value={form.doc_id}
                  onChange={handleChange}
                  placeholder="e.g. DOC-001"
                />
              </div>
              <div className="form-group">
                <label>Doc Version / DRS</label>
                <input
                  type="text"
                  name="doc_version"
                  value={form.doc_version}
                  onChange={handleChange}
                  placeholder="e.g. 1.0 / DRS-123"
                />
              </div>
              <div className="form-group">
                <label>Doc Type</label>
                <select name="doc_type" value={form.doc_type} onChange={handleChange}>
                  <option value="">-- Select --</option>
                  <option value="N">N - New Doc</option>
                  <option value="U">U - Update</option>
                </select>
              </div>
              <div className="form-group">
                <label>Work Time</label>
                <input
                  type="number"
                  name="work_time"
                  value={form.work_time}
                  onChange={handleChange}
                  step="0.5"
                  min="0"
                  max="24"
                  placeholder="e.g. 8"
                  required
                />
              </div>
              <div className="form-group">
                <label>Reviewer's / Mentor's Time</label>
                <input
                  type="number"
                  name="reviewer_time"
                  value={form.reviewer_time}
                  onChange={handleChange}
                  step="0.5"
                  min="0"
                  max="24"
                  placeholder="e.g. 1"
                />
              </div>
              <div className="form-group">
                <label>Doc. Status</label>
                <select name="doc_status" value={form.doc_status} onChange={handleChange}>
                  <option value="">-- Select --</option>
                  <option value="C80">C80</option>
                  <option value="C83">C83</option>
                  <option value="C82">C82</option>
                  <option value="C81">C81</option>
                  <option value="C40">C40</option>
                  <option value="C43">C43</option>
                  <option value="C42">C42</option>
                  <option value="C41">C41</option>
                  <option value="P80">P80</option>
                  <option value="P83">P83</option>
                  <option value="P82">P82</option>
                  <option value="P81">P81</option>
                  <option value="P40">P40</option>
                  <option value="P43">P43</option>
                  <option value="P42">P42</option>
                  <option value="P41">P41</option>
                </select>
              </div>
              <div className="form-group">
                <label>Work Location</label>
                <select name="work_location" value={form.work_location} onChange={handleChange}>
                  <option value="">-- Select --</option>
                  <option value="Office 5-5">Office 5-5</option>
                  <option value="Office 12-7">Office 12-7</option>
                  <option value="Office 5-13A">Office 5-13A</option>
                  <option value="Kuching Br.">Kuching Br.</option>
                  <option value="Jakarta Br.">Jakarta Br.</option>
                  <option value="Bangalore Br.">Bangalore Br.</option>
                  <option value="Site">Site</option>
                  <option value="WFH Primary">WFH Primary</option>
                  <option value="WFH Other">WFH Other</option>
                </select>
              </div>
            </>
          ) : formTab === "other" ? (
            <>
              <div className="form-group">
                <label>Activity Code</label>
                <select name="activity_code" value={form.activity_code} onChange={handleChange} required>
                  <option value="">-- Select --</option>
                  <option value="PC0-Invoicing">PC0-Invoicing</option>
                  <option value="PC1-P-Tracker Prep-Up">PC1-P-Tracker Prep-Up</option>
                  <option value="PC2-P-Tracker-Prog.">PC2-P-Tracker-Prog.</option>
                  <option value="PC3-Cash Flow">PC3-Cash Flow</option>
                  <option value="PC4-Contract">PC4-Contract</option>
                  <option value="PC10-Proj. Closing">PC10-Proj. Closing</option>
                  <option value="PC5-Subcon">PC5-Subcon</option>
                  <option value="PD1-Data Prep">PD1-Data Prep</option>
                  <option value="PD2-Data Analysis">PD2-Data Analysis</option>
                  <option value="PD3-Software Dev">PD3-Software Dev</option>
                  <option value="PF1-Folder Set up">PF1-Folder Set up</option>
                  <option value="PF2-Docs. Archive">PF2-Docs. Archive</option>
                  <option value="PL1-Time Plan">PL1-Time Plan</option>
                  <option value="PM1-Mtg. Client">PM1-Mtg. Client</option>
                  <option value="PM2-Mtg. Int. Team">PM2-Mtg. Int. Team</option>
                  <option value="PM3-Mtg. CC-Others">PM3-Mtg. CC-Others</option>
                  <option value="POA-Others">POA-Others</option>
                  <option value="PQ1-Doc. QC">PQ1-Doc. QC</option>
                  <option value="PS1-Site Visit">PS1-Site Visit</option>
                  <option value="PS2-Test Site">PS2-Test Site</option>
                  <option value="PS3-Test Factory">PS3-Test Factory</option>
                  <option value="PT1-D-Tracker Prep-Up">PT1-D-Tracker Prep-Up</option>
                  <option value="PT2-D-Tracker Prog.">PT2-D-Tracker Prog.</option>
                  <option value="PTR0-Trainer's Time">PTR0-Trainer's Time</option>
                </select>
              </div>
              <div className="form-group">
                <label>Project ID (If Proj. Activity)</label>
                <select name="project_id" value={form.project_id} onChange={handleChange}>
                  <option value="">-- Select --</option>
                  <option value="1904-NSCR">1904-NSCR</option>
                  <option value="2010-IPS">2010-IPS</option>
                  <option value="2011-DRT">2011-DRT</option>
                  <option value="2103-PSDS">2103-PSDS</option>
                  <option value="2108-OISA">2108-OISA</option>
                  <option value="2111-SDC">2111-SDC</option>
                  <option value="2112-IVV">2112-IVV</option>
                  <option value="2114-ES">2114-ES</option>
                  <option value="2201-DDC">2201-DDC</option>
                  <option value="2202-SPC2">2202-SPC2</option>
                  <option value="2203-RTS">2203-RTS</option>
                  <option value="2204-SPC1">2204-SPC1</option>
                  <option value="2206-DEMV">2206-DEMV</option>
                  <option value="2208-DMRT">2208-DMRT</option>
                  <option value="2302-ISA">2302-ISA</option>
                  <option value="2307-3PV">2307-3PV</option>
                  <option value="2401-MLLRT">2401-MLLRT</option>
                  <option value="2404-PMC">2404-PMC</option>
                  <option value="2407-CM">2407-CM</option>
                  <option value="2408-HCM">2408-HCM</option>
                  <option value="2409-TWK">2409-TWK</option>
                  <option value="2410-DX">2410-DX</option>
                  <option value="2411-CMRL">2411-CMRL</option>
                  <option value="2414-SSKL">2414-SSKL</option>
                  <option value="2415-MLRT">2415-MLRT</option>
                  <option value="2501-DRR">2501-DRR</option>
                  <option value="2502-MLIT">2502-MLIT</option>
                  <option value="2503-MRL">2503-MRL</option>
                  <option value="2504-BR">2504-BR</option>
                  <option value="2505-TRG">2505-TRG</option>
                  <option value="2507-HSR">2507-HSR</option>
                  <option value="2508-TRNB">2508-TRNB</option>
                  <option value="2509-SIG">2509-SIG</option>
                  <option value="2602-JRE">2602-JRE</option>
                  <option value="2603-SSKL">2603-SSKL</option>
                  <option value="2604-UTMY">2604-UTMY</option>
                  <option value="2605-GCRR">2605-GCRR</option>
                  <option value="2606-TMRL">2606-TMRL</option>
                  <option value="2607-3IRP">2607-3IRP</option>
                  <option value="2608-PBJB">2608-PBJB</option>
                  <option value="2609-MMSP">2609-MMSP</option>
                </select>
              </div>
              <div className="form-group">
                <label>Activity Time</label>
                <input
                  type="number"
                  name="activity_time"
                  value={form.activity_time}
                  onChange={handleChange}
                  step="0.5"
                  min="0"
                  max="24"
                  placeholder="e.g. 8"
                  required
                />
              </div>
              <div className="form-group">
                <label>Work Location</label>
                <select name="work_location" value={form.work_location} onChange={handleChange}>
                  <option value="">-- Select --</option>
                  <option value="Office 5-5">Office 5-5</option>
                  <option value="Office 12-7">Office 12-7</option>
                  <option value="Office 5-13A">Office 5-13A</option>
                  <option value="Kuching Br.">Kuching Br.</option>
                  <option value="Jakarta Br.">Jakarta Br.</option>
                  <option value="Bangalore Br.">Bangalore Br.</option>
                  <option value="Site">Site</option>
                  <option value="WFH Primary">WFH Primary</option>
                  <option value="WFH Other">WFH Other</option>
                </select>
              </div>
            </>
          ) : (
            <>
              <div className="form-group">
                <label>Travel/Work</label>
                <select name="leave_travel_type" value={form.leave_travel_type} onChange={handleChange} required>
                  <option value="">-- Select --</option>
                  <option value="AL-Half">AL-Half</option>
                  <option value="AL-Full">AL-Full</option>
                  <option value="MC-Sick">MC-Sick</option>
                  <option value="HL-Hospital">HL-Hospital</option>
                  <option value="PL-Paternity">PL-Paternity</option>
                  <option value="ML-Maternity">ML-Maternity</option>
                  <option value="CL-Comp">CL-Comp</option>
                  <option value="ATI-Air Travel Intl">ATI-Air Travel Intl</option>
                  <option value="ATD-Air Travel Dom">ATD-Air Travel Dom</option>
                </select>
              </div>
              <div className="form-group">
                <label>Time</label>
                <input
                  type="text"
                  value="8:30"
                  readOnly
                  className="readonly-field"
                />
              </div>
            </>
          )}
          {error && <div className="error">{error}</div>}
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? <span className="spinner" /> : null}
              {submitting ? "Saving..." : editingId ? "Update" : "Save Entry"}
            </button>
            {editingId && (
              <button type="button" className="btn btn-outline" onClick={handleCancelEdit}>
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="entries-panel">
        <h2>Timesheet Entries</h2>
        <div className="total-hours">Total Hours: {totalWorkTime}h</div>
        <CalendarView
          entries={entries}
          selectedDate={selectedDate}
          onSelectDate={(d) => setSelectedDate(selectedDate === d ? null : d)}
        />
        {selectedDate && (
          <div className="cal-filter-bar">
            Showing <strong>{selectedDate}</strong> — {calTotal}h
            <button className="btn btn-sm" onClick={() => setSelectedDate(null)}>Show All</button>
          </div>
        )}
        {displayEntries.length === 0 ? (
          <p className="empty">No entries yet.</p>
        ) : (
          <div className="entries-list">
            {displayEntries.map((entry) => (
              <div key={entry.id} className="entry-card">
                {entry.activity_type === "leave_travel" ? (
                  <>
                    <div className="entry-field"><strong>Name:</strong> {entry.user_name || "-"}</div>
                    <div className="entry-field"><strong>Date:</strong> {entry.date || "-"}</div>
                    <div className="entry-field"><strong>Type:</strong> {entry.leave_travel_type || "-"}</div>
                    <div className="entry-field"><strong>Time:</strong> {Math.floor(entry.time || 0)}:{String(Math.round(((entry.time || 0) - Math.floor(entry.time || 0)) * 60)).padStart(2, "0")}h</div>
                  </>
                ) : entry.activity_type === "other" ? (
                  <>
                    <div className="entry-field"><strong>Name:</strong> {entry.user_name || "-"}</div>
                    <div className="entry-field"><strong>Date:</strong> {entry.date || "-"}</div>
                    <div className="entry-field"><strong>Activity:</strong> {entry.activity_code}</div>
                    <div className="entry-field"><strong>Project:</strong> {entry.project_id || "-"}</div>
                    <div className="entry-field"><strong>Time:</strong> {entry.activity_time}h</div>
                    <div className="entry-field"><strong>Location:</strong> {entry.work_location || "-"}</div>
                  </>
                ) : (
                  <>
                    <div className="entry-field"><strong>Name:</strong> {entry.user_name || "-"}</div>
                    <div className="entry-field"><strong>Date:</strong> {entry.date || "-"}</div>
                    <div className="entry-field"><strong>Project:</strong> {entry.project_id}</div>
                    <div className="entry-field"><strong>Task:</strong> {entry.doc_task_type === "P" ? "Prepare" : entry.doc_task_type === "C" ? "Check" : entry.doc_task_type}</div>
                    <div className="entry-field"><strong>Doc ID:</strong> {entry.doc_id || "-"}</div>
                    <div className="entry-field"><strong>Version:</strong> {entry.doc_version || "-"}</div>
                    <div className="entry-field"><strong>Type:</strong> {entry.doc_type === "N" ? "New" : entry.doc_type === "U" ? "Update" : entry.doc_type || "-"}</div>
                    <div className="entry-field"><strong>Work:</strong> {entry.work_time}h</div>
                    <div className="entry-field"><strong>Reviewer:</strong> {entry.reviewer_time || 0}h</div>
                    <div className="entry-field"><strong>Status:</strong> {entry.doc_status || "-"}</div>
                    <div className="entry-field"><strong>Location:</strong> {entry.work_location || "-"}</div>
                  </>
                )}
                <div className="entry-actions">
                  <button className="btn btn-sm" onClick={() => handleEdit(entry)} disabled={submitting || deleting}>
                    {submitting ? <span className="spinner" /> : null}
                    Edit
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDelete(entry.id)} disabled={deleting}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {deleting && (
        <div className="modal-overlay">
          <div className="modal-box" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <div className="spinner-large" />
            <p>Deleting entry...</p>
          </div>
        </div>
      )}
    </div>
  );
}
