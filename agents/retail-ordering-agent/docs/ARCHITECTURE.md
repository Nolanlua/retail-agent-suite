# 架构

## 服务

~~~text
用户/店长
  → 零售 Agent（Python/FastAPI/LangGraph）
  → 数据中台（特征）
  → 订单服务（Go）
  → MySQL（订单、幂等、Outbox）
  → 供应商适配器
~~~

## 边界

- LLM 只做意图理解和解释；
- 预测、补货、MOQ、箱规、预算全部由代码计算；
- Agent 不直接写订单表；
- 订单服务负责事务、幂等、外部接口；
- 数据中台负责特征口径和新鲜度。

## 工作流

~~~text
parse_intent → load_features → load_notices → forecast → supply → calculate → explain
~~~

## 公告

零售智库提供 approved 公告；订货 Agent 读取公告：

- 召回：命中 SKU 强制建议 0；
- 陈列变更：生成店长提醒；
- 价格调整：生成商品专员提醒；
- 新品：生成首铺提醒。

公告不能直接修改补货公式，只有召回是硬阻断。

## 幂等

1. 客户端带 Idempotency-Key；
2. 订单服务先查幂等表；
3. 未命中才调用供应商；
4. 本地事务写订单、明细、幂等响应、Outbox；
5. 唯一索引冲突时回查并返回已有结果。

## 已知边界

供应商成功、本地失败存在不一致；生产用 Outbox 补偿 Worker、对账和人工处理队列。