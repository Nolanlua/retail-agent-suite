# 中文说明：生成并审核一批连锁零售企业知识库 Wiki 页面，用于本地演示和评测。
"""Seed the retail knowledge wiki with synthetic internal documents.

Content mimics a snack retail chain working with a supply-chain partner:
seasonal end-cap plans, store SOPs, product recalls, display changes and price
notices. It is synthetic and for development only.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db import Base, SessionFactory, engine
from app.wiki.indexer import WikiIndexer
from app.wiki.models import WikiPage, WikiRevision

PAGES = [
    {
        "slug": "display-endcap-standard",
        "title": "陈列端头执行标准（2026 版）",
        "category": "display",
        "source": "门店运营中心 · 陈列规范 V3.2",
        "content": "# 陈列端头执行标准（2026 版）\n\n## 适用范围\n\n所有直营店和加盟店。端头指货架两端面向主通道的陈列位，分金码端头、银码端头和普通端头。\n\n## 基本要求\n\n- 端头高度不超过 1.6 米，不得遮挡消防通道和价签；\n- 主推商品放在视线高度 1.1 到 1.5 米；\n- 价签、POP、活动标识必须与系统价格一致；\n- 端头陈列面不少于 3 个排面，库存深度不低于 2 天销量；\n- 每两周检查一次端头动销，连续 7 天动销低于同类平均 30% 的，申请调整。\n\n## 责任\n\n店长负责执行，区域运营负责抽检，商品专员负责主题和商品清单。",
    },
    {
        "slug": "display-2026-q4-theme",
        "title": "2026 年 Q4 端头主题与商品清单",
        "category": "display",
        "source": "商品中心 · 2026-Q4 陈列计划",
        "content": "# 2026 年 Q4 端头主题与商品清单\n\n## 主题\n\nQ4 主题为“暖冬囤货季”，周期 2026-10-01 至 2026-12-31。每三个月更新一次主题，下一次更新为 2027-01-01。\n\n## 端头分配\n\n- 门店入口第一端头：坚果、炒货、礼盒；\n- 收银台端头：口香糖、巧克力、小包装零食；\n- 饮料区端头：热饮、冲泡饮品、整箱饮料；\n- 日化区端头：纸巾、洗衣液、家庭清洁组合。\n\n## 执行要求\n\n- 10 月 1 日前完成第一波陈列；\n- 11 月 15 日前完成礼盒主题切换；\n- 12 月 20 日后不再新增大件礼盒，转为清库存；\n- 所有端头商品必须有对应价签和活动标识。\n\n## 数据口径\n\n端头动销按门店-SKU-日统计，缺货日不计入动销。",
    },
    {
        "slug": "display-2027-q1-theme",
        "title": "2027 年 Q1 端头主题预告",
        "category": "display",
        "source": "商品中心 · 2027-Q1 陈列计划",
        "content": "# 2027 年 Q1 端头主题预告\n\nQ1 主题为“新春焕新”，周期 2027-01-01 至 2027-03-31。\n\n- 春节前主推礼盒、坚果、饮料组合；\n- 节后切换为轻食、早餐、日化补货；\n- 2 月底完成春季新品端头切换；\n- 旧主题物料在 2027-01-05 前撤除。\n\n本页为预告，最终商品清单以商品中心正式通知为准。",
    },
    {
        "slug": "wanyou-recall-2026-11-18",
        "title": "南京万优商品召回通知（2026-11-18）",
        "category": "notice",
        "source": "南京万优供应链 · 召回公告 WY-2026-1118",
        "content": "# 南京万优商品召回通知（2026-11-18）\n\n## 等级\n\n紧急。\n\n## 召回商品\n\n- SKU-0032 某品牌每日坚果 750g；\n- 涉及批次：2026-09-10 至 2026-09-25；\n- 召回原因：供应商自检发现个别批次密封不良，存在受潮风险。\n\n## 门店动作\n\n1. 立即下架并封存相关批次；\n2. 停止订货和促销；\n3. 在 2026-11-19 18:00 前完成门店自查并在系统登记；\n4. 已售商品由客服按公司流程处理，门店不得自行承诺赔偿；\n5. 召回完成后等待商品中心书面恢复通知。\n\n## 责任\n\n店长执行，区域运营抽检，供应链专员对接南京万优。",
    },
    {
        "slug": "wanyou-display-change-2026-11",
        "title": "南京万优陈列变更通知（2026-11）",
        "category": "notice",
        "source": "南京万优供应链 · 陈列变更 WY-2026-1105",
        "content": "# 南京万优陈列变更通知（2026-11）\n\n## 变更内容\n\n南京万优新增“暖冬饮品”主题端头，要求重点门店在 2026-11-25 前完成陈列。\n\n## 涉及门店\n\n华北、华东区域首批 40 家门店。\n\n## 执行要求\n\n- 端头位置：饮料区主通道第一端头；\n- 商品：热饮、冲泡饮品、整箱饮料；\n- 陈列面不少于 4 个；\n- 价签和活动标识使用万优提供的最新模板；\n- 12 月 31 日后恢复常规陈列。\n\n## 提醒\n\n陈列变更不影响已审核的补货计划，但店长需要在订货时考虑端头增量。",
    },
    {
        "slug": "wanyou-price-change-2026-11",
        "title": "南京万优供货价调整通知（2026-11）",
        "category": "notice",
        "source": "南京万优供应链 · 价格通知 WY-2026-1112",
        "content": "# 南京万优供货价调整通知（2026-11）\n\n自 2026-11-20 起，部分饮料和日化商品供货价调整，具体以供应商价格表为准。\n\n## 门店要求\n\n- 不得自行调整零售价；\n- 价格变更由商品中心统一下发；\n- 发现价签与系统不一致，立即反馈区域运营；\n- 不得向顾客承诺“最低价”。\n\n## 影响\n\n补货建议中的预算和毛利测算需要使用最新供货价，历史价格只用于对比。",
    },
    {
        "slug": "new-product-2026-11",
        "title": "2026 年 11 月新品上架清单",
        "category": "product",
        "source": "商品中心 · 新品通知",
        "content": "# 2026 年 11 月新品上架清单\n\n本月新品包括：\n\n- SKU-0008 低糖气泡水；\n- SKU-0017 全麦苏打饼干；\n- SKU-0026 便携湿巾；\n- SKU-0041 小包装混合坚果。\n\n## 上架要求\n\n- 新品到店后 48 小时内完成首铺；\n- 首铺陈列在对应品类主货架，不占用端头；\n- 两周内完成第一次动销复盘；\n- 新品前 30 天不参与清仓促销。",
    },
    {
        "slug": "store-replenishment-sop",
        "title": "门店补货与订货 SOP",
        "category": "operation",
        "source": "运营中心 · 门店 SOP",
        "content": "# 门店补货与订货 SOP\n\n## 订货频率\n\n标准店每周订货 2 次，社区店每周 1 次；节假日按运营通知调整。\n\n## 订货依据\n\n- 近 7 天和 28 天销量；\n- 现有库存和在途库存；\n- 端头/促销计划；\n- 供应商可供货量和交期；\n- 商品召回、陈列变更等公告。\n\n## 审批\n\n建议订货量由系统生成，店长确认；超过预算或超过最大订货量时，需要区域运营审批。\n\n## 禁止\n\n- 不得绕过系统手工下重复订单；\n- 不得对召回商品继续订货；\n- 不得自行承诺供应商价格。",
    },
    {
        "slug": "supplier-delivery-sop",
        "title": "南京万优到货与验收 SOP",
        "category": "supplier",
        "source": "供应链中心 · 供应商协同",
        "content": "# 南京万优到货与验收 SOP\n\n## 到货前\n\n- 确认采购订单和预计到货时间；\n- 检查门店收货区和冷链/常温分区；\n- 召回商品不得收货。\n\n## 验收\n\n- 核对 SKU、数量、批次、保质期；\n- 外包装破损、临期、批次不符的，拒收并登记；\n- 验收完成后 2 小时内在系统确认。\n\n## 差异\n\n数量差异 24 小时内提交差异单；质量问题拍照留证并联系供应链专员。",
    },
    {
        "slug": "promotion-execution-policy",
        "title": "促销执行与价格标识规范",
        "category": "policy",
        "source": "商品中心 · 促销管理规范",
        "content": "# 促销执行与价格标识规范\n\n- 促销价格以系统生效价格为准；\n- 价签、POP、端头标识必须一致；\n- 促销开始前 1 天完成陈列和价签更换；\n- 促销结束后 24 小时内撤除物料；\n- 不得虚构原价，不得承诺全网最低价；\n- 发现价格异常立即反馈，不得自行改价。",
    },
    {
        "slug": "internal-document-security",
        "title": "内部文件与数据安全规范",
        "category": "policy",
        "source": "信息安全管理部",
        "content": "# 内部文件与数据安全规范\n\n- 内部制度、陈列计划、供应商价格属于公司内部资料；\n- 不得外发给客户、供应商或无关人员；\n- 不得在公开群、社交平台传播；\n- 员工信息、客户信息、供应商底价按敏感数据管理；\n- 对外提供资料需要走审批；\n- 发现泄露立即报告信息安全部。",
    },
    {
        "slug": "store-endcap-audit",
        "title": "端头陈列巡检表",
        "category": "operation",
        "source": "运营中心 · 巡检模板",
        "content": "# 端头陈列巡检表\n\n## 检查项\n\n- 端头位置是否符合季度主题；\n- 商品、价签、POP 是否一致；\n- 陈列面是否不少于标准；\n- 库存深度是否满足 2 天销量；\n- 消防通道是否被遮挡；\n- 召回商品是否已下架。\n\n## 频次\n\n店长每周自检一次，区域运营每月抽检一次。",
    },
    {
        "slug": "sku-master-2026",
        "title": "商品 SKU 主数据说明（2026-11）",
        "category": "product",
        "source": "商品中心 · SKU 主数据",
        "content": "# 商品 SKU 主数据说明（2026-11）\n\n公司当前维护约 100 个 SKU，覆盖饮料、零食、乳品、日化、粮油、方便食品和烘焙。\n\n## 字段\n\nSKU 编码、商品名称、品类、品牌、单位、箱规、MOQ、保质期、单价。\n\n## 使用\n\n- 补货计算使用箱规、MOQ、保质期和单价；\n- 商品资料和价签以系统主数据为准；\n- SKU 主数据 PDF 见 data/sample/sku_catalog.pdf；\n- 新品、停售和召回由商品中心发布公告。\n\n## 注意\n\nSKU 主数据 PDF 仅为演示数据，不包含真实商品和价格。",
    },
]


async def main() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        for item in PAGES:
            exists = await session.scalar(
                select(WikiPage).where(WikiPage.tenant_id == "demo", WikiPage.slug == item["slug"])
            )
            if exists:
                continue
            page = WikiPage(
                tenant_id="demo",
                slug=item["slug"],
                title=item["title"],
                category=item["category"],
                source=item["source"],
                status="approved",
                current_version=1,
                index_status="pending",
                created_by="seed",
                updated_at=datetime.now(timezone.utc),
            )
            session.add(page)
            await session.flush()
            revision = WikiRevision(
                page_id=page.id,
                version=1,
                title=item["title"],
                content_md=item["content"],
                status="approved",
                reviewer="seed-reviewer",
                review_note="seed data",
                created_by="seed",
            )
            session.add(revision)
            await session.commit()
            ok = await WikiIndexer().index(page, revision)
            page.index_status = "indexed" if ok else "failed"
            await session.commit()
            print("seeded", item["slug"], page.index_status)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())