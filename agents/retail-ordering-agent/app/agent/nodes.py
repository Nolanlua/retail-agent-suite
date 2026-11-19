# 中文说明：零售订货节点：门店/SKU 解析、特征读取、预测、供货匹配、补货计算和解释。
"""Nodes for the retail ordering graph."""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

import httpx

from app.agent.prompts import EXPLAIN_SYSTEM_PROMPT
from app.agent.state import OrderingState
from app.clients.data_platform import DataPlatformClient
from app.clients.knowledge_agent import KnowledgeAgentClient
from app.clients.order_service import OrderServiceClient
from app.config import settings
from app.domain.forecast import DemandForecaster
from app.domain.notices import apply_notices
from app.domain.replenishment import ReplenishmentCalculator, ReplenishmentInput


class OrderingNodes:
    def __init__(self) -> None:
        self._data = DataPlatformClient()
        self._orders = OrderServiceClient()
        self._knowledge = KnowledgeAgentClient()
        self._forecaster = DemandForecaster()
        self._calculator = ReplenishmentCalculator()

    async def parse_intent(self, state: OrderingState) -> dict[str, Any]:
        question = state.get("question", "")
        store_id = state.get("store_id") or self._first(re.findall(r"\bS\d{2}\b", question))
        sku = state.get("sku") or self._first(re.findall(r"SKU-\d{4}", question))
        coverage = int(state.get("coverage_days") or settings.default_coverage_days)
        target = date.today() + timedelta(days=7)
        error = ""
        if not store_id:
            error = "缺少门店编号，请在问题或参数中提供 S01 这类门店号"
        elif not sku:
            error = "缺少 SKU，请在问题或参数中提供 SKU-0001 这类商品编码"
        return {
            "store_id": store_id or "",
            "sku": sku or "",
            "coverage_days": coverage,
            "target_date": target.isoformat(),
            "error": error,
            "trace": {**state.get("trace", {}), "intent": {"store_id": store_id, "sku": sku}},
        }

    async def load_features(self, state: OrderingState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        features = await self._data.get_replenishment_features(
            tenant_id=state.get("tenant_id", ""),
            store_id=state["store_id"],
            sku=state["sku"],
            business_date=date.fromisoformat(state["target_date"]),
        )
        if features is None:
            return {"error": "未找到该门店-SKU 的可用特征，可能数据未同步或已过期"}
        return {"features": features, "trace": {**state.get("trace", {}), "feature_version": "feature_replenishment_input"}}

    async def load_notices(self, state: OrderingState) -> dict[str, Any]:
        notices = await self._knowledge.get_notices(state.get("tenant_id", ""))
        return {
            "notices": notices,
            "reminders": [],
            "trace": {**state.get("trace", {}), "notices": len(notices)},
        }
    async def forecast(self, state: OrderingState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        features = state.get("features", {})
        result = self._forecaster.forecast(
            features,
            target_date=date.fromisoformat(state["target_date"]),
            promo_lift=float(features.get("promo_lift", 0.0) or 0.0),
        )
        return {
            "forecast": {
                "daily_qty": result.daily_qty,
                "baseline": result.baseline,
                "trend_factor": result.trend_factor,
                "promo_factor": result.promo_factor,
                "confidence": result.confidence,
                "note": result.sample_note,
            },
            "trace": {**state.get("trace", {}), "forecast": "weighted_baseline"},
        }

    async def supply(self, state: OrderingState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        offers = await self._orders.get_offers(state["tenant_id"], state["store_id"], state["sku"])
        return {
            "offers": offers,
            "selected_offer": self._choose_offer(offers),
            "trace": {**state.get("trace", {}), "supplier_offers": len(offers)},
        }

    async def calculate(self, state: OrderingState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        features = state.get("features", {})
        forecast = state.get("forecast", {})
        offer = state.get("selected_offer") or {}
        if not offer:
            return {
                "suggestion": {
                    "suggested_qty": 0,
                    "risks": ["supplier_unavailable"],
                    "reasons": ["未获取到供应商可供货信息，建议转人工确认"],
                },
                "trace": {**state.get("trace", {}), "calculation": "no_supplier"},
            }
        result = self._calculator.calculate(
            ReplenishmentInput(
                daily_qty=float(forecast.get("daily_qty", 0.0)),
                confidence=float(forecast.get("confidence", 0.0)),
                coverage_days=int(state.get("coverage_days", 7)),
                safety_days=settings.default_safety_days,
                on_hand=int(features.get("on_hand", 0)),
                in_transit=int(features.get("in_transit", 0)),
                moq=int(offer.get("moq", 0)),
                case_pack=int(offer.get("case_pack", 1)),
                available_qty=int(offer.get("available_qty", 0)),
                unit_price=float(offer.get("unit_price", 0.0)),
                budget=float(features.get("budget", 100000.0)),
                max_order_qty=settings.max_order_qty,
                shelf_life_days=int(features.get("shelf_life_days", 0)),
                lead_time_days=int(offer.get("lead_time_days", 0)),
            )
        )
        impact = apply_notices(state["sku"], state.get("notices", []))
        risks = list(result.risks)
        reasons = list(result.reasons)
        suggested_qty = result.suggested_qty
        if impact.blocked_skus:
            suggested_qty = 0
            risks.append("recall_blocked")
            reasons.append("商品召回，停止订货")
        return {
            "suggestion": {
                "suggested_qty": suggested_qty,
                "forecast_demand": result.forecast_demand,
                "safety_stock": result.safety_stock,
                "raw_gap": result.raw_gap,
                "risks": risks,
                "reasons": reasons,
                "supplier_code": offer.get("supplier_code", ""),
                "supplier_sku": offer.get("supplier_sku", ""),
                "unit_price": offer.get("unit_price", 0.0),
            },
            "reminders": impact.reminders,
            "trace": {**state.get("trace", {}), "calculation": "deterministic"},
        }

    async def explain(self, state: OrderingState) -> dict[str, Any]:
        if state.get("error"):
            return {"explanation": state["error"]}
        suggestion = state.get("suggestion", {})
        forecast = state.get("forecast", {})
        fallback = (
            f"建议订货量 {suggestion.get('suggested_qty', 0)}。"
            f"预测日销 {forecast.get('daily_qty', 0)}，覆盖 {state.get('coverage_days', 7)} 天，"
            f"结合现有库存和在途库存计算；风险：{', '.join(suggestion.get('risks', [])) or '无'}。"
            f"公告提醒 {len(state.get('reminders', []))} 条，请店长逐条确认。"
            "请店长结合陈列、天气和促销再做确认。"
        )
        if not settings.llm_api_key:
            return {"explanation": fallback, "trace": {**state.get("trace", {}), "explain": "template"}}
        prompt = (
            f"建议数据：{suggestion}\n预测数据：{forecast}\n"
            f"门店：{state.get('store_id')}，SKU：{state.get('sku')}，覆盖天数：{state.get('coverage_days')}\n"
            f"公告：{state.get('notices', [])}\n提醒：{state.get('reminders', [])}"
        )
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": settings.llm_model,
                        "temperature": 0.2,
                        "messages": [
                            {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                    },
                )
                response.raise_for_status()
                text = str(response.json()["choices"][0]["message"]["content"]).strip()
            # Guardrail: if the model omits the calculated quantity, use the
            # deterministic template instead of trusting a fluent but incomplete answer.
            if str(suggestion.get("suggested_qty")) not in text:
                text = fallback
            return {"explanation": text, "trace": {**state.get("trace", {}), "explain": "llm"}}
        except Exception:  # noqa: BLE001
            return {"explanation": fallback, "trace": {**state.get("trace", {}), "explain": "fallback"}}

    @staticmethod
    def _first(values: list[str]) -> str:
        return values[0] if values else ""

    @staticmethod
    def _choose_offer(offers: list[dict[str, Any]]) -> dict[str, Any] | None:
        viable = [offer for offer in offers if int(offer.get("available_qty", 0)) > 0]
        if not viable:
            return None
        return sorted(
            viable,
            key=lambda offer: (
                float(offer.get("unit_price", 0)),
                int(offer.get("lead_time_days", 0)),
                -int(offer.get("available_qty", 0)),
            ),
        )[0]