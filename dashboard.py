import threading
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
from app import LinkedInAgent
from auto import start_messaging_bot
from linkedin_auto_connect import LinkedInAutoConnector

app = Flask(__name__)
app.secret_key = "dev-secret"
import logging
logging.getLogger("werkzeug").setLevel(logging.WARNING)

TASKS = {"post": [], "connect": [], "messaging": []}
_task_counter = 0

def _create_task(kind, payload):
    global _task_counter
    _task_counter += 1
    task = {"id": _task_counter, "kind": kind, "status": "running", "payload": payload, "message": ""}
    TASKS[kind].append(task)
    return task

def run_post(email, password, openai_key, industry, topic, task_id=None):
    agent = LinkedInAgent(email=email, password=password, openai_api_key=openai_key)
    agent.setup_driver()
    if not agent.login():
        _mark_task(task_id, "error", "login failed")
        return
    content = agent.generate_topic_content(industry, topic) if topic else agent.generate_unique_content(industry)
    agent.create_post(content)
    if agent.driver:
        agent.driver.quit()
    _mark_task(task_id, "completed", "post created")

def run_connect(email, password, keyword, max_connections, task_id=None):
    bot = LinkedInAutoConnector()
    if not bot.setup_driver():
        _mark_task(task_id, "error", "driver setup failed")
        return
    if not bot.login(email, password):
        _mark_task(task_id, "error", "login failed")
        bot.close()
        return
    if keyword:
        sent = bot.search_and_connect_by_keyword(keyword, max_connections)
    else:
        sent = bot.run_auto_connection_campaign(total_connections=max_connections) or 0
    bot.close()
    _mark_task(task_id, "completed", f"connections attempted: {sent}")

def run_messaging(email, password, gemini_key, task_id=None):
    ok = start_messaging_bot(email, password, gemini_key)
    _mark_task(task_id, "completed" if ok else "error", "messaging exited")

@app.route("/", methods=["GET"]) 
def index():
    root = os.path.dirname(__file__)
    return send_file(os.path.join(root, "index.html"))

@app.route("/dashboard", methods=["GET"]) 
def dashboard():
    return render_template("index_golden.html")

@app.route("/post", methods=["POST"]) 
def post():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    openai_key = request.form.get("openai_key", "").strip()
    industry = request.form.get("industry", "tech").strip()
    topic = request.form.get("topic", "").strip()
    if not email or not password:
        flash("Email and password required", "error")
        return redirect(url_for("dashboard"))
    task = _create_task("post", {"email": email, "industry": industry, "topic": topic})
    threading.Thread(target=run_post, args=(email, password, openai_key, industry, topic, task["id"] if isinstance(task, dict) else task), daemon=True).start()
    flash("Post task started", "info")
    return redirect(url_for("dashboard"))

@app.route("/connect", methods=["POST"]) 
def connect():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    keyword = request.form.get("keyword", "").strip()
    max_connections = int(request.form.get("max_connections", "20"))
    if not email or not password:
        flash("Email and password required", "error")
        return redirect(url_for("dashboard"))
    task = _create_task("connect", {"email": email, "keyword": keyword, "max": max_connections})
    threading.Thread(target=run_connect, args=(email, password, keyword, max_connections, task["id"] if isinstance(task, dict) else task), daemon=True).start()
    wants_json = (request.args.get("format") == "json") or ("application/json" in (request.headers.get("Accept") or ""))
    if wants_json:
        return jsonify({"task_id": task["id"], "status_url": url_for("status", _external=True)}), 202
    flash("Connection task started", "info")
    return redirect(url_for("index"))

@app.route("/messaging", methods=["POST"]) 
def messaging():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    gemini_key = request.form.get("gemini_key", "").strip()
    if not email or not password:
        flash("Email and password required", "error")
        return redirect(url_for("index"))
    task = _create_task("messaging", {"email": email})
    threading.Thread(target=run_messaging, args=(email, password, gemini_key, task["id"] if isinstance(task, dict) else task), daemon=True).start()
    flash("Messaging bot started", "info")
    return redirect(url_for("dashboard"))

def _mark_task(task_id, status, message):
    try:
        for kind in TASKS:
            for t in TASKS[kind]:
                if t.get("id") == task_id:
                    t["status"] = status
                    t["message"] = message
                    return
    except Exception:
        pass

@app.route("/status", methods=["GET"]) 
def status():
    return jsonify(TASKS)

@app.route("/logs", methods=["GET"]) 
def logs():
    def tail(path, max_chars=6000):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                data = f.read()
                return data[-max_chars:]
        except Exception:
            return ""
    return jsonify({
        "agent": tail("linkedin_agent.log"),
        "connect": tail("linkedin_connect.log")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)