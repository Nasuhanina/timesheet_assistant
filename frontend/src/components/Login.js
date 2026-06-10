import React from "react";
import { loginUrl } from "../services/auth";

export default function Login() {
  const handleLogin = () => {
    window.location.href = loginUrl();
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Timesheet Assistant</h1>
        <p>Sign in with your Microsoft account to manage your timesheets via form or chat.</p>
        <button className="btn btn-primary btn-large" onClick={handleLogin}>
          Sign in with Microsoft
        </button>
      </div>
    </div>
  );
}
