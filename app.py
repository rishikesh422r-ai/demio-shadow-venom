import os
from flask import Flask, request, jsonify, send_from_directory
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".")

api_key = os.getenv("GROQ_API_KEY")

client = Groq(api_key=api_key) if api_key else None

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    if not client:
        return jsonify({"error": "Groq API key is missing on server"}), 500

    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "Message is required"}), 400

    messages = [{
        "role": "system",
        "content": (
            "You are ULTRON, an advanced futuristic AI assistant. "
            "Respond intelligently, confidently and concisely. "
            "Call the user Creator."
        )
    }]

    for item in history[-12:]:
        if item.get("role") in ("user", "assistant"):
            messages.append({
                "role": item["role"],
                "content": str(item.get("content", ""))[:4000]
            })

    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )

        return jsonify({
            "reply": response.choices[0].message.content
        })

    except Exception:
        app.logger.exception("Groq request failed")
        return jsonify({"error": "AI core connection failed"}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
