"""Persistent token store backed by Google Cloud Firestore.
Survives restarts and scales to zero on Cloud Run.
Falls back to local JSON file for local development.
"""

import os
import json
import uuid
import time
from config import Config

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

STORE_FILE = ".token_store.json"
COLLECTION = os.getenv("FIRESTORE_COLLECTION", "tokens")


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


def store(tokens: dict) -> str:
    tid = str(uuid.uuid4())
    if _use_firestore():
        db = _get_db()
        db.collection(COLLECTION).document(tid).set({
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "created_at": time.time(),
        })
    else:
        store = _read_json()
        store[tid] = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "created_at": time.time(),
        }
        _write_json(store)
    return tid


def get(tid: str):
    if _use_firestore():
        db = _get_db()
        doc = db.collection(COLLECTION).document(tid).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
    else:
        store = _read_json()
        data = store.get(tid)
        if data is None:
            return None
    return {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "created_at": data.get("created_at"),
    }


def pop(tid: str):
    if _use_firestore():
        db = _get_db()
        doc_ref = db.collection(COLLECTION).document(tid)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        doc_ref.delete()
    else:
        store = _read_json()
        data = store.pop(tid, None)
        if data is None:
            return None
        _write_json(store)
    return {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "created_at": data.get("created_at"),
    }


def clear():
    if _use_firestore():
        db = _get_db()
        docs = db.collection(COLLECTION).list_documents()
        for doc in docs:
            doc.delete()
    else:
        _write_json({})
