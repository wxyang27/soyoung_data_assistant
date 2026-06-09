def build_gross_margin_diagnosis(question: str) -> dict:
    return {
        "summary": "已识别为毛利率诊断问题。当前 MVP 使用固定业务框架演示，后续会接入 MaxCompute 查询和 Doris RAG 检索。",
        "sections": [
            {
                "title": "一、大盘总览",
                "items": [
                    "核心指标：品项毛利率 = SUM(gross_margin_amt) / SUM(NULLIF(exe_income, 0))。",
                    "目标参考：整体毛利率目标 48%，绿标品建议 60%-70%，常规品建议不低于 50%。",
                    "诊断顺序：先判断大盘是否达标，再看三类品结构、成本侧和补贴侧。",
                ],
            },
            {
                "title": "二、收入侧：三类品结构",
                "items": [
                    "大师团：高客单、高毛利，但收入占比通常较低，重点关注标签维护是否正确。",
                    "绿标品：规模与利润双驱动，若收入占比和毛利率同步提升，说明结构优化有效。",
                    "常规品：体量最大但毛利率长期偏低，是毛利率承压时的重点排查对象。",
                ],
            },
            {
                "title": "三、成本侧：耗材 + 手工费",
                "items": [
                    "耗材口径：当前数仓毛利率只计入高值耗材，consumable_type IN (1,3)。",
                    "手工费口径：manual_fee 为医护手工费合计，当前无法拆分医生和护士。",
                    "异常信号：0 元单中出现高值耗材，会直接拖累毛利。",
                ],
            },
            {
                "title": "四、补贴侧：让利风险",
                "items": [
                    "促销补贴、门店改价、用户运营券和历史价差都可能侵蚀毛利。",
                    "常规品用户运营率超过 15% 或门店改价超过 5%，应优先预警。",
                    "L0/L1 用户补贴效率低，需关注灌券、纯薅和 0 元成本问题。",
                ],
            },
            {
                "title": "五、建议下钻方向",
                "items": [
                    "按品项：定位低毛利、高让利、高耗材的 TopN 品项。",
                    "按门店：排查毛利率极高或为负的异常门店。",
                    "按会员等级：重点查看 L0/L1 发券、用券、核销、纯薅漏斗。",
                ],
            },
        ],
        "sql": """SELECT
    SUBSTR(stat_date, 1, 7) AS month,
    CASE
        WHEN revenue_category = '大师团' OR standard_name LIKE '大师团-%' THEN '大师团'
        WHEN green_label = '是' THEN '绿标品'
        ELSE '常规品'
    END AS product_group,
    ROUND(SUM(exe_income), 2) AS exe_income,
    ROUND(SUM(ware_cost), 2) AS ware_cost,
    ROUND(SUM(manual_fee), 2) AS manual_fee,
    ROUND(SUM(gross_margin_amt) / NULLIF(SUM(exe_income), 0), 4) AS gross_margin_rate
FROM soyoung_dw.dws_opt_qy_gross_margin_stats_all_d
WHERE dp = DATE_SUB(CURRENT_DATE(), 1)
  AND stat_date >= '2026-05-01'
  AND stat_date <= '2026-05-31'
GROUP BY month, product_group
ORDER BY month, product_group
LIMIT 100;""",
        "caliber": [
            "数据源：soyoung_dw.dws_opt_qy_gross_margin_stats_all_d。",
            "毛利率必须先 SUM 聚合再相除，不能逐行计算后平均。",
            "三类品分类优先级：大师团 > 绿标品 > 常规品。",
            "耗材口径：只含高值耗材，数仓口径可能比财务口径高 1-4pp。",
        ],
    }
