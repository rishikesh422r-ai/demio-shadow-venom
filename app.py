import os
import uuid
import requests

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """
You are DEMIO, a helpful, intelligent AI assistant.
Answer the user's questions clearly and accurately.
Be conversational, friendly and useful.
Never pretend that you have performed an action you have not performed.
"""


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "assistant": "DEMIO",
        "ai_configured": bool(API_KEY)
    })


@app.route("/api/chat", methods=["POST"])
@app.route("/chat", methods=["POST"])
def chat():

    if not API_KEY:
        return jsonify({
            "error": "AI API key is missing. Set OPENAI_API_KEY in Render."
        }), 503

    try:
        data = request.get_json(silent=True) or {}

        message = str(data.get("message", "")).strip()
        history = data.get("history", [])
        images = data.get("images", [])

        if not message and not images:
            return jsonify({
                "error": "Please enter a message."
            }), 400

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

        # Previous conversation
        for item in history[-20:]:

            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")

            if role not in ("user", "assistant"):
                continue

            if isinstance(content, str) and content.strip():
                messages.append({
                    "role": role,
                    "content": content[:12000]
                })

        # Current message
        content = []

        if message:
            content.append({
                "type": "text",
                "text": message
            })

        # Images
        for image_data in images[:4]:

            if not isinstance(image_data, str):
                continue

            if not image_data.startswith("data:image/"):
                continue

            content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_data
                }
            })

        if not content:
            return jsonify({
                "error": "No valid message or image received."
            }), 400

        messages.append({
            "role": "user",
            "content": content
        })

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

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_message = error_data.get(
                    "error", {}
                ).get("message", "AI request failed.")
            except Exception:
                error_message = "AI provider returned an error."

            return jsonify({
                "error": error_message
            }), response.status_code

        result = response.json()

        reply = result["choices"][0]["message"]["content"]

        if not reply:
            return jsonify({
                "error": "The AI returned an empty response."
            }), 502

        return jsonify({
            "reply": reply,
            "assistant": "DEMIO"
        })

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "AI response timed out. Please try again."
        }), 504

    except requests.exceptions.RequestException:
        return jsonify({
            "error": "Could not connect to the AI service."
        }), 502

    except Exception as error:
        app.logger.exception("Chat error")

        return jsonify({
            "error": "Server error: " + str(error)
        }), 500


@app.route("/upload", methods=["POST"])
def upload():

    if "file" not in request.files:
        return jsonify({
            "error": "No file received."
        }), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({
            "error": "No filename provided."
        }), 400

    filename = secure_filename(file.filename)

    if not filename:
        return jsonify({
            "error": "Invalid filename."
        }), 400

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    allowed = {
        "png", "jpg", "jpeg", "gif", "webp",
        "mp4", "mov", "avi", "mkv", "webm"
    }

    if extension not in allowed:
        return jsonify({
            "error": "File type not supported."
        }), 400

    unique_name = str(uuid.uuid4()) + "_" + filename

    file.save(os.path.join(UPLOAD_FOLDER, unique_name))

    return jsonify({
        "success": True,
        "filename": unique_name,
        "url": "/uploads/" + unique_name
    })


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Route not found."
    }), 404


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "File is too large. Maximum size is 100 MB."
    }), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
