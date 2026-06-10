import requests
from flask import session
from config import Config

API_BASE = "https://api-{endpoint}.gptbots.ai"


def _headers():
    return {
        "Authorization": f"Bearer {Config.GPTBOTS_API_KEY}",
        "Content-Type": "application/json",
    }


def _base_url():
    ep = Config.GPTBOTS_ENDPOINT
    return API_BASE.format(endpoint=ep) if ep else "https://api.gptbots.ai"


def create_conversation(user_id):
    if not Config.GPTBOTS_API_KEY:
        return None, "GPTBOTS_API_KEY not configured"
    url = f"{_base_url()}/v1/conversation"
    resp = requests.post(url, headers=_headers(), json={"user_id": user_id[:32]})
    if not resp.ok:
        return None, f"GPTBots create conversation failed: {resp.status_code} {resp.text}"
    data = resp.json()
    return data.get("conversation_id"), None


def send_message(conversation_id, text, context_text=None):
    if not Config.GPTBOTS_API_KEY:
        return None, "GPTBOTS_API_KEY not configured"

    messages = []

    if context_text:
        messages.append({
            "role": "assistant",
            "content": context_text,
        })

    messages.append({
        "role": "user",
        "content": text,
    })

    url = f"{_base_url()}/v2/conversation/message"
    payload = {
        "conversation_id": conversation_id,
        "response_mode": "blocking",
        "messages": messages,
    }

    resp = requests.post(url, headers=_headers(), json=payload)
    if not resp.ok:
        return None, f"GPTBots send message failed: {resp.status_code} {resp.text}"

    data = resp.json()
    output = data.get("output", [])
    reply_text = ""
    for item in output:
        content = item.get("content", {})
        txt = content.get("text", "")
        if txt:
            reply_text += txt + "\n"

    usage = data.get("usage", {})
    return {
        "reply": reply_text.strip(),
        "conversation_id": data.get("conversation_id"),
        "message_id": data.get("message_id"),
        "usage": usage,
    }, None



