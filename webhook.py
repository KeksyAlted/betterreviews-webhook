from flask import Flask, request, jsonify
import os
import json
import time

app = Flask(__name__)

TOPGG_WEBHOOK_AUTH = os.getenv("TOPGG_WEBHOOK_AUTH", "")
API_AUTH = os.getenv("WEBHOOK_API_AUTH", "")
VOTES_FILE = "votes.json"


def load_votes():
    if not os.path.exists(VOTES_FILE):
        return {"users": {}}
    try:
        with open(VOTES_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}}


def save_votes(data):
    with open(VOTES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_vote(user_id):
    data = load_votes()
    data["users"][str(user_id)] = time.time() + 43200
    save_votes(data)


def has_vote(user_id):
    data = load_votes()
    exp = data["users"].get(str(user_id))
    if not exp:
        return False
    if time.time() > exp:
        data["users"].pop(str(user_id), None)
        save_votes(data)
        return False
    return True


def consume_vote(user_id):
    data = load_votes()
    data["users"].pop(str(user_id), None)
    save_votes(data)


def check_api(req):
    return req.headers.get("Authorization") == API_AUTH


@app.route("/")
def home():
    return "ok"


@app.route("/topgg", methods=["POST"])
def topgg():
    if request.headers.get("Authorization") != TOPGG_WEBHOOK_AUTH:
        return {"error": "unauthorized"}, 401

    data = request.json or {}
    user = data.get("user") or ((data.get("data") or {}).get("user") or {}).get("id")

    if not user:
        return {"error": "no user"}, 400

    add_vote(int(user))
    print("vote:", user)

    return {"ok": True}


@app.route("/has-vote/<int:user_id>")
def has(user_id):
    if not check_api(request):
        return {"error": "unauthorized"}, 401

    return {"has_vote": has_vote(user_id)}


@app.route("/consume-vote/<int:user_id>", methods=["POST"])
def consume(user_id):
    if not check_api(request):
        return {"error": "unauthorized"}, 401

    if not has_vote(user_id):
        return {"consumed": False}

    consume_vote(user_id)
    return {"consumed": True}
