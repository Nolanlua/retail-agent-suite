# 安全

## 身份

JWT 包含 subject、tenant_id、roles。Wiki 编辑与审核分离：

- knowledge-editor：编辑；
- knowledge-reviewer：审核；
- platform-admin：运维兜底。

## 数据

- 页面按 tenant 隔离；
- 未审核内容不进入索引；
- 内部文件、供应商价格、员工信息属于敏感数据；
- 日志不打印 token 和完整敏感内容；
- 导出和批量下载需审批。

## 合规

- 不承诺最低价；
- 不绕过商品召回；
- 不泄露内部文件/供应商底价；
- 召回、价格、陈列以系统和负责人最终确认为准。
