from flask import Flask, request, jsonify, session
from flask_cors import CORS
from main import app as agent_app
from langchain_core.messages import HumanMessage
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = "starbucks_secret_123"

# Simple user database — we'll store users here for now
users = {}

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data["username"]
    password = data["password"]

    if username in users:
        return jsonify({"error": "Username already exists"}), 400

    users[username] = generate_password_hash(password)
    return jsonify({"message": "Registration successful!"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"]
    password = data["password"]

    if username not in users:
        return jsonify({"error": "User not found"}), 401

    if not check_password_hash(users[username], password):
        return jsonify({"error": "Wrong password"}), 401

    session["username"] = username
    return jsonify({"message": "Login successful!", "username": username})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data["message"]
    thread_id = data.get("thread_id", "default_user")

    config = {"configurable": {"thread_id": thread_id}}

    result = agent_app.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config
    )

    last_message = result["messages"][-1]
    return jsonify({"response": last_message.content})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

    