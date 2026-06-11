import json
import sqlite3
from pathlib import Path

from flask import current_app, g


def resolve_db_path() -> Path:
    db_path = Path(current_app.config["APP_DB_PATH"])
    if not db_path.is_absolute():
        db_path = Path(current_app.root_path).parent / db_path
    return db_path


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = resolve_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    schema_path = Path(current_app.root_path).parent / "sql" / "sqlite_schema.sql"
    with schema_path.open("r", encoding="utf-8") as f:
        schema_sql = f.read()

    db = get_db()
    db.executescript(schema_sql)
    db.commit()


def save_chat_exchange(question: str, response: dict, session_id: int = 1):
    db = get_db()
    db.execute(
        """
        INSERT INTO chat_messages (session_id, role, content, intent, sql_text, payload_json)
        VALUES (?, 'user', ?, NULL, NULL, NULL)
        """,
        (session_id, question),
    )
    db.execute(
        """
        INSERT INTO chat_messages (session_id, role, content, intent, sql_text, payload_json)
        VALUES (?, 'assistant', ?, ?, ?, ?)
        """,
        (
            session_id,
            response.get("summary", ""),
            response.get("intent", {}).get("name"),
            response.get("sql", ""),
            json.dumps(response, ensure_ascii=False),
        ),
    )
    db.execute(
        "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (session_id,),
    )
    db.commit()


def list_recent_messages(limit: int = 20):
    db = get_db()
    rows = db.execute(
        """
        SELECT id, session_id, role, content, intent, sql_text, payload_json, created_at
        FROM chat_messages
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]
