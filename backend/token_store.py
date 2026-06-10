"""Persistent token store backed by a JSON file.
Survives server restarts unlike the in-memory version.
"""

import json
import os
import uuid
import time

_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_store.json")


def _load():
    if not os.path.exists(_STORE_PATH):
        return {}
    try:
        with open(_STORE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(store):
    with open(_STORE_PATH, "w") as f:
        json.dump(store, f)


def store(tokens: dict) -> str:
    tid = str(uuid.uuid4())
    store = _load()
    store[tid] = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "created_at": time.time(),
    }
    _save(store)
    return tid


def get(tid: str):
    store = _load()
    return store.get(tid)


def pop(tid: str):
    store = _load()
    result = store.pop(tid, None)
    _save(store)
    return result


def clear():
    if os.path.exists(_STORE_PATH):
        os.remove(_STORE_PATH)
