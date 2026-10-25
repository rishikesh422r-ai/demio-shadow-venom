import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path.home() / "demio.env")
load_dotenv()  # Also supports environment variables set by your hosting provider.

app = Flask(__name__)
SYSTEM_PROMPT = """You are DEMIO AI — SHADOW VENOM, a friendly futuristic AI companion.
Speak naturally, warmly, and confidently. Help with coding, technology, studies,
English communication, interviews, presentations, planning, motivation, and everyday
questions. Explain difficult things simply. Keep most spoken answers concise and conversational.
Never claim to have a physical body or real emotions; you are represented by an animated avatar."""
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    history = data.get("history", [])
    if not message:
        return jsonify({"error": "Please type or say something first."}), 400

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return jsonify({"error": "The server is missing GROQ_API_KEY. Add it to your hosting environment variables."}), 503

    safe_history = []
    if isinstance(history, list):
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str):
                safe_history.append({"role": role, "content": content[:3000]})

    try:
        client = Groq(api_key=api_key)
        result = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *safe_history,
                      {"role": "user", "content": message[:3000]}],
            max_tokens=450,
            temperature=0.7,
        )
        answer = result.choices[0].message.content or "Sorry, I couldn't form a reply. Please try again."
        return jsonify({"reply": answer})
    except Exception as exc:
        # Avoid returning credentials or internal request details to the browser.
        print("Groq request failed:", type(exc).__name__, str(exc))
        return jsonify({"error": "I couldn't reach the AI service. Check your API key, model access, and server logs."}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
