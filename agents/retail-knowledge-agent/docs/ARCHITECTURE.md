# 架构

## 分层

~~~text
门店/运营/商品/供应链员工
  → 零售智库 Agent（FastAPI + LangGraph）
  → Wiki（PostgreSQL：页面、版本、审核）
  → 审核通过 → Qdrant + OpenSearch
  → 回答 + 引用 + 合规提示
~~~

## 与订货 Agent 的关系

零售智库是“制度与公告”的知识源；订货 Agent 是“销售、库存、补货、下单”的执行 Agent。

- 智库提供公告：召回、陈列变更、价格调整、新品；
- 订货 Agent 读取公告，调整补货建议并生成店长提醒；
- 两者共享数据中台和评测中台，但代码、数据库、发布独立。

## 模块

- app/wiki：页面、修订、审核、索引、公告；
- app/agent：意图、术语、检索、合规、生成、引用；
- app/retrieval：BM25、向量、RRF、图谱、索引写入；
- app/safety：合规规则；
- packages/common：鉴权、配置、日志、错误契约。

## 外部依赖

PostgreSQL（Wiki）、Qdrant（向量）、OpenSearch（BM25）、Neo4j（关系）、模型 API。
