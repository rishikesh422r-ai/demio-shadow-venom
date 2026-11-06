import os
import base64
from io import BytesIO

from flask import Flask, request, jsonify, send_from_directory
from groq import Groq
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

TEXT_MODEL = "openai/gpt-oss-120b"
VISION_MODEL = "qwen/qwen3.8-27b"

SYSTEM_PROMPT = """
You are ULTRON 2099, also known as DEMIO.
You are a friendly, intelligent personal AI supervisor.
You can teach, mentor, explain, help with coding and answer questions.
Understand Tamil and English.
Reply in the language the user uses.
Be clear, accurate and helpful.
Analyze uploaded images and documents when possible.
Never claim to perform actions you did not perform.
"""

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "provider": "Groq",
        "configured": client is not None
    })


def read_document(file):
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("txt", "md", "csv"):
        return file.read().decode("utf-8", errors="replace")[:30000]

    if ext == "pdf":
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(file.read()))
        return "\n".join(
            page.extract_text() or "" for page in reader.pages
        )[:30000]

    if ext == "docx":
        from docx import Document
        doc = Document(BytesIO(file.read()))
        return "\n".join(p.text for p in doc.paragraphs)[:30000]

    raise ValueError("Supported files: PDF, DOCX, TXT, MD, CSV, PNG, JPG and WEBP.")


@app.route("/api/chat", methods=["POST"])
def chat():
    if client is None:
        return jsonify({
            "error": "GROQ_API_KEY is missing. Add your Groq key in Render Environment."
        }), 503

    try:
        message = request.form.get("message", "").strip()
        language = request.form.get("language", "English")
        uploaded = request.files.get("file")

        if not message and not (uploaded and uploaded.filename):
            return jsonify({"error": "Enter a message or attach a file."}), 400

        content = []
        has_image = False

        if message:
            content.append({
                "type": "text",
                "text": message
            })

        if uploaded and uploaded.filename:
            filename = secure_filename(uploaded.filename)
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

            if ext in ("png", "jpg", "jpeg", "webp"):
                raw = uploaded.read()
                mime = uploaded.mimetype or "image/jpeg"

                if len(raw) > 8 * 1024 * 1024:
                    return jsonify({"error": "Image must be smaller than 8 MB."}), 400

                if mime not in ("image/png", "image/jpeg", "image/webp"):
                    return jsonify({"error": "Unsupported image format."}), 400

                encoded = base64.b64encode(raw).decode("utf-8")
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{encoded}"
                    }
                })
                has_image = True
            else:
                document_text = read_document(uploaded)
                content.append({
                    "type": "text",
                    "text": f"\nDocument: {filename}\n{document_text}"
                })

        content.append({
            "type": "text",
            "text": f"\nRespond in {language} when appropriate."
        })

        model = VISION_MODEL if has_image else TEXT_MODEL

        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content}
            ],
            temperature=0.7,
            max_tokens=1500
        )

        reply = result.choices[0].message.content or "Please try again."

        return jsonify({
            "reply": reply,
            "audio_text": True,
            "provider": "Groq",
            "model": model
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        app.logger.exception("Groq request failed")
        return jsonify({"error": "Groq AI error: " + str(error)}), 500


@app.errorhandler(413)
def too_large(error):
    return jsonify({"error": "File exceeds the 12 MB limit."}), 413


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
