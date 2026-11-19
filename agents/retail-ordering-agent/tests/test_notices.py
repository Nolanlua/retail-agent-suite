from app.domain.notices import apply_notices


def test_recall_blocks_sku() -> None:
    notices = [
        {
            "slug": "recall",
            "title": "商品召回通知",
            "content_md": "召回 SKU-0032 每日坚果",
            "source": "南京万优",
        }
    ]
    impact = apply_notices("SKU-0032", notices)
    assert "SKU-0032" in impact.blocked_skus
    assert any(item["type"] == "recall" for item in impact.reminders)


def test_display_change_creates_reminder_only() -> None:
    notices = [
        {"slug": "display", "title": "端头陈列变更通知", "content_md": "调整饮料端头", "source": "南京万优"}
    ]
    impact = apply_notices("SKU-0001", notices)
    assert not impact.blocked_skus
    assert impact.reminders[0]["type"] == "display_change"
