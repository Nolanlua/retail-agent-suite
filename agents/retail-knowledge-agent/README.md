# 零售智库 · 连锁零售企业知识库 Wiki Agent

面向连锁零食零售企业（参考“好想来 + 南京万优”的零供协同模式）的企业级知识库。知识先进入 Wiki 编辑、审核和版本化，审核通过后才进入检索索引。

## 业务场景

- 门店店长：查陈列端头标准、季度主题、补货 SOP、召回/陈列/价格公告；
- 区域运营：查巡检标准、促销执行、门店执行差异；
- 商品/供应链专员：查新品、供应商到货、商品召回、价格调整；
- 新员工：按主题学习内部制度，不靠群聊和共享盘。

## 能力

- Wiki 页面创建、修订、送审、审核、历史版本；
- 只有 approved 页面进入 Qdrant/OpenSearch 索引；
- BM25 + 向量混合召回、RRF、知识图谱扩展（商品-品类-供应商关系）；
- 回答必须带引用，引用编号由代码生成并校验；
- 合规预检：价格承诺、召回绕过、内部文件外发、供应商底价；
- 公告接口：向订货 Agent 提供召回、陈列变更、价格调整等通知；
- 评测对接：引用准确率、拒答、合规性、忠实度。

## 仓库结构

~~~text
app/
  agent/            LangGraph：分类、归一、检索、合规、生成、校验
  retrieval/        混合检索、引用、索引写入
  safety/           合规规则
  wiki/             页面、版本、审核、索引
  api.py            Chat、Search、Notices
  main.py           FastAPI 入口
packages/common/    鉴权、配置、日志、错误契约
scripts/seed_wiki.py 初始化零售知识 Wiki
docs/               架构、Wiki、Agent、运维、安全
tests/              合规与引用测试
~~~

## 依赖

- 数据/评测中台：https://github.com/Nolanlua/agent-platform
- PostgreSQL：Wiki 页面与版本
- Qdrant / OpenSearch / Neo4j：检索与关系
- OpenAI 兼容模型 API

## 本地启动

~~~bash
cp .env.example .env
uv sync --all-packages
uv run uvicorn app.main:app --port 8011
uv run python scripts/seed_wiki.py
~~~

## API

~~~http
GET  /healthz
POST /v1/chat
POST /v1/knowledge/search
GET  /v1/notices
GET  /v1/wiki/pages
POST /v1/wiki/pages
POST /v1/wiki/pages/{slug}/submit
POST /v1/wiki/pages/{slug}/approve
GET  /v1/wiki/pages/{slug}/revisions
~~~

## 说明

这是企业级参考实现，不是生产系统。知识内容为模拟数据，价格、召回、陈列等执行动作必须由公司系统和负责人最终确认。
