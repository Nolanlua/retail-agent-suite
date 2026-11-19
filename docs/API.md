# 接口总览

## 数据中台

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | /healthz | 存活 |
| GET | /readyz | 数据库就绪 |
| POST | /v1/assets | 注册资产 |
| GET | /v1/assets | 查询资产 |
| POST | /v1/quality/run | 质量检查 |
| GET | /v1/quality/runs/{id} | 质量报告 |
| POST | /v1/features/query | 特征查询 |
| POST | /v1/features/snapshot | 特征写入 |
| GET | /v1/lineage/{name} | 血缘 |
| GET | /v1/features/health | 特征健康 |

## 评测中台

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | /healthz | 存活 |
| POST | /v1/datasets | 创建数据集 |
| GET | /v1/datasets | 查询数据集 |
| POST | /v1/runs | 触发评测 |
| GET | /v1/runs/{id} | 查询任务 |
| GET | /v1/runs/{id}/results | 查询单条结果 |

## 零售智库

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | /healthz | 存活 |
| POST | /v1/chat | 知识问答 |
| POST | /v1/knowledge/search | 只检索 |
| GET | /v1/notices | 公告（用户） |
| GET | /internal/notices | 公告（订货 Agent） |
| GET/POST | /v1/wiki/pages | 页面列表/创建 |
| GET/PUT | /v1/wiki/pages/{slug} | 详情/修订 |
| POST | /v1/wiki/pages/{slug}/submit | 送审 |
| POST | /v1/wiki/pages/{slug}/approve | 审核通过 |
| POST | /v1/wiki/pages/{slug}/reject | 驳回 |
| GET | /v1/wiki/pages/{slug}/revisions | 历史版本 |
| GET | /v1/wiki/search | 页面搜索 |

## 智能订货

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | /healthz | 存活 |
| POST | /v1/ordering/suggest | 补货建议、公告提醒 |
| POST | /v1/ordering/confirm | 人工确认下单 |

## Go 订单服务

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | /healthz | 存活 |
| GET | /internal/suppliers/offers | 供应商供货 |
| POST | /internal/orders | 创建订单（Idempotency-Key） |
