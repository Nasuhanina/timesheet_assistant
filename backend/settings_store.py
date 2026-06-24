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


def get_timesheet_path(user_id: str) -> str | None:
    if _use_firestore():
        db = _get_db()
        doc = db.collection(COLLECTION).document(user_id).get()
        if doc.exists:
            return doc.to_dict().get("timesheet_path")
        return None
    store = _read_json()
    return store.get(user_id, {}).get("timesheet_path")


def set_timesheet_path(user_id: str, path: str):
    if _use_firestore():
        db = _get_db()
        db.collection(COLLECTION).document(user_id).set({
            "timesheet_path": path,
        })
    else:
        store = _read_json()
        if user_id not in store:
            store[user_id] = {}
        store[user_id]["timesheet_path"] = path
        _write_json(store)


def get_template_filename(user_id: str) -> str | None:
    if _use_firestore():
        db = _get_db()
        doc = db.collection(COLLECTION).document(user_id).get()
        if doc.exists:
            return doc.to_dict().get("template_filename")
        return None
    store = _read_json()
    return store.get(user_id, {}).get("template_filename")


def set_template_filename(user_id: str, filename: str):
    if _use_firestore():
        db = _get_db()
        db.collection(COLLECTION).document(user_id).set({
            "template_filename": filename,
        }, merge=True)
    else:
        store = _read_json()
        if user_id not in store:
            store[user_id] = {}
        store[user_id]["template_filename"] = filename
        _write_json(store)
