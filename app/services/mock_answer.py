from flask import current_app

from app.services.gross_margin_agent import build_gross_margin_diagnosis
from app.services.intent_recognition import recognize_intent
from app.services.rag_answer import build_rag_sections
from app.services.rag_chain import build_llm_rag_response
from app.services.rag_chain_langchain import build_langchain_rag_response
from app.services.retrieval import search_knowledge


def build_chat_response(question: str) -> dict:
    intent = recognize_intent(question)

    if not current_app.config["MOCK_MODE"]:
        try:
            if current_app.config.get("RAG_ENGINE") == "langchain":
                return build_langchain_rag_response(question, intent)
            return build_llm_rag_response(question, intent)
        except Exception as exc:
            current_app.logger.warning("LLM RAG fallback to mock answer: %s", exc)

    citations = search_knowledge(question, top_k=5)

    if intent.name == "gross_margin_diagnosis":
        answer = build_gross_margin_diagnosis(question)
    elif intent.name == "metric_definition":
        answer = build_metric_definition_answer(question)
    elif intent.name == "metadata_lookup":
        answer = build_metadata_answer(question)
    elif intent.name == "nl2sql_query":
        answer = build_nl2sql_answer(question)
    else:
        answer = build_general_answer(question)

    answer = enrich_answer_with_rag(question, answer, citations)

    return {
        "question": question,
        "intent": {
            "name": intent.name,
            "label": intent.label,
            "confidence": intent.confidence,
        },
        "citations": citations,
        **answer,
    }


def enrich_answer_with_rag(question: str, answer: dict, citations: list[dict]) -> dict:
    rag_parts = build_rag_sections(question, citations)

    return {
        **answer,
        "sections": [*answer.get("sections", []), *rag_parts["sections"]],
        "caliber": [*answer.get("caliber", []), *rag_parts["caliber"]],
    }


def build_metric_definition_answer(question: str) -> dict:
    return {
        "summary": "已识别为指标口径问题。第一阶段先返回标准口径示例，后续接入指标字典 RAG。",
        "sections": [
            {
                "title": "指标口径卡片",
                "items": [
                    "核销收入：统计周期内连锁业务实际到院消费后的收入，字段为 exe_income。",
                    "核销 GMV：统计周期内核销 GMV，字段为 exe_amount。",
                    "品项毛利率：SUM(gross_margin_amt) / SUM(NULLIF(exe_income, 0))。",
                ],
            }
        ],
        "sql": "SELECT SUM(exe_income) AS 核销收入 FROM soyoung_dw.dm_opt_qy_user_execution_record_all_d WHERE dp = DATE_SUB(CURRENT_DATE(), 1) AND is_valid = 1;",
        "caliber": ["收入默认按核销收入理解。", "后续会根据用户问题检索完整指标字典。"],
    }


def build_metadata_answer(question: str) -> dict:
    return {
        "summary": "已识别为表字段查询问题。第一阶段返回毛利率主表核心字段示例。",
        "sections": [
            {
                "title": "毛利率主表",
                "items": [
                    "表名：soyoung_dw.dws_opt_qy_gross_margin_stats_all_d。",
                    "粒度：天 x 品项 x 门店。",
                    "核心字段：stat_date, standard_name, tenant_id, exe_income, ware_cost, manual_fee, gross_margin_amt。",
                ],
            }
        ],
        "sql": "DESC soyoung_dw.dws_opt_qy_gross_margin_stats_all_d;",
        "caliber": ["真实字段以后通过 MaxCompute 元数据同步获得。"],
    }


def build_nl2sql_answer(question: str) -> dict:
    return {
        "summary": "已识别为自然语言取数问题。第一阶段先展示 SQL 生成形态，暂不执行真实查询。",
        "sections": [
            {
                "title": "需求复述",
                "items": ["按默认经营口径查询连锁核销收入，时间范围以后由解析器自动识别。"],
            },
            {
                "title": "口径卡片",
                "items": [
                    "指标：核销收入。",
                    "源表：dm_opt_qy_user_execution_record_all_d。",
                    "过滤：dp 最新快照、is_valid = 1。",
                ],
            },
        ],
        "sql": "SELECT ROUND(SUM(exe_income), 2) AS income FROM soyoung_dw.dm_opt_qy_user_execution_record_all_d WHERE dp = DATE_SUB(CURRENT_DATE(), 1) AND is_valid = 1;",
        "caliber": ["第一阶段不连接 MaxCompute；第二阶段会执行只读查询并返回结果表。"],
    }


def build_general_answer(question: str) -> dict:
    return {
        "summary": "我可以帮助你做连锁业务问数、指标口径解释、毛利率诊断和表字段查询。",
        "sections": [
            {
                "title": "你可以这样问",
                "items": [
                    "帮我复盘一下 5 月品项毛利率。",
                    "品项毛利率怎么算？",
                    "昨天连锁核销收入是多少？",
                    "毛利率主表有哪些字段？",
                ],
            }
        ],
        "sql": "",
        "caliber": ["当前是第一阶段 MVP，重点验证问答交互和展示形态。"],
    }


