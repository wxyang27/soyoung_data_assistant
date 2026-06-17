from flask import Blueprint, current_app, jsonify, render_template, request

from app.db import (
    archive_chat_session,
    create_chat_session,
    delete_chat_session,
    list_chat_sessions,
    list_recent_messages,
    save_chat_exchange,
    update_chat_session_title,
)
from app.services.mock_answer import build_chat_response
from app.services.retrieval import search_knowledge


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("chat.html")


@bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "app": current_app.config["APP_NAME"],
            "version": current_app.config["APP_VERSION"],
            "mock_mode": current_app.config["MOCK_MODE"],
            "db_path": current_app.config["APP_DB_PATH"],
        }
    )


@bp.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    session_id = payload.get("session_id") or 1

    if not question:
        return jsonify({"error": "请输入你的问题。"}), 400

    response = build_chat_response(question)
    save_chat_exchange(question, response, session_id=int(session_id))
    response["session_id"] = int(session_id)
    return jsonify(response)


@bp.get("/api/history")
def history():
    session_id = request.args.get("session_id", default=1, type=int)
    return jsonify({"messages": list_recent_messages(session_id=session_id, limit=80)})


@bp.get("/api/sessions")
def sessions():
    include_archived = request.args.get("include_archived", "false").lower() == "true"
    return jsonify({"sessions": list_chat_sessions(include_archived=include_archived)})


@bp.post("/api/sessions")
def create_session():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "新对话任务").strip()[:40]
    return jsonify({"session": create_chat_session(title=title)})


@bp.patch("/api/sessions/<int:session_id>")
def update_session(session_id: int):
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()[:40]
    if not title:
        return jsonify({"error": "请输入会话标题。"}), 400
    return jsonify({"session": update_chat_session_title(session_id, title)})


@bp.post("/api/sessions/<int:session_id>/archive")
def archive_session(session_id: int):
    return jsonify({"session": archive_chat_session(session_id)})


@bp.delete("/api/sessions/<int:session_id>")
def delete_session(session_id: int):
    delete_chat_session(session_id)
    return jsonify({"ok": True})


@bp.get("/api/retrieve")
def retrieve():
    query = (request.args.get("q") or "").strip()
    top_k = request.args.get("top_k", default=5, type=int)

    if not query:
        return jsonify({"error": "请输入检索问题。"}), 400

    return jsonify({"query": query, "chunks": search_knowledge(query, top_k=top_k)})
