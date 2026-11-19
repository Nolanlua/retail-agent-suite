# 连锁零售 Agent 套件

面向连锁零食零售企业的知识库 Agent 与智能订货 Agent。两个 Agent 共享数据中台和评测中台，代码按独立服务组织。

## 项目结构

~~~text
retail-agent-suite/
  platform/                       数据中台 + 评测中台
  agents/retail-knowledge-agent/  零售智库：Wiki 审核、检索、引用、公告
  agents/retail-ordering-agent/   智能订货：预测、补货、公告、Go 订单服务
  docs/                           架构、项目解析、接口、运维、安全
  .github/                        CI
~~~

## 两个 Agent

### 零售智库

- 内部制度、陈列端头、季度主题、SOP、商品和供应商公告；
- Wiki 编辑、送审、审核、版本；
- 只有 approved 页面进入 Qdrant/OpenSearch；
- 回答带引用，合规规则拦截价格承诺、召回绕过和内部资料外发；
- 通过 internal/notices 给订货 Agent 提供公告。

### 智能订货

- 门店-SKU 特征：销售、库存、箱规、MOQ、价格；
- 7/28 天预测和确定性补货公式；
- 读取公告：召回、陈列变更、价格调整、新品；
- 召回命中 SKU 强制建议量 0；
- 店长确认后走 Go 订单服务，幂等键 + MySQL 唯一索引。

## 共享中台

- 数据中台：目录、质量、特征、血缘；
- 评测中台：数据集版本、评测任务、引用/合规/补货指标；
- 两个 Agent 只通过 HTTP 访问平台，不共享业务表。

## 本地打开

推荐用 PyCharm 或 VS Code 打开根目录，再分别打开三个 Python 子项目：

~~~text
platform/                       uv sync --all-packages
agents/retail-knowledge-agent/  uv sync --all-packages
agents/retail-ordering-agent/   uv sync --all-packages
~~~

每个子项目有自己的 README、pyproject 和 docker-compose。

## 文档

- docs/PROJECT_OVERVIEW.md：项目解析（业务、架构、接口、代码区域）
- docs/ARCHITECTURE.md：三仓库总体架构
- docs/API.md：全部接口
- docs/OPERATIONS.md：运维
- docs/SECURITY.md：安全与合规

## 数据

- agents/retail-ordering-agent/data/sample/sku_master.csv：100 个模拟 SKU；
- agents/retail-ordering-agent/data/sample/sku_catalog.pdf：100 SKU PDF；
- 模拟销售/库存数据由脚本生成，不提交大文件。

## 说明

企业级参考实现，不是生产系统。模型 API、PostgreSQL、Qdrant、OpenSearch、MySQL 需要真实环境；价格、召回、陈列以公司系统和负责人最终确认为准。
