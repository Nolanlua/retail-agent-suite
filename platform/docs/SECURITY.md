# 安全

## 身份

- JWT 由统一身份提供方签发；
- token 包含 subject、tenant_id、roles；
- 网关校验后注入 X-Tenant-Id；
- 服务比较 header 和 token 的 tenant。

## 权限

- 平台管理员：跨租户运维，不读业务正文；
- 数据管理员：目录、质量规则；
- 业务用户：只访问授权租户/门店；
- 内部服务：服务令牌，只能调内部接口。

## 数据

- 按 public/internal/confidential 分级；
- 敏感字段脱敏；
- 日志不打印 token、Authorization、业务正文；
- 原始数据下载走审批和审计。

## 审计

记录谁在什么时间调用了哪个接口、操作了哪个资产、触发了哪次评测。
