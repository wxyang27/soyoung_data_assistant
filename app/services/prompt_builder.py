def build_rag_prompt(question: str, intent: dict, citations: list[dict]) -> str:
    context = format_context(citations)
    return f"""你是新氧连锁数据智能运营助手，服务对象是连锁医美数据仓库/经营分析团队。

你的任务：基于【知识库片段】回答用户问题。请优先使用给定片段，不要编造未出现的数据结论。
如果知识库不足以回答，请明确说明缺少哪些数据或口径。

用户问题：{question}
识别意图：{intent.get('label', intent.get('name', '未知'))}

【知识库片段】
{context}

请只输出合法 JSON，不要使用 Markdown 代码块，不要输出 JSON 之外的解释文字。
JSON 结构如下：
{{
  "summary": "2-3 句话结论先行，直接回答用户问题",
  "sections": [
    {{"title": "一、业务依据", "items": ["关键口径、字段、表或业务现象"]}},
    {{"title": "二、诊断路径", "items": ["按哪些维度下钻，为什么"]}},
    {{"title": "三、SQL/口径提醒", "items": ["SQL 或字段线索；没有就说明暂未命中"]}},
    {{"title": "四、下一步建议", "items": ["面向数据仓库实习生的可执行动作"]}}
  ],
  "sql": ""
  "caliber": ["回答口径声明", "数据限制说明"]
}}

要求：
- 不要输出虚假的具体数值。
- 不要泄露或要求用户提供密钥。
- 可以引用文件名，但不要说“根据第几个 chunk”。
- 语气专业、清晰，适合项目展示。
- 每个 section 最多 3 条 items，每条不超过 90 个中文字符。
- 不要复制长 SQL；SQL 线索只写进“SQL/口径提醒”的 items。
- sql 字段必须保持为空字符串。
""".strip()


def format_context(citations: list[dict]) -> str:
    if not citations:
        return "未检索到可用知识库片段。"

    blocks = []
    for index, item in enumerate(citations[:5], start=1):
        title = item.get("title") or "未命名片段"
        filename = item.get("filename") or "未知文件"
        topic = item.get("topic") or "general"
        content = item.get("content") or item.get("snippet") or ""
        blocks.append(
            f"[{index}] 文件：{filename}\n"
            f"标题：{title}\n"
            f"主题：{topic}\n"
            f"内容：{content[:1200]}"
        )
    return "\n\n".join(blocks)

