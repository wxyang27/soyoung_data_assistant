from flask import current_app


class LLMNotConfiguredError(RuntimeError):
    pass


def generate_answer(prompt: str) -> str:
    api_key = current_app.config.get("LLM_API_KEY")
    if not api_key:
        raise LLMNotConfiguredError("LLM_API_KEY is not configured.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMNotConfiguredError("openai package is not installed. Run pip install -r requirements.txt.") from exc

    client = OpenAI(
        api_key=api_key,
        base_url=current_app.config.get("LLM_BASE_URL") or None,
    )
    response = client.chat.completions.create(
        model=current_app.config["LLM_MODEL"],
        messages=[
            {"role": "system", "content": "你是严谨的新氧连锁业务数据智能运营助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=current_app.config["LLM_TEMPERATURE"],
        max_tokens=current_app.config["LLM_MAX_TOKENS"],
    )
    return response.choices[0].message.content or ""
