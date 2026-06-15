import json
import re

from app.db import get_db


DOMAIN_TERMS = [
    "毛利率",
    "品项",
    "核销收入",
    "核销",
    "支付GMV",
    "支付",
    "GMV",
    "L0",
    "灌券",
    "纯薅",
    "0元单",
    "0 元单",
    "补贴",
    "让利",
    "会员等级",
    "耗材",
    "手工费",
    "绿标品",
    "常规品",
    "大师团",
    "表",
    "字段",
    "SQL",
    "客单价",
]

STOP_TERMS = {"怎么", "为什么", "一下", "哪些", "什么", "如何", "多少", "帮我", "请问"}


def normalize(text: str) -> str:
    return (text or "").lower().replace(" ", "")


def cjk_ngrams(text: str) -> set[str]:
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]+", text))
    terms = set()
    for size in (2, 3, 4):
        for index in range(0, max(len(cjk) - size + 1, 0)):
            terms.add(cjk[index : index + size])
    return terms


def extract_terms(query: str) -> list[str]:
    terms = set()
    normalized_query = normalize(query)

    for term in DOMAIN_TERMS:
        if normalize(term) in normalized_query:
            terms.add(term)

    for token in re.findall(r"[A-Za-z0-9_]+", query):
        if len(token) >= 2:
            terms.add(token)

    for term in cjk_ngrams(query):
        if term not in STOP_TERMS:
            terms.add(term)

    if "毛利率" in query or "毛利" in query:
        terms.update(["gross_margin_amt", "exe_income", "ware_cost", "manual_fee", "公式", "计算", "口径"])
    if "L0" in query or "灌券" in query:
        terms.update(["L0", "灌券", "纯薅", "0元单", "补贴率", "会员等级"])
    if "核销收入" in query:
        terms.update(["dm_opt_qy_user_execution_record_all_d", "exe_income", "is_valid"])
    if "0元单" in query or "0 元单" in query:
        terms.update(["0元单", "零元单", "zero_cost", "手工费", "耗材", "会员等级"])

    return sorted(terms, key=len, reverse=True)


def parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def score_chunk(query: str, terms: list[str], row: dict) -> int:
    title = row.get("title") or ""
    content = row.get("content") or ""
    source = row.get("source_path") or ""
    metadata = parse_metadata(row.get("metadata_json"))
    topic = metadata.get("topic", "")

    score = 0
    normalized_title = normalize(title)
    normalized_content = normalize(content)
    normalized_source = normalize(source)

    for term in terms:
        normalized_term = normalize(term)
        if not normalized_term:
            continue
        score += normalized_title.count(normalized_term) * 8
        score += normalized_content.count(normalized_term) * 3
        score += normalized_source.count(normalized_term) * 2

    if "毛利" in query and topic == "gross_margin":
        score += 20
    if "L0" in query or "灌券" in query:
        coupon_signal = (
            normalized_title.count("l0")
            + normalized_content.count("l0")
            + normalized_title.count("灌券")
            + normalized_content.count("灌券")
            + normalized_title.count("纯薅")
            + normalized_content.count("纯薅")
            + normalized_title.count("发券")
            + normalized_content.count("发券")
            + normalized_title.count("补贴率")
            + normalized_content.count("补贴率")
        )
        score += coupon_signal * 30
    if ("表" in query or "字段" in query) and topic == "table_metadata":
        score += 15
    if ("sql" in query.lower() or "怎么查" in query) and topic == "sql_example":
        score += 12
    if "口径" in query and topic == "metric_dictionary":
        score += 12

    return score


def snippet(content: str, terms: list[str], width: int = 180) -> str:
    compact = re.sub(r"\s+", " ", content or "").strip()
    if not compact:
        return ""

    positions = []
    normalized = normalize(compact)
    for term in terms:
        pos = normalized.find(normalize(term))
        if pos >= 0:
            positions.append(pos)

    start = max(min(positions) - 40, 0) if positions else 0
    return compact[start : start + width]


def search_knowledge(query: str, top_k: int = 5, include_content: bool = False) -> list[dict]:
    terms = extract_terms(query)
    if not terms:
        return []

    db = get_db()
    rows = db.execute(
        """
        SELECT
            c.id,
            c.title,
            c.content,
            c.char_count,
            c.metadata_json,
            d.filename,
            d.source_path,
            d.file_type
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE d.status = 'imported'
        """
    ).fetchall()

    ranked = []
    for row in rows:
        item = dict(row)
        score = score_chunk(query, terms, item)
        if score <= 0:
            continue
        metadata = parse_metadata(item.get("metadata_json"))
        result = {
            "chunk_id": item["id"],
            "title": item["title"],
            "filename": item["filename"],
            "source_path": item["source_path"],
            "file_type": item["file_type"],
            "topic": metadata.get("topic", "general"),
            "score": score,
            "snippet": snippet(item["content"], terms),
        }
        if include_content:
            result["content"] = item["content"]
        ranked.append(result)

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_k]
