import os
import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

SYSTEMS = {
    "chat": "You are DEMIO, a capable personal AI assistant. Be accurate, clear, practical, and honest about limitations.",
    "mentor": "You are DEMIO Mentor, a patient programming and study mentor. Teach step by step, check understanding, use simple examples, and never shame the learner.",
    "exercise": "You are DEMIO Coach. Create useful, appropriately challenging exercises with clear instructions. Do not reveal the answer immediately unless asked.",
    "game": "You are DEMIO Game Master. Be playful, concise, safe, and create interactive text games or trivia."
}

@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")

@app.get("/app.js")
def javascript():
    return send_from_directory(BASE_DIR, "app.js", mimetype="application/javascript")

@app.get("/health")
def health():
    return jsonify({
        "status": "online",
        "assistant": "DEMIO",
        "ai_configured": bool(API_KEY),
        "model": MODEL
    })

@app.post("/api/chat")
def chat():
    if not API_KEY:
        return jsonify({"error": "OPENAI_API_KEY is not configured in Render Environment Variables."}), 503

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    mode = str(data.get("mode", "chat")).lower()
    history = data.get("history", [])
    variables = data.get("variables", {})
    images = data.get("images", [])

    if mode not in SYSTEMS:
        mode = "chat"
    if not message and not images:
        return jsonify({"error": "Please enter a message or attach an image."}), 400

    variable_text = ""
    if isinstance(variables, dict) and variables:
        safe_vars = []
        for key, value in list(variables.items())[:30]:
            safe_vars.append(f"{str(key)[:80]} = {str(value)[:500]}")
        variable_text = "\n\nUser workspace variables:\n" + "\n".join(safe_vars)

    messages = [{"role": "system", "content": SYSTEMS[mode] + variable_text}]

    if isinstance(history, list):
        for item in history[-16:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content[:8000]})

    user_content = []
    if message:
        user_content.append({"type": "text", "text": message})

    if isinstance(images, list):
        for image in images[:3]:
            if isinstance(image, str) and image.startswith("data:image/"):
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": image}
                })

    messages.append({"role": "user", "content": user_content if len(user_content) > 1 or images else message})

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.7
            },
            timeout=90
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if not response.ok:
            error = payload.get("error", {}).get("message", "The AI provider rejected the request.")
            return jsonify({"error": error}), response.status_code

        reply = payload["choices"][0]["message"]["content"]
        if isinstance(reply, list):
            reply = "\n".join(part.get("text", "") for part in reply if isinstance(part, dict))
        if not reply:
            return jsonify({"error": "The AI returned an empty response."}), 502

        return jsonify({"reply": reply, "assistant": "DEMIO"})
    except requests.Timeout:
        return jsonify({"error": "The AI request timed out. Please try again."}), 504
    except requests.RequestException:
        app.logger.exception("AI connection error")
        return jsonify({"error": "Could not connect to the AI provider."}), 502
    except Exception:
        app.logger.exception("Unexpected chat error")
        return jsonify({"error": "Unexpected server error. Check Render logs."}), 500

@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Route not found. Check the Render service and deployed files."}), 404

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Request too large. Try a smaller image."}), 413

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
