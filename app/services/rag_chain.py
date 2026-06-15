import json
import re

from flask import current_app

from app.services.llm_client import generate_answer
from app.services.prompt_builder import build_rag_prompt
from app.services.retrieval import search_knowledge


DEFAULT_CALIBER = [
    "本回答由 LLM 基于本地知识库检索结果生成。",
    "当前不会执行真实 MaxCompute、Doris 或 MySQL 查询。",
    "如知识库未覆盖具体数据，回答只给出分析路径，不编造数值。",
]


def build_llm_rag_response(question: str, intent) -> dict:
    citations = search_knowledge(question, top_k=5, include_content=True)
    intent_payload = {
        "name": intent.name,
        "label": intent.label,
        "confidence": intent.confidence,
    }
    prompt = build_rag_prompt(question, intent_payload, citations)
    answer_text = generate_answer(prompt).strip()
    parsed = parse_llm_answer(answer_text)

    public_citations = [strip_private_content(item) for item in citations]
    return {
        "question": question,
        "intent": intent_payload,
        "summary": parsed["summary"],
        "sections": parsed["sections"],
        "sql": parsed.get("sql", ""),
        "caliber": [*parsed.get("caliber", []), *DEFAULT_CALIBER],
        "citations": public_citations,
        "llm_mode": True,
        "llm": {
            "provider": current_app.config.get("LLM_PROVIDER", "llm"),
            "model": current_app.config.get("LLM_MODEL", "unknown"),
        },
    }


def parse_llm_answer(text: str) -> dict:
    json_text = extract_json_object(text)
    if json_text:
        try:
            payload = json.loads(json_text)
            return normalize_payload(payload, text)
        except json.JSONDecodeError:
            salvaged = salvage_jsonish_answer(json_text)
            if salvaged:
                return salvaged
    return parse_markdown_answer(text)


def extract_json_object(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start : end + 1]
    return ""


def salvage_jsonish_answer(text: str) -> dict | None:
    summary_match = re.search(r'"summary"\s*:\s*"((?:\\.|[^"\\])*)"', text, flags=re.DOTALL)
    section_matches = re.finditer(
        r'"title"\s*:\s*"((?:\\.|[^"\\])*)"\s*,\s*"items"\s*:\s*\[(.*?)\]',
        text,
        flags=re.DOTALL,
    )

    sections = []
    for match in section_matches:
        title = unescape_json_string(match.group(1))
        items_blob = match.group(2)
        items = [unescape_json_string(item) for item in re.findall(r'"((?:\\.|[^"\\])*)"', items_blob)]
        items = [item.strip() for item in items if item.strip()]
        if title and items:
            sections.append({"title": title, "items": items})

    if not summary_match and not sections:
        return None

    return {
        "summary": unescape_json_string(summary_match.group(1)) if summary_match else first_paragraph(text),
        "sections": sections or [{"title": "AI 诊断回答", "items": split_answer_items(text)}],
        "sql": "",
        "caliber": [],
    }


def unescape_json_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value.replace('\\n', ' ').replace('\\"', '"')

def normalize_payload(payload: dict, raw_text: str) -> dict:
    summary = str(payload.get("summary") or first_paragraph(raw_text))
    sections = normalize_sections(payload.get("sections"))
    if not sections:
        sections = parse_markdown_answer(raw_text)["sections"]

    sql = payload.get("sql") or ""
    if not isinstance(sql, str):
        sql = ""

    caliber = payload.get("caliber") or []
    if isinstance(caliber, str):
        caliber = [caliber]
    caliber = [str(item) for item in caliber if str(item).strip()]

    return {
        "summary": summary,
        "sections": sections,
        "sql": sql.strip(),
        "caliber": caliber,
    }


def normalize_sections(raw_sections) -> list[dict]:
    sections = []
    if not isinstance(raw_sections, list):
        return sections

    for section in raw_sections:
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "分析结果").strip()
        raw_items = section.get("items") or []
        if isinstance(raw_items, str):
            raw_items = [raw_items]
        items = [str(item).strip() for item in raw_items if str(item).strip()]
        if items:
            sections.append({"title": title, "items": items})
    return sections


def parse_markdown_answer(text: str) -> dict:
    sections = []
    current_title = "AI 诊断回答"
    current_items = []

    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        heading = re.match(r"^(?:#{1,4}\s*)?(?:\d+[.、]\s*)?(.{2,24})[:：]?$", clean)
        looks_like_heading = bool(heading and any(keyword in clean for keyword in ["结论", "依据", "诊断", "SQL", "口径", "建议"]))
        if looks_like_heading:
            if current_items:
                sections.append({"title": current_title, "items": current_items})
            current_title = clean.lstrip("# ")
            current_items = []
        else:
            current_items.append(clean.strip("-• "))

    if current_items:
        sections.append({"title": current_title, "items": current_items})
    if not sections:
        sections = [{"title": "AI 诊断回答", "items": split_answer_items(text)}]

    return {
        "summary": first_paragraph(text),
        "sections": sections,
        "sql": "",
        "caliber": [],
    }


def strip_private_content(item: dict) -> dict:
    public = dict(item)
    public.pop("content", None)
    return public


def first_paragraph(text: str) -> str:
    for part in text.split("\n"):
        part = part.strip()
        if part:
            return part.lstrip("#0123456789.、 ")
    return "已基于知识库生成回答。"


def split_answer_items(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        clean = line.strip().strip("-• ")
        if clean:
            items.append(clean)
    return items or [text]

