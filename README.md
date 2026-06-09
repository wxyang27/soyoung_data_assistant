# soyoung_data_assistant

连锁医美数据智能运营助手。目标是基于 Doris + LangChain + Prompt 工程 + Python + Flask + MySQL，结合新氧连锁业务指标口径、数仓表结构和 MaxCompute 只读查询能力，完成一个可展示的实习项目。

## 项目定位

- 自然语言问数：收入、核销、新老客、渠道、品项、门店等高频问题。
- 标准口径 SQL：结合指标字典和 NL2SQL 模板生成可审计 SQL。
- 经营诊断：按连锁业务七步分析法输出结果解释和动作建议。
- 知识检索：使用 Doris ANN 存储业务知识、表结构、SQL 示例和 Prompt 片段。

## 推荐仓库关系

本仓库是应用工程仓库；业务知识源建议来自兄弟仓库：

- https://github.com/wxyang27/soyoung-skills-hub

开发时可将 `soyoung-skills-hub` 作为 submodule 或知识快照放入 `knowledge/`，避免应用代码和技能库混在一起。

## 目录结构

```text
app/          Flask 后端应用
scripts/      离线构建、元数据同步、向量入库脚本
sql/          MySQL / Doris 建表 SQL
templates/    Flask 页面模板
static/       前端静态资源
knowledge/    业务知识库引用或脱敏快照
docs/         架构、演示案例、开发记录
```

## 安全约定

- 不提交真实 MaxCompute、Doris、MySQL、LLM API 密钥。
- 不提交敏感用户明细数据。
- 公开展示版优先使用脱敏样例数据和脱敏知识片段。
