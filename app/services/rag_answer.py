def build_rag_sections(question: str, citations: list[dict]) -> dict:
    """Build deterministic RAG-style answer parts from retrieved chunks."""
    if not citations:
        return {
            "sections": [
                {
                    "title": "知识库检索结果",
                    "items": [
                        "本次问题暂未命中本地知识库内容，回答将退回到内置业务框架。",
                        "建议补充相关 Markdown 业务文档，或检查问题是否包含关键业务词。",
                    ],
                }
            ],
            "caliber": ["本次未使用知识库引用。"],
        }

    top_chunks = citations[:3]
    evidence_items = []
    for index, chunk in enumerate(top_chunks, start=1):
        title = chunk.get("title") or "未命名片段"
        filename = chunk.get("filename") or "未知文件"
        snippet = chunk.get("snippet") or "该片段暂无摘要。"
        evidence_items.append(f"{index}. {title}（{filename}）：{snippet}")

    action_items = infer_next_actions(question, citations)

    return {
        "sections": [
            {
                "title": "知识库依据",
                "items": evidence_items,
            },
            {
                "title": "建议下钻方向",
                "items": action_items,
            },
        ],
        "caliber": [
            "本回答已结合本地 SQLite 知识库 TopK 检索结果生成。",
            "当前阶段使用关键词检索与规则增强，后续可替换为向量检索或混合检索。",
        ],
    }


def infer_next_actions(question: str, citations: list[dict]) -> list[str]:
    text = question.lower()
    topics = {chunk.get("topic") for chunk in citations}
    filenames = " ".join(chunk.get("filename", "") for chunk in citations)

    if "l0" in text or "灌券" in question or "纯薅" in question:
        return [
            "先按发券时会员等级拆发券、用券、核销、核销收入和纯薅率漏斗。",
            "重点检查 L0/L1 是否存在高发券、低支付、高 0 元单成本的补贴黑洞。",
            "把补贴率、0 元成本和核销收入放在同一张表里看，避免只看券量。",
        ]

    if "0元单" in question or "0 元单" in question:
        return [
            "优先拆 0 元单的手工费和耗材成本，判断是真成本还是口径异常。",
            "按会员等级、品项和门店定位成本集中的 TopN 对象。",
            "与发券漏斗联动查看，判断 0 元单是否来自低等级用户薅券。",
        ]

    if "毛利" in question:
        return [
            "先看整体毛利率是否达标，再拆大师团、绿标品、常规品三类结构。",
            "对低毛利品项继续拆收入、耗材、手工费、让利补贴四个因素。",
            "如果命中 SQL 文档，可优先复用对应 SQL 模板做月度或会员等级下钻。",
        ]

    if "表" in question or "字段" in question or "sql" in text or "怎么查" in question:
        return [
            "先确认指标口径，再确认源表、日期分区、有效订单过滤条件。",
            "优先复用知识库中的 SQL 示例，避免手写口径遗漏。",
            "如果后续接入 MaxCompute/Doris，只允许执行 SELECT 类只读查询。",
        ]

    if "metric_dictionary" in topics or "指标" in filenames:
        return [
            "先查指标字典中的原子指标，再看衍生指标是否有额外过滤条件。",
            "把指标定义、计算公式、源表字段和业务解释一起返回给用户。",
            "遇到经营复盘口径时，优先引用经管中心沉淀文档。",
        ]

    return [
        "先阅读 Top1-Top3 引用来源，确认是否命中正确业务主题。",
        "如果答案不够精确，可以补充时间范围、品类、会员等级或门店维度。",
        "后续可把本问题沉淀进 eval_questions.yaml，用作检索质量回归测试。",
    ]
