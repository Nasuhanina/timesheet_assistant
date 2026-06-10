import React from "react";
import { loginUrl } from "../services/auth";

export default function SessionExpiredModal() {
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const handler = () => setVisible(true);
    window.addEventListener("session-expired", handler);
    return () => window.removeEventListener("session-expired", handler);
  }, []);

  if (!visible) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <h2>Session Expired</h2>
        <p>Please re-login to continue.</p>
        <button
          className="btn btn-primary"
          onClick={() => {
            setVisible(false);
            window.location.href = loginUrl();
          }}
        >
          Go to Login
        </button>
      </div>
    </div>
  );
}
