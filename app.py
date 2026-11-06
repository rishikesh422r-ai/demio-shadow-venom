import os
from pathlib import Path
from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory
)
from werkzeug.utils import secure_filename

# ----------------------------------
# DEMIO CONFIGURATION
# ----------------------------------

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"

UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp",
    "mp4", "mov", "avi", "mkv", "webm"
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


# ----------------------------------
# FILE VALIDATION
# ----------------------------------

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ----------------------------------
# HOMEPAGE
# ----------------------------------

@app.route("/", methods=["GET"])
def home():

    index_file = BASE_DIR / "index.html"

    if index_file.exists():
        return send_from_directory(BASE_DIR, "index.html")

    template_file = BASE_DIR / "templates" / "index.html"

    if template_file.exists():
        return send_from_directory(
            BASE_DIR / "templates",
            "index.html"
        )

    return "DEMIO: index.html not found", 404


# ----------------------------------
# CHAT API
# ----------------------------------

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True) or {}

    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "success": False,
            "error": "Message cannot be empty"
        }), 400

    # Demo response.
    # Connect your AI model here for real AI responses.

    return jsonify({
        "success": True,
        "reply": "DEMIO received your message: " + message
    })


# ----------------------------------
# IMAGE AND VIDEO UPLOAD
# ----------------------------------

@app.route("/upload", methods=["POST"])
def upload():

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No file selected"
        }), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({
            "success": False,
            "error": "Empty filename"
        }), 400

    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": "Unsupported file format"
        }), 400

    filename = secure_filename(file.filename)

    if not filename:
        return jsonify({
            "success": False,
            "error": "Invalid filename"
        }), 400

    save_path = UPLOAD_FOLDER / filename

    # Avoid overwriting existing files
    counter = 1

    while save_path.exists():
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        filename = f"{stem}_{counter}{suffix}"
        save_path = UPLOAD_FOLDER / filename
        counter += 1

    file.save(save_path)

    return jsonify({
        "success": True,
        "message": "File uploaded successfully",
        "filename": filename,
        "file_type": Path(filename).suffix.lower()
    })


# ----------------------------------
# HEALTH CHECK
# ----------------------------------

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "online",
        "application": "DEMIO",
        "message": "DEMIO server is running"
    })


# ----------------------------------
# ERROR HANDLING
# ----------------------------------

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "error": "Requested page not found"
    }), 404


@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "success": False,
        "error": "File exceeds the 100 MB limit"
    }), 413


@app.errorhandler(500)
def server_error(error):

    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


# ----------------------------------
# START APPLICATION
# ----------------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
