from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")

    return jsonify({
        "reply": "DEMIO received your message: " + message
    })
