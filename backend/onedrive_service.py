import json
from datetime import datetime
from flask import session
import requests
from config import Config
from token_store import get as get_tokens, pop as pop_tokens
import settings_store

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
    return {"Authorization": f"Bearer {token}"}


def _find_drive_from_items(items, site_path_like):
    for item in items:
        remote = item.get("remoteItem") or item
        web_url = remote.get("webUrl", "")
        parent = remote.get("parentReference", {})
        if parent.get("driveType") != "documentLibrary":
            continue
        if site_path_like in web_url:
            drive_id = parent.get("driveId")
            if drive_id:
                return drive_id
    return None


def _get_data_drive():
    """Always use personal OneDrive for JSON data storage (reliable with Files.ReadWrite)."""
    return "/me/drive"


def _get_drive_base():
    return "/me/drive"


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


def _get_effective_path():
    user = session.get("user", {})
    email = user.get("email", "")
    if email:
        custom = settings_store.get_timesheet_path(email)
        if custom:
            return custom
    return Config.ONEDRIVE_ROOT_PATH


def _ensure_timesheets_folder():
    """Return the drive root — save JSON files at root level to avoid folder-creation issues."""
    return "root"


def save_timesheet(timesheet_data):
    user = session.get("user", {})
    email = user.get("email", "unknown")
    timesheet_data["user_email"] = email
    timesheet_data["updated_at"] = datetime.utcnow().isoformat()

    drive = _get_data_drive()
    filename = f"timesheet_{email.replace('@', '_at_')}.json"
    content = json.dumps(timesheet_data, indent=2).encode()

    # Check if file already exists
    folder_children = requests.get(
        f"{GRAPH_BASE}{drive}/items/root/children",
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
            f"{GRAPH_BASE}{drive}/items/{existing_id}/content",
            headers={**_headers(), "Content-Type": "application/json"}, data=content,
        )
    else:
        resp = requests.put(
            f"{GRAPH_BASE}{drive}/root:/{filename}:/content",
            headers={**_headers(), "Content-Type": "application/json"}, data=content,
        )

    if _handle_errors(resp):
        return save_timesheet(timesheet_data)
    if not resp.ok:
        print(f"[save_timesheet] PUT {filename} → {resp.status_code}: {resp.text[:200]}")
    return resp.ok


def load_timesheets():
    user = session.get("user", {})
    email = user.get("email", "unknown")
    drive = _get_data_drive()
    filename = f"timesheet_{email.replace('@', '_at_')}.json"

    resp = requests.get(
        f"{GRAPH_BASE}{drive}/root:/{filename}:/content",
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
