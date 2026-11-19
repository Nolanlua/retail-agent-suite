# 中文说明：零售订货 LangGraph 编排：解析、取特征、预测、供货、计算和解释。
"""LangGraph assembly for retail ordering.

The workflow is linear by design. A planner-style autonomous loop would add
latency and non-determinism without improving a replenishment calculation that
must be reproducible.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import OrderingNodes
from app.agent.state import OrderingState


def route_after_load(state: OrderingState) -> str:
    return "explain" if state.get("error") else "forecast"


def build_graph(nodes: OrderingNodes | None = None):
    nodes = nodes or OrderingNodes()
    builder = StateGraph(OrderingState)
    builder.add_node("parse_intent", nodes.parse_intent)
    builder.add_node("load_features", nodes.load_features)
    builder.add_node("load_notices", nodes.load_notices)
    builder.add_node("forecast", nodes.forecast)
    builder.add_node("supply", nodes.supply)
    builder.add_node("calculate", nodes.calculate)
    builder.add_node("explain", nodes.explain)

    builder.add_edge(START, "parse_intent")
    builder.add_edge("parse_intent", "load_features")
    builder.add_conditional_edges(
        "load_features",
        route_after_load,
        {"forecast": "load_notices", "explain": "explain"},
    )
    builder.add_edge("load_notices", "forecast")
    builder.add_edge("forecast", "supply")
    builder.add_edge("supply", "calculate")
    builder.add_edge("calculate", "explain")
    builder.add_edge("explain", END)
    return builder.compile(checkpointer=MemorySaver())