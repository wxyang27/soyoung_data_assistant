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
    ensure_runtime_migrations(db)
    db.commit()


def ensure_runtime_migrations(db: sqlite3.Connection):
    columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(chat_sessions)").fetchall()
    }
    if "status" not in columns:
        db.execute("ALTER TABLE chat_sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if "archived_at" not in columns:
        db.execute("ALTER TABLE chat_sessions ADD COLUMN archived_at TEXT")


def create_chat_session(title: str = "新对话任务", user_id: int = 1) -> dict:
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO chat_sessions (user_id, title, status)
        VALUES (?, ?, 'active')
        """,
        (user_id, title),
    )
    db.commit()
    return get_chat_session(cursor.lastrowid)


def get_chat_session(session_id: int) -> dict:
    db = get_db()
    row = db.execute(
        """
        SELECT id, user_id, title, status, created_at, updated_at, archived_at
        FROM chat_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()
    return dict(row) if row else {}


def list_chat_sessions(include_archived: bool = False) -> list[dict]:
    db = get_db()
    where = "1 = 1" if include_archived else "s.status = 'active'"
    rows = db.execute(
        f"""
        SELECT
            s.id,
            s.title,
            s.status,
            s.created_at,
            s.updated_at,
            s.archived_at,
            COUNT(m.id) AS message_count,
            COALESCE(
                (
                    SELECT content
                    FROM chat_messages latest
                    WHERE latest.session_id = s.id AND latest.role = 'user'
                    ORDER BY latest.id DESC
                    LIMIT 1
                ),
                ''
            ) AS preview
        FROM chat_sessions s
        LEFT JOIN chat_messages m ON m.session_id = s.id
        WHERE {where}
        GROUP BY s.id
        ORDER BY s.updated_at DESC, s.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def update_chat_session_title(session_id: int, title: str) -> dict:
    db = get_db()
    db.execute(
        """
        UPDATE chat_sessions
        SET title = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (title, session_id),
    )
    db.commit()
    return get_chat_session(session_id)


def archive_chat_session(session_id: int) -> dict:
    db = get_db()
    db.execute(
        """
        UPDATE chat_sessions
        SET status = 'archived', archived_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (session_id,),
    )
    db.commit()
    return get_chat_session(session_id)


def delete_chat_session(session_id: int):
    db = get_db()
    db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    db.commit()


def save_chat_exchange(question: str, response: dict, session_id: int = 1):
    db = get_db()
    session = get_chat_session(session_id)
    if not session:
        session = create_chat_session()
        session_id = session["id"]

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
    if session.get("title") in {"默认演示会话", "新对话任务"}:
        update_chat_session_title(session_id, question[:28])
    db.commit()


def list_recent_messages(session_id: int = 1, limit: int = 50):
    db = get_db()
    rows = db.execute(
        """
        SELECT id, session_id, role, content, intent, sql_text, payload_json, created_at
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]
