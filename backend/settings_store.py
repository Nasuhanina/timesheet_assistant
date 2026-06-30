import os
import json
from config import Config

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

STORE_FILE = ".settings_store.json"
COLLECTION = "user_settings"


def _use_firestore():
    if firestore is None:
        return False
    if Config.IS_CLOUD_RUN:
        return True
    if os.getenv("FIRESTORE_PROJECT_ID") or os.getenv("FIRESTORE_EMULATOR_HOST"):
        return True
    return False


def _get_db():
    project = os.getenv("FIRESTORE_PROJECT_ID")
    return firestore.Client(project=project) if project else firestore.Client()


def _read_json():
    try:
        with open(STORE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_json(data):
    with open(STORE_FILE, "w") as f:
        json.dump(data, f)


def _firestore_get(user_id: str, field: str):
    if not _use_firestore():
        return None
    try:
        db = _get_db()
        doc = db.collection(COLLECTION).document(user_id).get()
        if doc.exists:
            return doc.to_dict().get(field)
    except Exception:
        pass
    return None


def _firestore_set(user_id: str, data: dict):
    if not _use_firestore():
        return False
    try:
        db = _get_db()
        db.collection(COLLECTION).document(user_id).set(data, merge=True)
        return True
    except Exception:
        return False


def get_timesheet_path(user_id: str) -> str | None:
    val = _firestore_get(user_id, "timesheet_path")
    if val is not None:
        return val
    store = _read_json()
    return store.get(user_id, {}).get("timesheet_path")


def set_timesheet_path(user_id: str, path: str):
    if not _firestore_set(user_id, {"timesheet_path": path}):
        store = _read_json()
        if user_id not in store:
            store[user_id] = {}
        store[user_id]["timesheet_path"] = path
        _write_json(store)


def get_template_filename(user_id: str) -> str | None:
    val = _firestore_get(user_id, "template_filename")
    if val is not None:
        return val
    store = _read_json()
    return store.get(user_id, {}).get("template_filename")


def set_template_filename(user_id: str, filename: str):
    if not _firestore_set(user_id, {"template_filename": filename}):
        store = _read_json()
        if user_id not in store:
            store[user_id] = {}
        store[user_id]["template_filename"] = filename
        _write_json(store)
