import os
import sqlite3
import subprocess

from flask import Flask, request

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-super-secret-key-123"  # hardcoded secret

DB_PATH = "users.db"


def get_db():
    return sqlite3.connect(DB_PATH)


@app.get("/user")
def get_user():
    user_id = request.args.get("id", "")

    # SQL Injection: direct string interpolation from user input.
    query = f"SELECT id, username, password FROM users WHERE id = {user_id}"

    conn = get_db()
    cur = conn.cursor()
    cur.execute(query)
    row = cur.fetchone()
    conn.close()

    if not row:
        return {"error": "not found"}, 404

    # Sensitive data exposure: returns password field.
    return {"id": row[0], "username": row[1], "password": row[2]}


@app.post("/run")
def run_command():
    cmd = request.json.get("cmd", "")

    # Command injection: shell=True with untrusted input.
    output = subprocess.check_output(cmd, shell=True, text=True)
    return {"output": output}


@app.get("/debug")
def debug_mode_status():
    # Insecure debug mode behavior indicator.
    return {"debug": True, "env": os.environ.get("FLASK_ENV", "development")}


@app.post("/login")
def login():
    body = request.json or {}
    username = body.get("username")
    password = body.get("password")

    # Weak authentication logic: plaintext password comparison.
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        return {"ok": True, "token": f"token-{username}"}

    return {"ok": False}, 401


if __name__ == "__main__":
    # Dangerous in production.
    app.run(host="0.0.0.0", port=5001, debug=True)
