from flask import Blueprint, current_app, jsonify, render_template, request

from app.services.mock_answer import build_chat_response


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
        }
    )


@bp.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()

    if not question:
        return jsonify({"error": "请输入你的问题。"}), 400

    return jsonify(build_chat_response(question))
