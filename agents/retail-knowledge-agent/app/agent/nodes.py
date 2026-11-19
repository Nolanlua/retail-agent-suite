# 中文说明：零售知识库 Agent 节点：意图分类、术语归一、混合检索、图谱扩展、合规预检、生成和引用校验。
"""LangGraph nodes for the retail knowledge agent."""
from __future__ import annotations

import asyncio
import re
from typing import Any

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import KnowledgeState
from app.clients import LLMClient
from app.config import settings
from app.retrieval.citation import CitationBuilder, fallback_answer
from app.retrieval.retriever import KnowledgeRetriever, RetrievedChunk, rrf_fuse
from app.safety.guard import ComplianceGuard

SYNONYMS = {
    "端头": "陈列端头",
    "堆头": "端架陈列",
    "陈列面": "排面",
    "叫货": "订货",
    "新品": "新商品",
    "特价": "促销价",
    "万优": "南京万优",
}


class KnowledgeNodes:
    def __init__(self, retriever: KnowledgeRetriever, safety: ComplianceGuard) -> None:
        self._retriever = retriever
        self._safety = safety
        self._llm = LLMClient()
        self._citation = CitationBuilder()

    async def classify(self, state: KnowledgeState) -> dict[str, Any]:
        question = state.get("question", "")
        if re.search(r"端头|堆头|陈列|排面", question):
            intent = "display"
        elif re.search(r"召回|公告|通知|变更", question):
            intent = "notice"
        elif re.search(r"供应商|万优|到货|交期|送货", question):
            intent = "supplier"
        elif re.search(r"新品|商品|SKU|条码", question):
            intent = "product"
        elif re.search(r"SOP|流程|制度|规范|操作", question):
            intent = "operation"
        elif re.search(r"价格|促销|折扣|毛利", question):
            intent = "policy"
        else:
            intent = "general"
        return {"intent": intent, "trace": {**state.get("trace", {}), "intent": intent}}

    async def normalize(self, state: KnowledgeState) -> dict[str, Any]:
        question = state.get("question", "")
        terms: list[str] = []
        for colloquial, formal in SYNONYMS.items():
            if colloquial in question:
                terms.append(formal)
        terms.extend(re.findall(r"SKU-\d{4}|S\d{2}", question))
        terms = list(dict.fromkeys(terms))[: settings.max_rewrite_queries]
        return {
            "normalized_terms": terms or [question],
            "rewritten_queries": [question] + [f"{question} {term}" for term in terms][:2],
            "trace": {**state.get("trace", {}), "normalized_terms": terms},
        }

    async def retrieve(self, state: KnowledgeState) -> dict[str, Any]:
        tenant_id = state.get("tenant_id", "")
        queries = state.get("rewritten_queries") or [state.get("question", "")]
        tasks = [self._retriever.retrieve(query, tenant_id=tenant_id) for query in queries]
        batches = await asyncio.gather(*tasks, return_exceptions=True)
        result_lists: list[list[RetrievedChunk]] = []
        for batch in batches:
            if isinstance(batch, Exception):
                continue
            result_lists.append(batch)
        fused = rrf_fuse(result_lists, k=settings.rrf_k, top_k=settings.top_k)
        context, citations = self._citation.build(fused)
        return {
            "candidates": [
                {
                    "chunk_id": item.chunk_id,
                    "doc_id": item.doc_id,
                    "title": item.title,
                    "source": item.source,
                    "score": item.score,
                }
                for item in fused
            ],
            "context": context,
            "citations": citations,
            "trace": {**state.get("trace", {}), "candidate_count": len(fused)},
        }

    async def graph_expand(self, state: KnowledgeState) -> dict[str, Any]:
        rows = await self._retriever.graph_expand(state.get("normalized_terms", []), state.get("tenant_id", ""))
        return {"graph_facts": rows, "trace": {**state.get("trace", {}), "graph_facts": len(rows)}}

    async def safety_precheck(self, state: KnowledgeState) -> dict[str, Any]:
        decision = self._safety.evaluate(state.get("question", ""), state.get("intent", ""))
        if decision.level == "block":
            answer = (
                "这个问题涉及价格承诺、商品召回、内部资料或供应商敏感信息，知识库不能直接给出执行结论。"
                "请以系统公告、商品/供应链负责人和门店负责人最终确认为准。"
            )
            return {
                "safety_level": "block",
                "safety_reasons": decision.reasons,
                "disclaimer": decision.disclaimer,
                "answer": answer,
                "trace": {**state.get("trace", {}), "compliance": "block"},
            }
        return {"safety_level": "pass", "safety_reasons": [], "trace": {**state.get("trace", {}), "compliance": "pass"}}

    async def generate(self, state: KnowledgeState) -> dict[str, Any]:
        context = state.get("context", "")
        citations = state.get("citations", [])
        question = state.get("question", "")
        graph_facts = state.get("graph_facts", [])
        if not context:
            return {
                "answer": "知识库暂未找到足够资料回答这个问题。请补充门店、SKU、公告编号或制度名称，或咨询对应负责人。",
                "citations": [],
                "trace": {**state.get("trace", {}), "generation": "no_evidence"},
            }
        graph_text = "\n".join(f"{row[0]} -{row[1]}-> {row[2]}" for row in graph_facts[:8])
        prompt = (
            f"用户问题：{question}\n\n"
            f"检索资料：\n{context}\n\n"
            f"知识图谱关系（仅作背景，不得单独作为引用）：\n{graph_text or '无'}\n\n"
            "请基于资料回答，标注 [n] 引用；若资料不足请直接说明。"
        )
        try:
            answer = await self._llm.chat(SYSTEM_PROMPT, prompt)
        except Exception:  # noqa: BLE001 - local fallback keeps the contract
            answer = self._extractive_answer(context)
        return {"answer": answer, "trace": {**state.get("trace", {}), "generation": "llm"}}

    async def verify(self, state: KnowledgeState) -> dict[str, Any]:
        answer = state.get("answer", "")
        citations = state.get("citations", [])
        report = self._citation.validate(answer, citations)
        unsafe = self._safety.inspect_answer(answer)
        trace = state.get("trace", {})
        retry_count = int(trace.get("retry_count", 0))
        valid = report.valid and not unsafe
        if not valid and retry_count < 1:
            return {
                "validation": {"valid": False, "invalid_indexes": report.invalid_indexes, "unsafe": unsafe},
                "trace": {**trace, "retry_count": retry_count + 1, "validation": "retry"},
            }
        if not valid:
            return {
                "answer": fallback_answer(citations),
                "validation": {"valid": True, "reason": "fallback", "invalid_indexes": report.invalid_indexes},
                "trace": {**trace, "retry_count": retry_count, "validation": "fallback"},
            }
        return {
            "validation": {"valid": True, "reason": "ok", "invalid_indexes": [], "unsafe": []},
            "trace": {**trace, "retry_count": retry_count, "validation": "ok"},
        }

    async def finalize(self, state: KnowledgeState) -> dict[str, Any]:
        answer = state.get("answer", "")
        disclaimer = state.get("disclaimer") or (
            "以上内容来自公司内部知识库，仅供授权员工执行参考；价格、召回、陈列和促销以系统公告及负责人最终确认为准。"
        )
        if disclaimer not in answer:
            answer = f"{answer}\n\n{disclaimer}"
        return {"answer": answer, "disclaimer": disclaimer, "trace": {**state.get("trace", {}), "finalized": True}}

    @staticmethod
    def _extractive_answer(context: str) -> str:
        sentences = [part.strip() for part in re.split(r"[。\n]", context) if part.strip()]
        selected = "。".join(sentences[:3])
        return f"根据知识库资料：{selected}。[1] 请注意，这只是资料摘录，具体执行以系统和负责人确认为准。"
