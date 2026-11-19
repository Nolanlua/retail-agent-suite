# Order Service

Go 订单服务，负责：

- 供应商可供货查询；
- 幂等键校验；
- 供应商下单；
- MySQL 事务写订单、明细、幂等响应和 Outbox 事件；
- 健康检查和优雅关闭。

## 接口

- GET /healthz
- GET /internal/suppliers/offers?store_id=S01&sku=SKU-0001
- POST /internal/orders

下单必须带 Idempotency-Key。重复请求返回第一次的 order_id，并标记 idempotent=true。

## 本地运行

~~~bash
go mod tidy
go run ./cmd/order-service
~~~

## 已知边界

供应商成功、本地落库失败时，当前实现会返回错误但上游可能已经下单。生产应通过 Outbox + 补偿任务或供应商对账解决；本项目已经写入 outbox 事件，补偿 worker 是下一阶段工作。
