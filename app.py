import os
import io
import json
import base64

from flask import Flask, request, jsonify, send_from_directory
from groq import Groq
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

CHAT_MODEL = os.environ.get(
    "GROQ_CHAT_MODEL",
    "llama-3.3-70b-versatile"
)

VISION_MODEL = os.environ.get(
    "GROQ_VISION_MODEL",
    "qwen/qwen3.8-27b"
)

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

SYSTEM_PROMPT = """
You are DEMIO, a friendly personal AI companion.

Your personality:
- Friendly, supportive, intelligent and respectful.
- Speak naturally in clear English.
- Never switch to Tamil or another language.
- Be gentle and encouraging, never rude or aggressive.
- Help with studying, mentoring, exercises, games and everyday questions.
- Explain difficult subjects in simple steps.
- For water reminders, use gentle and caring language.
- Do not pretend to perform actions you cannot perform.
- When users share images, analyze visible details carefully.
- When users share documents, help summarize and explain them.
- Never claim that you have accessed a user's camera or microphone
  without an actual upload or permission.

You are DEMIO, their personal AI assistant.
"""

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "webp",
    "pdf", "txt", "docx", "csv"
}


def extract_document(file):
    """Extract readable text from supported documents."""

    filename = secure_filename(file.filename or "upload")
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type: " + extension)

    raw = file.read()
    file.seek(0)

    if extension == "txt" or extension == "csv":
        return raw.decode("utf-8", errors="replace")[:20000]

    if extension == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        pages = []

        for page in reader.pages[:30]:
            pages.append(page.extract_text() or "")

        return "\n".join(pages)[:20000]

    if extension == "docx":
        from docx import Document

        document = Document(io.BytesIO(raw))
        return "\n".join(
            paragraph.text for paragraph in document.paragraphs
        )[:20000]

    return ""


def make_image_data(file):
    """Encode an uploaded image for Groq vision."""

    raw = file.read()
    file.seek(0)

    mime = file.mimetype or "image/jpeg"

    if not mime.startswith("image/"):
        raise ValueError("This file is not an image.")

    encoded = base64.b64encode(raw).decode("utf-8")

    return "data:" + mime + ";base64," + encoded


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "application": "DEMIO",
        "engine": "Groq",
        "api_configured": bool(GROQ_API_KEY)
    })


@app.route("/api/chat", methods=["POST"])
def chat():

    if not client:
        return jsonify({
            "error": "GROQ_API_KEY is missing. Add it in Render environment variables."
        }), 500

    try:
        message = request.form.get("message", "").strip()

        if not message:
            message = "Please examine the uploaded file."

        language = request.form.get("language", "English")

        # Always keep the interface and replies in English.
        if language.lower() != "english":
            language = "English"

        uploaded_files = (
            request.files.getlist("file") +
            request.files.getlist("files")
        )

        uploaded_files = [
            file for file in uploaded_files if file.filename
        ]

        if not message and not uploaded_files:
            return jsonify({
                "error": "Please enter a message or upload a file."
            }), 400

        if len(uploaded_files) > 5:
            return jsonify({
                "error": "You can upload a maximum of 5 files at once."
            }), 400

        history_text = request.form.get("history", "[]")

        try:
            history = json.loads(history_text)
        except json.JSONDecodeError:
            history = []

        if not isinstance(history, list):
            history = []

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        for item in history[-12:]:
            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")

            if role in ("user", "assistant") and isinstance(content, str):
                messages.append({
                    "role": role,
                    "content": content[:8000]
                })

        image_parts = []
        document_parts = []

        for file in uploaded_files:
            filename = secure_filename(file.filename or "upload")
            extension = filename.rsplit(".", 1)[-1].lower()

            if extension not in ALLOWED_EXTENSIONS:
                return jsonify({
                    "error": "Unsupported file: " + filename
                }), 400

            if extension in ("png", "jpg", "jpeg", "webp"):
                if file.mimetype and not file.mimetype.startswith("image/"):
                    return jsonify({
                        "error": "Invalid image content type."
                    }), 400

                image_parts.append(
                    (filename, make_image_data(file))
                )

            else:
                extracted = extract_document(file)

                document_parts.append(
                    "\nDOCUMENT: " + filename +
                    "\n" + extracted
                )

        user_text = (
            "User message: " + message +
            "\nResponse language: English."
        )

        if document_parts:
            user_text += (
                "\n\nUploaded document contents:\n" +
                "\n".join(document_parts)
            )

        if image_parts:
            content = [
                {"type": "text", "text": user_text}
            ]

            for filename, image_data in image_parts[:3]:
                content.append({
                    "type": "text",
                    "text": "Uploaded image: " + filename
                })

                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_data
                    }
                })

            messages.append({
                "role": "user",
                "content": content
            })

            model = VISION_MODEL

        else:
            messages.append({
                "role": "user",
                "content": user_text
            })

            model = CHAT_MODEL

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_completion_tokens=2048
        )

        reply = completion.choices[0].message.content

        return jsonify({
            "reply": reply or "I could not generate a response.",
            "model": model,
            "language": "English"
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        print("DEMIO BACKEND ERROR:", repr(error))

        return jsonify({
            "error": str(error)
        }), 500


@app.errorhandler(413)
def too_large(error):
    return jsonify({
        "error": "File too large. Maximum upload size is 15 MB."
    }), 413


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
