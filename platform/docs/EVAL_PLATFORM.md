# 评测中台

## 概念

| 概念 | 说明 |
|---|---|
| Dataset | 不可变评测集版本 |
| Case | 单条问题、期望、来源、安全期望 |
| Run | 一次评测任务，指向 Dataset |
| Result | 单条输出、分数、耗时、是否通过 |

## 指标

### RAG

- citation_accuracy：引用命中期望来源；
- refusal_correctness：该拒答时是否拒答；
- safety_pass：禁用断言；
- faithfulness：Judge 评估回答是否被上下文支持。

### 结构化任务

- formula_compliance：结果与期望值/容差；
- tool_trace_accuracy：必要工具是否调用；
- safety_pass：解释是否包含违规承诺。

## 回归

- 数据集版本不可变；
- 每次运行记录 Agent 版本、模型版本、数据集版本；
- 安全性是硬门禁；
- 通过率低于基线阻断发布。

## Judge

Judge 不是标准答案：

- 必须抽检；
- Prompt 版本化；
- 记录模型、温度、时间；
- 高风险领域保留人工复核。
