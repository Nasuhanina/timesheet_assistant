import json
from datetime import datetime
from flask import session
import requests
from config import Config
from token_store import get as get_tokens, pop as pop_tokens

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_access_token():
    tid = session.get("token_id")
    if not tid:
        raise PermissionError("Not authenticated — no token_id in session")
    tokens = get_tokens(tid)
    if not tokens:
        raise PermissionError("Tokens expired or missing from store")
    return tokens["access_token"], tokens.get("refresh_token")


def _headers():
    token, _ = _get_access_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _refresh_token():
    tid = session.get("token_id")
    tokens = get_tokens(tid)
    if not tokens or not tokens.get("refresh_token"):
        return False

    from token_store import store as store_tokens, pop as pop_tokens

    token_url = f"{Config.MICROSOFT_AUTHORITY}/oauth2/v2.0/token"
    data = {
        "client_id": Config.MICROSOFT_CLIENT_ID,
        "client_secret": Config.MICROSOFT_CLIENT_SECRET,
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token",
    }
    resp = requests.post(token_url, data=data)
    if not resp.ok:
        return False

    new_tokens = resp.json()
    pop_tokens(tid)
    new_tid = store_tokens(new_tokens)
    session["token_id"] = new_tid
    return True


def _handle_errors(resp):
    if resp.status_code == 401:
        return _refresh_token()
    return False


def _ensure_timesheets_folder():
    path = Config.ONEDRIVE_ROOT_PATH.strip("/")
    parts = path.split("/")
    folder_id = None

    for part in parts:
        parent_path = f"/drive/root:{path}" if folder_id is None else ""
        current_path = f"/drive/root:/{path}" if not folder_id else ""

        if not folder_id:
            resp = requests.get(
                f"{GRAPH_BASE}/me/drive/root:/{path}",
                headers=_headers(),
            )
            if resp.ok:
                folder_id = resp.json().get("id")
                continue

        create_resp = requests.post(
            f"{GRAPH_BASE}/me/drive/items/{folder_id or 'root'}/children",
            headers=_headers(),
            json={"name": part, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"},
        )
        if create_resp.status_code in (200, 201):
            folder_id = create_resp.json().get("id")
        else:
            existing = requests.get(
                f"{GRAPH_BASE}/me/drive/root:/{path}",
                headers=_headers(),
            )
            if existing.ok:
                folder_id = existing.json().get("id")

    return folder_id


def save_timesheet(timesheet_data):
    user = session.get("user", {})
    email = user.get("email", "unknown")
    timesheet_data["user_email"] = email
    timesheet_data["updated_at"] = datetime.utcnow().isoformat()

    folder_id = _ensure_timesheets_folder()
    if not folder_id:
        raise RuntimeError("Could not create/find OneDrive Timesheets folder")

    filename = f"timesheet_{email.replace('@', '_at_')}.json"
    content = json.dumps(timesheet_data, indent=2).encode()

    folder_children = requests.get(
        f"{GRAPH_BASE}/me/drive/items/{folder_id}/children",
        headers=_headers(),
    )
    existing_id = None
    if folder_children.ok:
        for child in folder_children.json().get("value", []):
            if child.get("name") == filename:
                existing_id = child["id"]
                break

    if existing_id:
        resp = requests.put(
            f"{GRAPH_BASE}/me/drive/items/{existing_id}/content",
            headers=_headers(), data=content,
        )
    else:
        resp = requests.put(
            f"{GRAPH_BASE}/me/drive/items/{folder_id}:/{filename}:/content",
            headers=_headers(), data=content,
        )

    if _handle_errors(resp):
        return save_timesheet(timesheet_data)
    return resp.ok


def load_timesheets():
    user = session.get("user", {})
    email = user.get("email", "unknown")
    folder_id = _ensure_timesheets_folder()
    filename = f"timesheet_{email.replace('@', '_at_')}.json"

    if not folder_id:
        return {"entries": []}

    resp = requests.get(
        f"{GRAPH_BASE}/me/drive/items/{folder_id}:/{filename}:/content",
        headers=_headers(),
    )
    if resp.status_code == 404:
        return {"entries": []}
    if not resp.ok:
        if _handle_errors(resp):
            return load_timesheets()
        return {"entries": []}
    try:
        data = resp.json()
        migrated = False
        for entry in data.get("entries", []):
            if entry.get("activity_type") == "leave_travel":
                t = entry.get("time")
                if t is None:
                    entry["time"] = 8.5
                    migrated = True
                else:
                    try:
                        ft = float(t)
                        if ft == 0 or abs(ft - 8.83) < 0.001:
                            entry["time"] = 8.5
                            migrated = True
                    except (ValueError, TypeError):
                        entry["time"] = 8.5
                        migrated = True
        if migrated:
            try:
                save_timesheet(data)
            except Exception:
                pass
        return data
    except Exception:
        return {"entries": []}
