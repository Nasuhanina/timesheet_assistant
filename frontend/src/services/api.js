const BASE =
  process.env.REACT_APP_API_URL ||
  (window.location.hostname === 'localhost'
    ? 'http://localhost:5000'
    : window.location.origin);

function triggerSessionExpired() {
  window.dispatchEvent(new CustomEvent("session-expired"));
}

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const config = {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  };
  const resp = await fetch(url, config);
  if (resp.status === 401) {
    triggerSessionExpired();
    throw new Error("Session expired. Please re-login.");
  }
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.error || `Request failed (${resp.status})`);
  }
  return data;
}

export function getEntries() {
  return request("/api/timesheet/entries");
}

export function addEntry(entry) {
  return request("/api/timesheet/entries", {
    method: "POST",
    body: JSON.stringify(entry),
  });
}

export function updateEntry(id, entry) {
  return request(`/api/timesheet/entries/${id}`, {
    method: "PUT",
    body: JSON.stringify(entry),
  });
}

export function deleteEntry(id) {
  return request(`/api/timesheet/entries/${id}`, {
    method: "DELETE",
  });
}

export function getUser() {
  return request("/auth/me");
}

export function logout() {
  return request("/auth/logout");
}

// ── Document ──────────────────────────────────────────────────

export async function getDocumentInfo() {
  return request("/api/timesheet/document/info");
}

export async function downloadDocument() {
  const url = `${BASE}/api/timesheet/document/download`;
  const resp = await fetch(url, { credentials: "include" });
  if (resp.status === 401) {
    triggerSessionExpired();
    throw new Error("Session expired. Please re-login.");
  }
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.error || `Download failed (${resp.status})`);
  }
  return resp.blob();
}

export async function generateDocument() {
  return request("/api/timesheet/document/generate", { method: "POST" });
}

export async function previewDocument() {
  return request("/api/timesheet/document/preview");
}

// ── GPTBots Chat ──────────────────────────────────────────────

export function sendGptbotsMessage(message, conversationId = null, currentDraft = null) {
  const payload = { message, conversation_id: conversationId, include_context: true };
  if (currentDraft) {
    payload.current_draft = currentDraft;
  }
  return request("/api/timesheet/chat-gptbots", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function confirmGptbotsEntry(entry, message) {
  return request("/api/timesheet/chat-gptbots", {
    method: "POST",
    body: JSON.stringify({ message, confirm_entry: entry }),
  });
}

// ── File Picker ────────────────────────────────────────────────

export function listFolderFiles() {
  return request("/api/timesheet/documents/list");
}

export function saveEntriesToFile(filename) {
  return request("/api/timesheet/documents/save-to-file", {
    method: "POST",
    body: JSON.stringify({ filename }),
  });
}

// ── Settings ───────────────────────────────────────────────────

export function getSettingsPath() {
  return request("/api/timesheet/settings/path");
}

export function setSettingsPath(path) {
  return request("/api/timesheet/settings/path", {
    method: "PUT",
    body: JSON.stringify({ path }),
  });
}

export async function uploadDocumentTemplate(file) {
  const url = `${BASE}/api/timesheet/document/upload`;
  const formData = new FormData();
  formData.append("file", file);
  const resp = await fetch(url, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (resp.status === 401) {
    triggerSessionExpired();
    throw new Error("Session expired. Please re-login.");
  }
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.error || "Upload failed");
  }
  return data;
}
