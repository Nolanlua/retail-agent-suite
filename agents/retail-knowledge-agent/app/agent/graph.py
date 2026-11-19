# 中文说明：连锁零售 Agent 的 LangGraph 编排：检索、安全、生成、引用校验。
"""LangGraph assembly.

The graph is deliberately small: classification, terminology normalization,
retrieval, graph expansion, safety pre-check, generation and verification.
Business rules stay in domain modules; nodes only coordinate.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import KnowledgeNodes
from app.agent.state import KnowledgeState
from app.retrieval.retriever import KnowledgeRetriever
from app.safety.guard import ComplianceGuard


def route_after_safety(state: KnowledgeState) -> str:
    # Emergency and prescription requests skip generation entirely. This is
    # cheaper and safer than asking a model to refuse.
    return "finalize" if state.get("safety_level") in {"block", "emergency"} else "generate"


def route_after_verify(state: KnowledgeState) -> str:
    validation = state.get("validation", {})
    if validation.get("valid", False):
        return "finalize"
    if state.get("trace", {}).get("retry_count", 0) >= 1:
        return "finalize"
    return "retry"


def build_graph(retriever: KnowledgeRetriever, safety: ComplianceGuard):
    nodes = KnowledgeNodes(retriever=retriever, safety=safety)
    builder = StateGraph(KnowledgeState)

    builder.add_node("classify", nodes.classify)
    builder.add_node("normalize", nodes.normalize)
    builder.add_node("retrieve", nodes.retrieve)
    builder.add_node("graph_expand", nodes.graph_expand)
    builder.add_node("safety", nodes.safety_precheck)
    builder.add_node("generate", nodes.generate)
    builder.add_node("verify", nodes.verify)
    builder.add_node("finalize", nodes.finalize)

    builder.add_edge(START, "classify")
    builder.add_edge("classify", "normalize")
    builder.add_edge("normalize", "retrieve")
    builder.add_edge("retrieve", "graph_expand")
    builder.add_edge("graph_expand", "safety")
    builder.add_conditional_edges(
        "safety",
        route_after_safety,
        {"generate": "generate", "finalize": "finalize"},
    )
    builder.add_edge("generate", "verify")
    builder.add_conditional_edges(
        "verify",
        route_after_verify,
        {"retry": "generate", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)

    # MemorySaver is for local demos. Production uses AsyncPostgresSaver so a
    # conversation survives a pod restart and can be audited.
    return builder.compile(checkpointer=MemorySaver())
