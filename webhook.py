from flask import Flask, request, jsonify
import os
import json
import time
import requests

app = Flask(__name__)

TOPGG_WEBHOOK_AUTH = os.getenv("TOPGG_WEBHOOK_AUTH", "")
API_AUTH = os.getenv("WEBHOOK_API_AUTH", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
VOTES_FILE = "votes.json"


def load_votes():
    if not os.path.exists(VOTES_FILE):
        return {"users": {}}

    try:
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"users": {}}

            data = json.loads(content)

            if not isinstance(data, dict):
                return {"users": {}}

            if "users" not in data or not isinstance(data["users"], dict):
                data["users"] = {}

            return data
    except Exception:
        return {"users": {}}


def save_votes(data):
    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}

    with open(VOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_unclaimed_vote(user_id: int, hours: int = 12):
    data = load_votes()
    data["users"][str(user_id)] = time.time() + (hours * 3600)
    save_votes(data)


def has_unclaimed_vote(user_id: int) -> bool:
    data = load_votes()
    expires_at = data["users"].get(str(user_id))

    if not expires_at:
        return False

    if time.time() > expires_at:
        data["users"].pop(str(user_id), None)
        save_votes(data)
        return False

    return True


def consume_unclaimed_vote(user_id: int):
    data = load_votes()
    data["users"].pop(str(user_id), None)
    save_votes(data)


def check_api_auth(req) -> bool:
    return req.headers.get("Authorization") == API_AUTH


@app.route("/", methods=["GET"])
def home():
    return "Webhook works", 200


@app.route("/topgg", methods=["POST"])
def topgg_vote():
    auth = request.headers.get("Authorization")

    print("TOPGG HIT")
    print("HEADERS AUTH:", repr(auth))
    print("EXPECTED AUTH:", repr(TOPGG_WEBHOOK_AUTH))

    if auth != TOPGG_WEBHOOK_AUTH:
        print("UNAUTHORIZED")
        return jsonify({"error": "unauthorized"}), 401

    payload = request.json or {}
    print("RAW JSON:", payload)

    user_id = payload.get("user")
    if not user_id:
        user_id = ((payload.get("data") or {}).get("user") or {}).get("id")

    if not user_id:
        print("MISSING USER ID")
        return jsonify({"error": "missing user id"}), 400

    try:
        add_unclaimed_vote(int(user_id), hours=12)
        print(f"Vote stored for user: {user_id}")

        if DISCORD_WEBHOOK_URL:
            try:
                user = await bot.fetch_user(user_id)
                embed = {
                    "title": "New Vote ⭐",
                    "description": f"<@{user_id}> just voted.\nThanks for the support 💜",
                    "color": 0xED4245,
                    "thumbnail": {
                    "url": user.display_avatar.url
                }
            }

                requests.post(
                    DISCORD_WEBHOOK_URL,
                    json={"embeds": [embed]},
                    timeout=10
                )
            except Exception as e:
                print("DISCORD WEBHOOK ERROR:", str(e))

        return jsonify({"ok": True}), 200

    except Exception as e:
        print("SAVE ERROR:", str(e))
        return jsonify({"error": "internal_error"}), 500


@app.route("/has-vote/<int:user_id>", methods=["GET"])
def api_has_vote(user_id: int):
    if not check_api_auth(request):
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({
        "user_id": user_id,
        "has_vote": has_unclaimed_vote(user_id)
    }), 200


@app.route("/consume-vote/<int:user_id>", methods=["POST"])
def api_consume_vote(user_id: int):
    if not check_api_auth(request):
        return jsonify({"error": "unauthorized"}), 401

    if not has_unclaimed_vote(user_id):
        return jsonify({
            "user_id": user_id,
            "consumed": False,
            "reason": "no_active_vote"
        }), 200

    consume_unclaimed_vote(user_id)
    return jsonify({
        "user_id": user_id,
        "consumed": True
    }), 200
