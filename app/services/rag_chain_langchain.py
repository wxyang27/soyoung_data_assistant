import os

from flask import current_app
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek

from app.services.prompt_builder import build_rag_prompt
from app.services.rag_chain import parse_llm_answer, strip_private_content
from app.services.retrieval import search_knowledge


DEFAULT_CALIBER = [
    "???? LangChain ?? RAG ?????",
    "?????????? SQLite ???????????? LangChain Retriever + ????",
    "???????? MaxCompute?Doris ? MySQL ???",
]


def build_langchain_rag_response(question: str, intent) -> dict:
    citations = search_knowledge(question, top_k=5, include_content=True)
    intent_payload = {
        "name": intent.name,
        "label": intent.label,
        "confidence": intent.confidence,
    }
    prompt_text = build_rag_prompt(question, intent_payload, citations)
    answer_text = build_chain().invoke({"prompt": prompt_text}).strip()
    parsed = parse_llm_answer(answer_text)

    return {
        "question": question,
        "intent": intent_payload,
        "summary": parsed["summary"],
        "sections": parsed["sections"],
        "sql": parsed.get("sql", ""),
        "caliber": [*parsed.get("caliber", []), *DEFAULT_CALIBER],
        "citations": [strip_private_content(item) for item in citations],
        "llm_mode": True,
        "rag_engine": "langchain",
        "llm": {
            "provider": current_app.config.get("LLM_PROVIDER", "deepseek"),
            "model": current_app.config.get("LLM_MODEL", "unknown"),
        },
    }


def build_chain():
    api_key = current_app.config.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not configured.")

    # langchain-deepseek reads DEEPSEEK_API_KEY by default.
    os.environ["DEEPSEEK_API_KEY"] = api_key

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "????????????????????"),
            ("human", "{prompt}"),
        ]
    )
    llm = ChatDeepSeek(
        model=current_app.config["LLM_MODEL"],
        temperature=current_app.config["LLM_TEMPERATURE"],
        max_tokens=current_app.config["LLM_MAX_TOKENS"],
    )
    return prompt | llm | StrOutputParser()
