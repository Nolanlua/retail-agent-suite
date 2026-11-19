# 中文说明：连锁零售混合检索：OpenSearch BM25、Qdrant 向量、RRF 融合和索引写入。
"""Hybrid retrieval for retail knowledge.

Three signals are combined:
1. BM25 from OpenSearch: exact terms, herb names, classic titles.
2. Dense vectors from Qdrant: paraphrases and colloquial symptoms.
3. Neo4j graph expansion: related herbs/formulas/classics.

RRF fuses ranked lists without comparing incompatible scores. The retriever is
an adapter; swapping Qdrant or OpenSearch does not affect the agent graph.
"""
from __future__ import annotations

import hashlib
import math
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    source: str
    section: str = ""
    score: float = 0.0
    retrieval_source: str = ""


class EmbeddingClient:
    def __init__(self) -> None:
        self._url = settings.llm_base_url.rstrip("/")

    async def embed(self, text: str) -> list[float]:
        if not settings.llm_api_key:
            # Deterministic local fallback so the service can boot without a
            # model key. It has no semantic quality and is never used for
            # production evaluation.
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            raw = [byte / 255.0 for byte in digest]
            return (raw * (settings.embedding_dim // len(raw) + 1))[: settings.embedding_dim]
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{self._url}/embeddings",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={"model": settings.embedding_model, "input": text},
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]


class KnowledgeRetriever:
    def __init__(self) -> None:
        self._embedder = EmbeddingClient()
        self._qdrant = settings.qdrant_url.rstrip("/")
        self._opensearch = settings.opensearch_url.rstrip("/")

    async def retrieve(self, query: str, tenant_id: str, top_k: int | None = None) -> list[RetrievedChunk]:
        vector = await self._embedder.embed(query)
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            vector_hits, bm25_hits = await self._gather(client, query, vector, tenant_id)
        fused = rrf_fuse([bm25_hits, vector_hits], k=settings.rrf_k)
        return fused[: top_k or settings.top_k]

    async def _gather(self, client: httpx.AsyncClient, query: str, vector: list[float], tenant_id: str):
        import asyncio

        async def vector_search():
            return await self._search_qdrant(client, vector, tenant_id)

        async def keyword_search():
            return await self._search_opensearch(client, query, tenant_id)

        results = await asyncio.gather(vector_search(), keyword_search(), return_exceptions=True)
        vector_hits = [] if isinstance(results[0], Exception) else results[0]
        bm25_hits = [] if isinstance(results[1], Exception) else results[1]
        return vector_hits, bm25_hits

    async def _search_qdrant(self, client: httpx.AsyncClient, vector: list[float], tenant_id: str):
        response = await client.post(
            f"{self._qdrant}/collections/{settings.qdrant_collection}/points/search",
            json={
                "vector": vector,
                "limit": settings.vector_top_k,
                "with_payload": True,
                "filter": {"must": [{"key": "tenant_id", "match": {"value": tenant_id}}]},
            },
        )
        response.raise_for_status()
        hits = []
        for index, item in enumerate(response.json().get("result", []), start=1):
            payload = item.get("payload", {})
            hits.append(
                RetrievedChunk(
                    chunk_id=str(item.get("id")),
                    doc_id=str(payload.get("doc_id", "")),
                    title=str(payload.get("title", "")),
                    text=str(payload.get("text", "")),
                    source=str(payload.get("source", "")),
                    section=str(payload.get("section", "")),
                    score=float(item.get("score", 0.0)),
                    retrieval_source="vector",
                )
            )
        return hits

    async def _search_opensearch(self, client: httpx.AsyncClient, query: str, tenant_id: str):
        response = await client.post(
            f"{self._opensearch}/{settings.opensearch_index}/_search",
            json={
                "size": settings.bm25_top_k,
                "query": {
                    "bool": {
                        "must": [{"multi_match": {"query": query, "fields": ["title^2", "text", "source"]}}],
                        "filter": [{"term": {"tenant_id": tenant_id}}],
                    }
                },
            },
        )
        response.raise_for_status()
        hits = []
        for item in response.json().get("hits", {}).get("hits", []):
            source = item.get("_source", {})
            hits.append(
                RetrievedChunk(
                    chunk_id=str(item.get("_id")),
                    doc_id=str(source.get("doc_id", "")),
                    title=str(source.get("title", "")),
                    text=str(source.get("text", "")),
                    source=str(source.get("source", "")),
                    section=str(source.get("section", "")),
                    score=float(item.get("_score", 0.0)),
                    retrieval_source="bm25",
                )
            )
        return hits


    async def index_page(
        self,
        *,
        chunk_id: str,
        doc_id: str,
        title: str,
        text: str,
        source: str,
        section: str,
        tenant_id: str,
    ) -> None:
        """Index one approved wiki page into both retrieval backends.

        Indexing is deliberately part of the approval workflow: a page that is
        not approved never reaches Qdrant or OpenSearch. The point id is derived
        from the stable chunk id so re-indexing is idempotent.
        """
        vector = await self._embedder.embed(title + "\n" + text)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))
        payload = {
            "doc_id": doc_id,
            "title": title,
            "text": text,
            "source": source,
            "section": section,
            "tenant_id": tenant_id,
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            qdrant = await client.put(
                f"{self._qdrant}/collections/{settings.qdrant_collection}/points?wait=true",
                json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
            )
            qdrant.raise_for_status()
            indexed = await client.put(
                f"{self._opensearch}/{settings.opensearch_index}/_doc/{chunk_id}?refresh=true",
                json=payload,
            )
            indexed.raise_for_status()

    async def delete_page(self, *, chunk_id: str) -> None:
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            await client.post(
                f"{self._qdrant}/collections/{settings.qdrant_collection}/points/delete?wait=true",
                json={"points": [point_id]},
            )
            await client.delete(f"{self._opensearch}/{settings.opensearch_index}/_doc/{chunk_id}?refresh=true")

    async def graph_expand(self, terms: list[str], tenant_id: str) -> list[dict[str, Any]]:
        """Query Neo4j over HTTP to avoid a long-lived driver in request paths."""
        if not terms:
            return []
        cypher = (
            "MATCH (e:Entity)-[r]-(n:Entity) "
            "WHERE e.name IN $terms AND e.tenant_id = $tenant "
            "RETURN e.name AS source, type(r) AS relation, n.name AS target LIMIT 20"
        )
        try:
            async with httpx.AsyncClient(timeout=5.0, auth=(settings.neo4j_user, settings.neo4j_password)) as client:
                response = await client.post(
                    f"{settings.neo4j_url.rstrip('/')}/db/neo4j/tx/commit",
                    json={"statements": [{"statement": cypher, "parameters": {"terms": terms, "tenant": tenant_id}}]},
                )
                response.raise_for_status()
                rows = response.json()["results"][0]["data"]
                return [row["row"] for row in rows]
        except Exception:  # noqa: BLE001 - graph expansion is additive, never fatal
            return []


def rrf_fuse(result_lists: list[list[RetrievedChunk]], k: int = 60, top_k: int = 20) -> list[RetrievedChunk]:
    scores: dict[str, float] = {}
    best: dict[str, RetrievedChunk] = {}
    for results in result_lists:
        for rank, hit in enumerate(results, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            if hit.chunk_id not in best:
                best[hit.chunk_id] = hit
    ordered = sorted(best.values(), key=lambda item: scores[item.chunk_id], reverse=True)
    for hit in ordered:
        hit.score = scores[hit.chunk_id]
        hit.retrieval_source = "rrf"
    return ordered[:top_k]