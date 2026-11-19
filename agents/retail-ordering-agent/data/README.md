# 模拟数据

## SKU

- data/sample/sku_master.csv：100 个零食店/社区超市 SKU，提交到仓库用于代码审阅；
data/sample/sku_catalog.pdf：100 SKU 商品主数据 PDF，用于演示文档解析/知识库资产；
- 品类：饮料、零食、乳品、日化、粮油、方便食品、烘焙；
- 字段：SKU、名称、品类、品牌、单位、箱规、MOQ、保质期、单价。

## 完整本地数据

~~~bash
uv run python data/generate_retail.py
~~~

生成到 data/local/：

- 8 家门店；
- 100 个 SKU；
- 120 天销售；
- 库存快照；
- 促销；
- 供应商报价。

data/local/ 不提交仓库，避免大文件；data/sample/ 提交 SKU 主数据。

## 特征

数据中台启动后：

~~~bash
uv run python scripts/seed_features.py
~~~

把门店-SKU 的补货特征写入特征服务。生产环境由 dbt/Airflow 产出，不在 Agent 仓库计算。