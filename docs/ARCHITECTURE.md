# 总体架构

## 组件

~~~text
员工/店长
  ├─ 零售智库 Agent（Wiki + 检索 + 引用 + 公告）
  └─ 智能订货 Agent（特征 + 预测 + 补货 + 公告 + 订单）
       ↓
共享数据中台 + 评测中台
       ↓
PostgreSQL / Qdrant / OpenSearch / Neo4j / MySQL
~~~

## 仓库分层

| 目录 | 职责 |
|---|---|
| platform | 数据目录、质量、特征、血缘、评测集、任务、指标 |
| agents/retail-knowledge-agent | Wiki 审核、检索、引用、合规、公告 |
| agents/retail-ordering-agent | 预测、补货、公告影响、订单服务 |

## 知识链路

~~~text
内部文件/公告 → Wiki 编辑 → 送审 → 审核 → approved
             → Qdrant/OpenSearch → Agent 检索 → 引用回答
~~~

未审核内容不进入索引。

## 订货链路

~~~text
销售/库存/促销 → 数据中台特征 → 预测 → 补货公式
                                  ↓
                     公告（召回/陈列/价格/新品）
                                  ↓
                        提醒 + 人工确认 + 幂等下单
~~~

## 边界

- LLM 不计算补货、不写订单；
- 召回由代码硬阻断；
- 价格/陈列以系统公告和负责人确认为准；
- 平台不保存业务答案、订单、知识正文。
