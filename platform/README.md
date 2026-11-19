# Agent Platform · 企业级数据与评测中台

为多个业务 Agent 提供统一的数据治理、特征服务、血缘、评测集、评测任务、指标和回归报告。平台本身不包含具体业务 Agent，也不保存业务答案。

## 服务

| 服务 | 目录 | 端口 |
|---|---|---|
| 数据中台 | platforms/data-platform | 8001 |
| 评测中台 | platforms/eval-platform | 8002 |

## 数据中台

- 数据资产目录；
- 质量规则与质量任务；
- 在线特征快照；
- 数据血缘；
- PostgreSQL 元数据。

## 评测中台

- 版本化评测集；
- 评测任务与并发执行；
- 确定性指标 + LLM Judge；
- 回归报告与通过率；
- 结果可追溯到数据集版本。

## 架构

~~~text
业务 Agent
  → 数据中台：资产、质量、特征、血缘
  → 评测中台：数据集、任务、指标、报告
  → PostgreSQL / Redis / 对象存储
~~~

## 本地启动

~~~bash
cp .env.example .env
uv sync --all-packages
docker compose -f deploy/docker-compose.yml up -d postgres redis
cd platforms/data-platform && uv run uvicorn app.main:app --port 8001
cd platforms/eval-platform && uv run uvicorn app.main:app --port 8002
~~~

## API

~~~http
GET  /healthz
POST /v1/assets
GET  /v1/assets
POST /v1/quality/run
GET  /v1/quality/runs/{run_id}
POST /v1/features/query
POST /v1/features/snapshot
GET  /v1/lineage/{asset_name}

POST /v1/datasets
GET  /v1/datasets
POST /v1/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/results
~~~

## 设计原则

1. 平台不直接读写业务订单；
2. 业务域按 tenant_id 和 domain 隔离；
3. 质量失败阻断发布；
4. 评测集不可变，任务指向版本；
5. 安全性是硬门禁，不取平均分；
6. 所有接口有统一错误契约和 request id。

## 参考 Agent

- 岐黄智库：https://github.com/Nolanlua/qihuang-tcm-agent
- 零售订货：https://github.com/Nolanlua/retail-ordering-agent-enterprise

## 文档

- docs/ARCHITECTURE.md
- docs/DATA_PLATFORM.md
- docs/EVAL_PLATFORM.md
- docs/OPERATIONS.md
- docs/SECURITY.md