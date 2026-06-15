# Knowledge

这里存放业务知识库资料。建议分三层管理：

```text
knowledge/
  raw/        # 原始资料，不提交 GitHub
  curated/    # 脱敏、整理后的 Markdown，可选择提交
  eval/       # 检索评估问题集，可提交
```

## raw/

`raw/` 用于放原始业务文档，例如 Word、Excel、Markdown、SQL、PDF、HTML。

注意：`raw/` 已加入 `.gitignore`，默认不提交 GitHub，避免泄露内部业务资料。

## curated/

`curated/` 用于放人工整理、脱敏后的 Markdown 知识卡片。它适合补充 RAG 检索中发现的缺口。

## eval/

`eval/` 用于放评估问题集，例如：

```text
eval/eval_questions.yaml
```

后续每次调整 chunk 切分或向量检索，都可以用这些问题检查召回效果。

## 入库脚本

体检 raw 文档：

```powershell
python scripts/audit_knowledge.py
```

将 raw 文档切 chunk 并写入本地 SQLite：

```powershell
python scripts/ingest_knowledge.py
```

如果也要导入 curated 文档：

```powershell
python scripts/ingest_knowledge.py --include-curated
```

默认写入：

```text
instance/soyoung_data_assistant.db
```

## 与 soyoung-skills-hub 的关系

本项目可从 `soyoung-skills-hub` 引用或复制脱敏后的业务知识。

推荐方式：

```powershell
git submodule add https://github.com/wxyang27/soyoung-skills-hub.git knowledge/soyoung-skills-hub
```

如果仓库公开展示，请先脱敏内部表名、业务文档和样例数据。
