import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from app import create_app
from app.db import get_db, init_db
from audit_knowledge import extract_text


RAW_DIR = PROJECT_ROOT / "knowledge" / "raw"
CURATED_DIR = PROJECT_ROOT / "knowledge" / "curated"


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def infer_topic(path: Path, text: str) -> str:
    haystack = f"{path.name}\n{text[:2000]}"
    rules = [
        ("gross_margin", ["毛利", "让利", "补贴", "0元", "灌券", "绿标品"]),
        ("metric_dictionary", ["指标字典", "原子指标", "衍生指标", "口径"]),
        ("table_metadata", ["数据库表", "表地图", "字段", "关联键"]),
        ("sql_example", ["SELECT", "WITH", "GROUP BY", "ORDER BY"]),
        ("business_analysis", ["经营分析", "拆解", "分析方法论", "七步"]),
        ("supply_chain", ["供应链", "ERP", "耗材", "库存"]),
    ]
    for topic, keywords in rules:
        if any(keyword in haystack for keyword in keywords):
            return topic
    return "general"


def infer_doc_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".sql":
        return "sql"
    if suffix in {".md", ".txt"}:
        return "text"
    if suffix == ".docx":
        return "docx"
    if suffix == ".xlsx":
        return "spreadsheet"
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".pdf":
        return "pdf"
    return "unknown"


def split_by_heading(text: str) -> list[tuple[str, str]]:
    blocks = []
    current_title = "未命名片段"
    current_lines = []
    heading_pattern = re.compile(r"^(#{1,6}\s+.+|第[一二三四五六七八九十0-9]+[章节部分].+|--\s*[A-Z0-9一二三四五六七八九十].+)$")

    for line in text.splitlines():
        stripped = line.strip()
        is_heading = bool(heading_pattern.match(stripped))
        if is_heading and current_lines:
            blocks.append((current_title, "\n".join(current_lines).strip()))
            current_title = stripped.lstrip("#").strip()
            current_lines = [line]
        else:
            if is_heading:
                current_title = stripped.lstrip("#").strip()
            current_lines.append(line)

    if current_lines:
        blocks.append((current_title, "\n".join(current_lines).strip()))
    return [(title, content) for title, content in blocks if content]


def split_long_block(title: str, content: str, max_chars: int, overlap: int) -> list[tuple[str, str]]:
    if len(content) <= max_chars:
        return [(title, content)]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    chunks = []
    current = ""
    part_index = 1

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
            continue

        if current:
            chunks.append((f"{title} · {part_index}", current))
            part_index += 1
            current = current[-overlap:] if overlap and len(current) > overlap else ""

        if len(paragraph) > max_chars:
            start = 0
            while start < len(paragraph):
                end = min(start + max_chars, len(paragraph))
                chunks.append((f"{title} · {part_index}", paragraph[start:end]))
                part_index += 1
                start = end
            current = ""
        else:
            current = paragraph

    if current:
        chunks.append((f"{title} · {part_index}", current))
    return chunks


def chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[tuple[str, str]]:
    chunks = []
    for title, block in split_by_heading(text):
        chunks.extend(split_long_block(title, block, max_chars=max_chars, overlap=overlap))
    return chunks


def upsert_document(db: sqlite3.Connection, path: Path, text: str, status: str, error: str | None = None) -> int:
    rel_path = str(path.relative_to(PROJECT_ROOT))
    db.execute(
        """
        INSERT INTO kb_documents (
            source_path, filename, file_type, status, content_hash,
            char_count, chunk_count, error_message, imported_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(source_path) DO UPDATE SET
            filename=excluded.filename,
            file_type=excluded.file_type,
            status=excluded.status,
            content_hash=excluded.content_hash,
            char_count=excluded.char_count,
            chunk_count=0,
            error_message=excluded.error_message,
            imported_at=CURRENT_TIMESTAMP
        """,
        (
            rel_path,
            path.name,
            infer_doc_type(path),
            status,
            stable_hash(text) if text else None,
            len(text),
            error,
        ),
    )
    row = db.execute("SELECT id FROM kb_documents WHERE source_path = ?", (rel_path,)).fetchone()
    document_id = row["id"]
    db.execute("DELETE FROM kb_chunks WHERE document_id = ?", (document_id,))
    return document_id


def insert_chunks(db: sqlite3.Connection, document_id: int, path: Path, text: str, chunks: list[tuple[str, str]]):
    topic = infer_topic(path, text)
    doc_type = infer_doc_type(path)
    for index, (title, content) in enumerate(chunks):
        metadata = {
            "source_path": str(path.relative_to(PROJECT_ROOT)),
            "file_type": doc_type,
            "topic": topic,
            "chunk_index": index,
        }
        db.execute(
            """
            INSERT INTO kb_chunks (
                document_id, chunk_index, title, content,
                char_count, token_estimate, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                index,
                title[:200],
                content,
                len(content),
                max(1, len(content) // 2),
                json.dumps(metadata, ensure_ascii=False),
            ),
        )
    db.execute("UPDATE kb_documents SET chunk_count = ? WHERE id = ?", (len(chunks), document_id))


def iter_source_files(include_curated: bool):
    roots = [RAW_DIR]
    if include_curated:
        roots.append(CURATED_DIR)
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                yield path


def ingest(include_curated: bool, max_chars: int, overlap: int):
    app = create_app()
    imported = 0
    skipped = 0
    total_chunks = 0

    with app.app_context():
        init_db()
        db = get_db()

        for path in iter_source_files(include_curated=include_curated):
            try:
                text, status = extract_text(path)
                if status != "ok" or not text:
                    upsert_document(db, path, "", status=status, error=f"extract status: {status}")
                    skipped += 1
                    continue

                chunks = chunk_text(text, max_chars=max_chars, overlap=overlap)
                document_id = upsert_document(db, path, text, status="imported")
                insert_chunks(db, document_id, path, text, chunks)
                imported += 1
                total_chunks += len(chunks)
                print(f"OK {path.relative_to(PROJECT_ROOT)} -> {len(chunks)} chunks")
            except Exception as exc:
                upsert_document(db, path, "", status="error", error=str(exc))
                skipped += 1
                print(f"ERR {path.relative_to(PROJECT_ROOT)} -> {exc}")

        db.commit()

    print()
    print(f"Knowledge ingestion finished: imported={imported}, skipped={skipped}, chunks={total_chunks}")


def main():
    parser = argparse.ArgumentParser(description="Ingest raw/curated knowledge files into local SQLite.")
    parser.add_argument("--include-curated", action="store_true", help="Also ingest knowledge/curated files.")
    parser.add_argument("--max-chars", type=int, default=900)
    parser.add_argument("--overlap", type=int, default=120)
    args = parser.parse_args()
    ingest(include_curated=args.include_curated, max_chars=args.max_chars, overlap=args.overlap)


if __name__ == "__main__":
    main()
