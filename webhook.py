from flask import Flask, request, jsonify
import os

app = Flask(__name__)

TOPGG_WEBHOOK_AUTH = os.getenv("TOPGG_WEBHOOK_AUTH", "")

@app.route("/", methods=["GET"])
def home():
    return "Webhook works", 200

@app.route("/topgg", methods=["POST"])
def topgg_vote():
    auth = request.headers.get("Authorization")

    if auth != TOPGG_WEBHOOK_AUTH:
        return jsonify({"error": "unauthorized"}), 401

    data = request.json or {}
    user_id = data.get("user")

    print(f"Vote from user: {user_id}")

    return jsonify({"ok": True}), 200
