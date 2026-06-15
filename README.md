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
- 本地 SQLite：自动初始化用户、会话、聊天历史等应用表。
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

初始化 SQLite：

```powershell
python scripts/init_sqlite.py
```

默认数据库文件：

```text
instance/soyoung_data_assistant.db
```

知识库体检：

```powershell
python scripts/audit_knowledge.py
```

知识库入库：

```powershell
python scripts/ingest_knowledge.py
```

知识库检索接口：

```text
http://127.0.0.1:5000/api/retrieve?q=品项毛利率怎么算
```

知识库增强问答：

```powershell
python run.py
```

在页面输入业务问题后，`/api/chat` 会完成：

- 规则意图识别。
- SQLite 知识库 TopK 检索。
- 固定业务框架回答。
- 追加“知识库依据”和“建议下钻方向”。
- 返回引用来源，前端展示片段标题、文件名、topic、score 和摘要。

检索效果评估：

```powershell
python scripts/evaluate_retrieval.py
```

LLM RAG 问答配置：

```env
MOCK_MODE=false
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=你的新 API Key
LLM_MODEL=deepseek-v4-pro
```

开启 LLM 前先安装依赖：

```powershell
pip install -r requirements.txt
```

如果没有配置 `LLM_API_KEY`，或 LLM 调用失败，系统会自动回退到当前 mock 回答，保证演示可用。

命令行测试 LLM RAG：

```powershell
python scripts/test_llm_rag.py "L0灌券为什么会拖累毛利？"
```

成功走通 LLM 时，输出中会看到：

```text
llm_mode=True
llm=deepseek / deepseek-v4-pro
```

### 当前限制

第一阶段默认 `MOCK_MODE=true`，暂不连接 Doris、LangChain、MaxCompute 和 MySQL。后续会把 mock answer 逐步替换为真实 RAG、SQL 生成、只读查询和会话持久化。


