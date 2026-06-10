const BASE = process.env.REACT_APP_API_URL || "http://localhost:5000";

export function loginUrl() {
  return `${BASE}/auth/login`;
}
