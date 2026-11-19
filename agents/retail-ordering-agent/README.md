# 零售智能订货 Agent

面向零食店、社区超市和连锁便利店的补货 Agent。LLM 只做意图理解和解释，预测、补货公式、MOQ、箱规、预算全部由确定性代码计算。

## 能力

- 读取零售智库公告：商品召回、端头陈列变更、供货价调整、新品；
- 公告影响由确定性规则处理，召回商品建议量强制为 0；
- 返回店长/商品专员提醒；

- 门店、SKU、覆盖天数意图解析；
- 数据中台在线特征读取；
- 7/28 天加权需求预测、趋势、促销、置信度；
- 补货公式：预测需求 + 安全库存 - 现有 - 在途；
- 箱规、MOQ、可供货量、预算、最大订货量约束；
- 供应商供货匹配；
- 人工确认 + Go 订单服务幂等下单；
- 数据脚本生成零食/日用品 SKU、销售、库存、促销、供应商报价。

## 仓库结构


~~~text
app/
  agent/            LangGraph 工作流
  domain/           预测与补货公式
  clients/          数据中台、订单服务
  api.py            suggest / confirm
  main.py           FastAPI 入口
order-service/      Go 订单服务：幂等、MySQL 事务、Outbox
data/               模拟数据、100 SKU PDF、SKU 生成
packages/common/    鉴权、配置、日志
docs/               架构、数据、运维
tests/              预测与补货测试
~~~

## 依赖

- 零售智库：https://github.com/Nolanlua/retail-knowledge-agent

- 数据/评测中台：https://github.com/Nolanlua/agent-platform
- MySQL：订单库
- 数据中台：特征服务
- OpenAI 兼容模型 API（可选，未配置时使用模板解释）

## 本地启动

~~~bash
cp .env.example .env
uv sync --all-packages
uv run python data/generate_retail.py
uv run uvicorn app.main:app --port 8012
~~~

订单服务：

~~~bash
cd order-service
go test ./...
go run ./cmd/order-service
~~~

## 说明

这是企业级参考实现，不是生产系统。供应商接口是模拟适配器，生产需要接入真实供货 API 并补充对账/补偿。