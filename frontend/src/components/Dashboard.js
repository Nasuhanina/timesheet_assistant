import React, { useState, useEffect } from "react";
import { getUser, logout } from "../services/api";
import TimesheetForm from "./TimesheetForm";
import ChatBot from "./ChatBot";
import DocumentManager from "./DocumentManager";

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState("form");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    getUser()
      .then((data) => setUser(data.user))
      .catch(() => {
        window.location.href = "/";
      });
  }, []);

  const handleLogout = async () => {
    await logout();
    window.location.href = "/";
  };

  if (!user) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Timesheet Assistant</h1>
        <div className="user-info">
          <span>{user.displayName || user.email}</span>
          <button className="btn btn-outline" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <nav className="tabs">
        <button
          className={`tab ${activeTab === "form" ? "active" : ""}`}
          onClick={() => setActiveTab("form")}
        >
          Timesheet Form
        </button>
        <button
          className={`tab ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => setActiveTab("chat")}
        >
          Chat Assistant
        </button>
        <button
          className={`tab ${activeTab === "document" ? "active" : ""}`}
          onClick={() => setActiveTab("document")}
        >
          Document
        </button>
      </nav>

      <main className="dashboard-content">
        <div style={{ display: activeTab === "form" ? "" : "none" }}>
          <TimesheetForm activeTab={activeTab} refreshKey={refreshKey} onSaved={() => setRefreshKey((k) => k + 1)} />
        </div>
        <div style={{ display: activeTab === "chat" ? "" : "none" }}>
          <ChatBot onSaved={() => setRefreshKey((k) => k + 1)} />
        </div>
        <div style={{ display: activeTab === "document" ? "" : "none" }}>
          <DocumentManager key={`doc-${refreshKey}`} />
        </div>
      </main>
    </div>
  );
}
