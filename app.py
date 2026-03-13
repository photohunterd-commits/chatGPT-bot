from flask import Flask, request
import requests
import os
import json

PACHCA_BOT_TOKEN = (os.environ.get("PACHCA_BOT_TOKEN") or "").strip()
DEEPSEEK_API_KEY = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()

app = Flask(__name__)


def send_message(chat_id: int, parent_message_id: int, text: str):
    url = "https://api.pachca.com/api/shared/v1/messages"

    payload = {
        "message": {
            "entity_type": "discussion",
            "entity_id": chat_id,
            "content": text,
            "parent_message_id": parent_message_id
        }
    }

    headers = {
        "Authorization": f"Bearer {PACHCA_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=20)
    print("pachca:", resp.status_code, resp.text[:500], flush=True)
    resp.raise_for_status()


def ask_deepseek(prompt: str) -> str:

    url = "https://api.deepseek.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "Ты полезный ассистент. Отвечай кратко и на русском."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    print("deepseek:", resp.status_code, resp.text[:500], flush=True)
    resp.raise_for_status()

    data = resp.json()

    return data["choices"][0]["message"]["content"]


@app.route("/", methods=["GET"])
def home():
    return "deepseek bot running", 200


@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json(silent=True) or {}
    print("incoming:", json.dumps(data, ensure_ascii=False), flush=True)

    if data.get("type") != "message":
        return "ok", 200

    if data.get("event") != "new":
        return "ok", 200

    text = (data.get("content") or "").strip()
    chat_id = data.get("chat_id")
    message_id = data.get("id")

    if not text or not chat_id or not message_id:
        return "ok", 200

    if not text.lower().startswith("ai "):
        return "ok", 200

    prompt = text[3:].strip()

    try:

        answer = ask_deepseek(prompt)

        send_message(chat_id, message_id, answer)

    except Exception as e:

        print("bot error:", repr(e), flush=True)

        try:
            send_message(chat_id, message_id, "Ошибка при запросе к AI.")
        except:
            pass

    return "ok", 200


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))

    app.run(host="0.0.0.0", port=port)