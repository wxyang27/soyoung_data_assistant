# 架构草图

## 在线链路

用户问题 -> 意图识别 -> RAG 检索 Doris 知识向量 -> 口径卡片 -> SQL 生成与安全校验 -> MaxCompute 只读查询 -> 结果解释 / 经营诊断 -> 前端展示

## 离线链路

soyoung-skills-hub 业务知识 -> 文档切分 -> Embedding -> Doris ANN 向量表
MaxCompute 表结构 -> 元数据同步 -> MySQL / Doris 元数据表
