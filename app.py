import os

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM_PROMPT = (
    "You are DEMIO, a friendly personal AI assistant called Shadow Venom. "
    "Talk like a close friend: short, clear, motivating answers. "
    "Help with learning, ideas, planning and timetables."
)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"ok": True, "key_set": bool(API_KEY)})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "Empty message"}), 400
    if not API_KEY:
        return jsonify({"error": "GEMINI_API_KEY is not set on the server"}), 500

    contents = []
    for item in history[-10:]:
        role = "model" if item.get("role") in ("model", "assistant", "demio") else "user"
        text = (item.get("text") or "").strip()
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
    }

    try:
        resp = requests.post(
            GEMINI_URL,
            headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
            json=payload,
            timeout=30,
        )
        result = resp.json()
        if resp.status_code != 200:
            err = result.get("error", {}).get("message", "Gemini request failed")
            return jsonify({"error": err}), 502
        reply = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"reply": reply})
    except Exception as exc:  # keep the site alive on any failure
        return jsonify({"error": f"Server error: {exc}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
