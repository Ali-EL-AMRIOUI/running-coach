# core/agents/retriever_agent.py
"""
RAG enriched with aerobic profile and adapted philosophy.
"""

import os
import logging
import requests
from qdrant_client import QdrantClient
from core.agents.base_agent import BaseAgent
from core.rules.formulas import compute_aerobic_profile, extract_all_records

logger = logging.getLogger(__name__)

INFINITY_URL       = os.getenv("INFINITY_URL", "http://localhost:7997")
EMBEDDING_MODEL    = "BAAI/bge-m3"
RERANKER_MODEL     = "BAAI/bge-reranker-v2-m3"
COLLECTION_NAME    = "running_knowledge"
SCORE_THRESHOLD    = 0.35
TOP_K_PER_QUERY    = 5
TOP_K_AFTER_RERANK = 6


class RetrieverAgent(BaseAgent):

    def __init__(self):
        super().__init__()
        url     = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY", None)
        self.qdrant = QdrantClient(url=url, api_key=api_key, timeout=60)
        logger.info("RetrieverAgent initialized")

    def _embed(self, texts: list) -> list:
        try:
            response = requests.post(
                f"{INFINITY_URL}/embeddings",
                json={"input": texts, "model": EMBEDDING_MODEL},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return [
                item["embedding"]
                for item in sorted(data["data"], key=lambda x: x["index"])
            ]
        except Exception as e:
            logger.error(f"Embedding: {e}")
            return []

    def _rerank(self, query: str, documents: list) -> list:
        try:
            response = requests.post(
                f"{INFINITY_URL}/rerank",
                json={
                    "query": query,
                    "documents": documents,
                    "model": RERANKER_MODEL,
                    "return_documents": False,
                },
                timeout=30,
            )
            response.raise_for_status()
            results = response.json()["results"]
            return [
                r["relevance_score"]
                for r in sorted(results, key=lambda x: x["index"])
            ]
        except Exception as e:
            logger.warning(f"Re-ranking unavailable: {e}")
            return []

    def _generate_queries(
        self,
        goal_distance: str,
        athlete_context: str,
        aerobic_profile: str = "unknown",
    ) -> list:
        """
        Generates 4-5 targeted queries based on the athlete's actual aerobic profile.
        A sprinter converting to distance needs different methods
        than a pure marathoner.
        """
        profile_hint = {
            "aerobic_elite": (
                "highly aerobic runner, strong marathon/half marathon base, "
                "focus on high mileage and polarized training"
            ),
            "aerobic": (
                "balanced aerobic runner, good endurance base, "
                "ready for threshold and tempo work"
            ),
            "mixed": (
                "mixed aerobic-anaerobic profile, strong 5k-10k, "
                "needs aerobic base development for longer distances"
            ),
            "anaerobic": (
                "anaerobic dominant athlete, track/speed background, "
                "converting to longer distances, needs aerobic development"
            ),
            "unknown": "recreational runner",
        }.get(aerobic_profile, "recreational runner")

        prompt = f"""Generate exactly 5 search queries in English to retrieve relevant content
from running training books for this athlete:

Profile: {profile_hint}
Athlete context: {athlete_context}
Goal: {goal_distance}

Queries must cover:
1. Training philosophy suited to this aerobic/anaerobic profile
2. Pace zones and intensity for this profile type
3. Weekly volume progression and periodization phases
4. Key session types (intervals, threshold, long runs) for the goal distance
5. Recovery and injury prevention for this profile

Return ONLY 5 queries, one per line, no numbering, no explanation."""

        try:
            # Replacing direct call that failed with our centralized method
            messages = [{"role": "user", "content": prompt}]
            content = self.execute_with_fallback(messages)
            
            queries = [
                q.strip()
                for q in content.strip().split("\n")
                if q.strip()
            ][:5]
            return queries if len(queries) >= 3 else self._fallback_queries(
                goal_distance, aerobic_profile
            )
        except Exception as e:
            logger.warning(f"LLM queries failed: {e}")
            return self._fallback_queries(goal_distance, aerobic_profile)

    def _fallback_queries(self, goal_distance: str, aerobic_profile: str = "unknown") -> list:
        """Fallback queries adapted to profile."""
        dist = goal_distance.lower()

        profile_query = {
            "aerobic_elite": f"polarized training high mileage {dist} Seiler Lydiard",
            "aerobic":       f"threshold tempo training aerobic {dist} Daniels Pfitzinger",
            "mixed":         f"aerobic base development speed endurance {dist}",
            "anaerobic":     f"aerobic conversion track athlete {dist} base building",
            "unknown":       f"training methodology {dist} beginner intermediate",
        }.get(aerobic_profile, f"training methodology {dist}")

        return [
            profile_query,
            f"pace zones intensity calculation {dist} performance",
            f"weekly volume progression periodization {dist}",
            f"interval threshold long run session types {dist}",
            f"recovery injury prevention endurance training",
        ]

    def _search(self, query: str, top_k: int) -> list:
        vectors = self._embed([query])
        if not vectors:
            return []
        try:
            results = self.qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=vectors[0],
                using="dense",
                limit=top_k,
                score_threshold=SCORE_THRESHOLD,
            )
            return results.points
        except Exception as e:
            logger.error(f"Search: {e}")
            return []

    def _deduplicate(self, hits: list) -> list:
        seen, unique = set(), []
        for hit in hits:
            key = (
                hit.payload.get("source", ""),
                hit.payload.get("chunk_index", hit.id),
            )
            if key not in seen:
                seen.add(key)
                unique.append(hit)
        return unique

    def _rerank_multi_query(self, queries: list, hits: list) -> list:
        """
        Re-rank against multiple queries and take the max score.
        Avoids penalizing chunks relevant to queries 2-3-4.
        """
        documents = [h.payload.get("content", "") for h in hits]
        best_scores = [0.0] * len(hits)

        for query in queries[:3]:  # max 3 reranker calls
            scores = self._rerank(query, documents)
            if scores:
                for i, s in enumerate(scores):
                    best_scores[i] = max(best_scores[i], s)

        return best_scores

    def run(
        self,
        query: str = None,
        goal_distance: str = None,
        goal_date: str = None,
        athlete_context: str = None,
        aerobic_profile: str = "unknown",
        top_k: int = TOP_K_PER_QUERY,
        **kwargs,
    ) -> str:

        logger.info(f"RetrieverAgent - profile: {aerobic_profile}")

        queries = (
            self._generate_queries(
                goal_distance,
                athlete_context or f"goal {goal_distance}",
                aerobic_profile,
            )
            if goal_distance
            else [query or "running training methodology"]
        )

        # Dense search for each query
        all_hits = []
        for q in queries:
            hits = self._search(q, top_k=top_k)
            logger.info(f"   '{q[:60]}' -> {len(hits)} chunks")
            all_hits.extend(hits)

        all_hits.sort(key=lambda h: h.score, reverse=True)
        all_hits = self._deduplicate(all_hits)
        logger.info(f"{len(all_hits)} unique chunks before reranking")

        if not all_hits:
            logger.warning("No chunks - empty RAG")
            return "No knowledge available in Qdrant."

        # Multi-query re-ranking
        best_scores = self._rerank_multi_query(queries, all_hits)

        if any(s > 0 for s in best_scores):
            ranked   = sorted(
                zip(all_hits, best_scores),
                key=lambda x: x[1],
                reverse=True,
            )
            top_hits = [hit for hit, _ in ranked[:TOP_K_AFTER_RERANK]]
            logger.info(f"Top {TOP_K_AFTER_RERANK} after multi-query reranking")
        else:
            top_hits = all_hits[:TOP_K_AFTER_RERANK]

        parts = [
            f"[Excerpt {i} | {hit.payload.get('source','?')} | score:{round(hit.score,3)}]\n"
            f"{hit.payload.get('content','')}"
            for i, hit in enumerate(top_hits, 1)
        ]
        context = "\n\n---\n\n".join(parts)
        logger.info(f"RAG context: {len(context)} characters")
        return context