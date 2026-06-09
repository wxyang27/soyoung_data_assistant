from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    label: str
    confidence: float


INTENT_RULES = [
    (
        "gross_margin_diagnosis",
        "毛利率诊断",
        ["毛利率", "毛利", "补贴", "让利", "耗材", "手工费", "0元", "0 元", "灌券", "绿标品", "复盘", "诊断"],
    ),
    (
        "metric_definition",
        "指标口径解释",
        ["怎么算", "口径", "定义", "公式", "区别", "是什么"],
    ),
    (
        "metadata_lookup",
        "表字段查询",
        ["字段", "表", "哪张表", "数据源", "关联键", "schema"],
    ),
    (
        "nl2sql_query",
        "自然语言取数",
        ["多少", "查询", "查一下", "昨天", "近", "上月", "本月", "收入", "GMV", "客单价"],
    ),
]


def recognize_intent(question: str) -> Intent:
    normalized = question.lower()

    for name, label, keywords in INTENT_RULES:
        hits = sum(1 for keyword in keywords if keyword.lower() in normalized)
        if hits:
            confidence = min(0.65 + hits * 0.1, 0.95)
            return Intent(name=name, label=label, confidence=confidence)

    return Intent(name="general_business_qa", label="连锁业务问答", confidence=0.55)
