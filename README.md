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

## 第一阶段 MVP

当前已跑通“应用骨架 + 问答交互 + 毛利率诊断展示形态”：

- Flask app factory 和 `/health` 健康检查。
- `/api/chat` 问答接口。
- 规则意图识别：毛利率诊断、指标口径、自然语言取数、表字段查询。
- 毛利率诊断 mock agent：按大盘、三类品、成本侧、补贴侧、下钻方向输出。
- 聊天页：示例问题、答案卡片、SQL 折叠区、口径声明。

### 本地运行

```powershell
cd C:\Users\Soyoung\Desktop\Cdemo\soyoung_data_assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

健康检查：

```text
http://127.0.0.1:5000/health
```

### 当前限制

第一阶段默认 `MOCK_MODE=true`，暂不连接 Doris、LangChain、MaxCompute 和 MySQL。后续会把 mock answer 逐步替换为真实 RAG、SQL 生成、只读查询和会话持久化。
