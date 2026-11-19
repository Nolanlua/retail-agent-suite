# 知识 Agent

## 工作流

~~~text
classify → normalize → retrieve → graph_expand → compliance_precheck
         → generate → verify → finalize
~~~

## 意图

陈列、公告、供应商、商品、制度、价格、通用。

## 检索

- OpenSearch BM25：端头、公告编号、SKU、制度名；
- Qdrant 向量：口语化问题；
- RRF 融合；
- Neo4j 关系（商品-品类-供应商）只做扩展。

## 合规

代码规则优先：

- 不承诺最低价；
- 不绕过召回；
- 不泄露内部文件/员工信息/供应商底价；
- 召回、价格、陈列以系统和负责人确认为准。

## 引用

代码按检索顺序生成 [1]..[n]；生成后校验编号范围；失败重试一次，再失败兜底。
