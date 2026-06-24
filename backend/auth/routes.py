import uuid
import urllib.parse
import requests
from flask import Blueprint, redirect, request, jsonify, session
from config import Config
from token_store import store as store_tokens

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login")
def login():
    state = str(uuid.uuid4())
    session["oauth_state"] = state

    redirect_uri = Config.MICROSOFT_REDIRECT_URI
    if Config.IS_CLOUD_RUN:
        redirect_uri = request.url_root.rstrip("/") + "/auth/callback"

    params = {
        "client_id": Config.MICROSOFT_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": " ".join(Config.MICROSOFT_SCOPE),
        "state": state,
    }

    auth_url = f"{Config.MICROSOFT_AUTHORITY}/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


@auth_bp.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        return jsonify({"error": error}), 400

    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400

    state = request.args.get("state")
    stored_state = session.pop("oauth_state", None)

    if not stored_state or state != stored_state:
        return jsonify({"error": "Session expired or state mismatch — try logging in again"}), 400

    token_url = f"{Config.MICROSOFT_AUTHORITY}/oauth2/v2.0/token"

    redirect_uri = Config.MICROSOFT_REDIRECT_URI
    if Config.IS_CLOUD_RUN:
        redirect_uri = request.url_root.rstrip("/") + "/auth/callback"

    data = {
        "client_id": Config.MICROSOFT_CLIENT_ID,
        "client_secret": Config.MICROSOFT_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": " ".join(Config.MICROSOFT_SCOPE),
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(token_url, data=data, headers=headers)

    if not resp.ok:
        return jsonify({
            "error": "Token exchange failed",
            "status": resp.status_code,
            "details": resp.text,
        }), 400

    tokens = resp.json()

    tid = store_tokens(tokens)
    session["token_id"] = tid

    access_token = tokens.get("access_token")
    user_info = _get_user_info(access_token)
    session["user"] = user_info

    frontend_url = Config.FRONTEND_URL
    if Config.IS_CLOUD_RUN:
        frontend_url = request.url_root.rstrip("/")
    return redirect(f"{frontend_url}/dashboard")


@auth_bp.route("/me")
def me():
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"user": user})


@auth_bp.route("/logout")
def logout():
    from token_store import pop as pop_tokens
    tid = session.pop("token_id", None)
    if tid:
        pop_tokens(tid)
    session.clear()
    return jsonify({"message": "Logged out"})


@auth_bp.route("/config-check")
def config_check():
    errors = []
    if not Config.MICROSOFT_CLIENT_ID:
        errors.append("MICROSOFT_CLIENT_ID is empty")
    if not Config.MICROSOFT_CLIENT_SECRET:
        errors.append("MICROSOFT_CLIENT_SECRET is empty")
    if "common" not in Config.MICROSOFT_AUTHORITY and len(Config.MICROSOFT_TENANT_ID) < 10:
        errors.append("MICROSOFT_TENANT_ID looks invalid (must be 'common' or a UUID)")
    return jsonify({
        "ok": len(errors) == 0,
        "errors": errors,
        "tenant_id": Config.MICROSOFT_TENANT_ID,
        "redirect_uri": Config.MICROSOFT_REDIRECT_URI,
        "frontend_url": Config.FRONTEND_URL,
        "authority": Config.MICROSOFT_AUTHORITY,
    })


def _get_user_info(access_token):
    resp = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if resp.ok:
        data = resp.json()
        return {
            "id": data.get("id"),
            "displayName": data.get("displayName"),
            "email": data.get("mail") or data.get("userPrincipalName"),
        }
    return None
