import os
import base64
from io import BytesIO

from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=API_KEY) if API_KEY else None

SYSTEM_PROMPT = """
You are ULTRON, also called DEMIO, an intelligent personal AI supervisor.
You are helpful, friendly, intelligent and professional.
You can teach, mentor, explain, brainstorm and help with coding.
Understand and respond in Tamil and English.
Follow the language used by the user.
Explain things clearly and accurately.
Analyze uploaded images and documents when provided.
Never pretend to have performed an action you did not perform.
"""

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "model": MODEL,
        "ai_configured": client is not None
    })


def extract_document(file):
    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension in ["txt", "md", "csv"]:
        return file.read().decode("utf-8", errors="replace")

    if extension == "pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(file.read()))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )[:30000]
        except Exception as error:
            raise ValueError("Could not read PDF: " + str(error))

    if extension == "docx":
        try:
            from docx import Document
            document = Document(BytesIO(file.read()))
            return "\n".join(p.text for p in document.paragraphs)[:30000]
        except Exception as error:
            raise ValueError("Could not read DOCX: " + str(error))

    raise ValueError("Unsupported file. Upload an image, PDF, DOCX, TXT, MD or CSV.")


@app.route("/api/chat", methods=["POST"])
def chat():
    if client is None:
        return jsonify({
            "error": "OPENAI_API_KEY is missing. Add your API key in Render Environment Variables."
        }), 503

    try:
        message = request.form.get("message", "").strip()
        language = request.form.get("language", "English")
        uploaded = request.files.get("file")

        if not message and not uploaded:
            return jsonify({"error": "Please enter a message or attach a file."}), 400

        content = []

        if message:
            content.append({
                "type": "text",
                "text": message
            })

        if uploaded and uploaded.filename:
            filename = secure_filename(uploaded.filename)
            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

            if extension in ["png", "jpg", "jpeg", "webp", "gif"]:
                raw = uploaded.read()
                mime = uploaded.mimetype or "image/jpeg"

                if not mime.startswith("image/"):
                    return jsonify({"error": "Invalid image type."}), 400

                encoded = base64.b64encode(raw).decode("utf-8")
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{encoded}"
                    }
                })

            else:
                document_text = extract_document(uploaded)
                content.append({
                    "type": "text",
                    "text": (
                        f"\nUploaded document: {filename}\n"
                        f"Document content:\n{document_text}"
                    )
                })

        content.append({
            "type": "text",
            "text": f"\nPreferred response language: {language}."
        })

        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content}
            ],
            temperature=0.7,
            max_tokens=1500
        )

        reply = result.choices[0].message.content or "I could not generate a response."

        return jsonify({
            "reply": reply,
            "audio_text": True,
            "model": MODEL
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        app.logger.exception("AI request failed")
        return jsonify({
            "error": "AI request failed: " + str(error)
        }), 500


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"error": "File too large. Maximum upload size is 12 MB."}), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
