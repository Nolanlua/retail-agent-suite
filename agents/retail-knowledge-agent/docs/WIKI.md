# Wiki 设计

## 页面与版本

- WikiPage：稳定页面身份，slug、标题、分类、来源、状态；
- WikiRevision：每次编辑的不可变版本，包含 Markdown 正文、审核人和审核意见。

状态：

~~~text
draft → pending → approved
                 ↘ rejected
~~~

## 分类

- display：陈列端头标准、季度主题；
- operation：门店 SOP、巡检；
- notice：召回、陈列变更、价格调整等公告；
- product：新品、商品资料；
- supplier：供应商到货、验收；
- policy：价格、促销、内部资料安全。

## 审核与索引

1. 编辑创建草稿；
2. 送审；
3. 审核通过；
4. 写入 Qdrant/OpenSearch；
5. 索引失败标记 failed，不丢审核结果；
6. 运维可以重建索引。

未审核页面不会进入 Agent 上下文。这是和“文档直接入库”最大的区别。

## 公告接口

~~~http
GET /v1/notices
~~~

返回 approved 的 notice 页面，供订货 Agent 读取召回、陈列变更和价格通知。

## 角色

- knowledge-editor：创建/修改草稿；
- knowledge-reviewer：审核通过/驳回；
- platform-admin：平台运维兜底。
