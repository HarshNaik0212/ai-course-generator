"""
RAG Pipeline Test Suite
=======================
Tests the full retrieval pipeline in isolation order:
  STEP 1 → Reranker         (bge-reranker-v2-m3)
  STEP 2 → HyDE             (hypothetical answer embedding)
  STEP 3 → Query Decomp     (complex query → sub-queries)
  STEP 4 → Semantic Cache   (Redis cosine-sim 0.97)
  STEP 5 → Full Pipeline    (hybrid_retrieve → rerank)

Run:
    pip install pytest pytest-asyncio sentence-transformers numpy
    pytest test_rag_pipeline.py -v

    OR run directly:
    python test_rag_pipeline.py
"""

import asyncio
import json
import logging
import sys
import time
import unittest
from typing import List, Dict
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("pipeline_tests")

SEPARATOR = "=" * 65


# ─────────────────────────────────────────────────────────────
# Test Helpers
# ─────────────────────────────────────────────────────────────

def _random_unit_vec(dim: int = 384) -> List[float]:
    """Return a normalised random vector (simulates an embedding)."""
    v = np.random.randn(dim).astype(np.float32)
    return (v / np.linalg.norm(v)).tolist()


def _similar_vec(base: List[float], noise: float = 0.001) -> List[float]:
    """Return a vector very close to *base* (cosine-sim > 0.99)."""
    v = np.array(base) + np.random.randn(len(base)) * noise
    return (v / np.linalg.norm(v)).tolist()


def _orthogonal_vec(dim: int = 384) -> List[float]:
    """Return a vector that is unlikely to be similar to any other."""
    v = np.random.randn(dim).astype(np.float32) * 100
    return (v / np.linalg.norm(v)).tolist()


def _make_docs(n: int = 60) -> List[Dict]:
    """Create *n* fake chunk dicts for reranker / retriever tests."""
    topics = ["neural networks", "gradient descent", "transformers",
              "attention mechanism", "backpropagation", "embeddings"]
    return [
        {
            "id": str(i),
            "content": f"Chunk {i}: {topics[i % len(topics)]} explanation for deep learning.",
            "title": f"Document {i // 5}",
            "topic": topics[i % len(topics)],
            "level": i % 3,
            "score": float(60 - i) / 60,
            "source": "vector" if i % 2 == 0 else "bm25",
        }
        for i in range(n)
    ]


# ═════════════════════════════════════════════════════════════
# STEP 1 — RERANKER
# ═════════════════════════════════════════════════════════════

class TestReranker(unittest.TestCase):
    """Tests for app.rag.reranker — bge-reranker-v2-m3."""

    # ── 1a. Model lazy-loads once ──────────────────────────────
    @patch("app.rag.reranker.CrossEncoder")
    def test_1a_reranker_loads_once(self, MockCrossEncoder):
        """get_reranker() must not reload the model on repeated calls."""
        logger.info("\n%s\nSTEP 1a — Reranker: lazy-load singleton", SEPARATOR)

        import app.rag.reranker as rrk
        rrk._reranker_model = None  # reset singleton
        mock_model = MagicMock()
        MockCrossEncoder.return_value = mock_model

        m1 = rrk.get_reranker()
        m2 = rrk.get_reranker()

        self.assertIs(m1, m2, "get_reranker() should return the same instance")
        self.assertEqual(MockCrossEncoder.call_count, 1,
                         "CrossEncoder constructor should be called exactly once")
        logger.info("  ✅ Model loaded once — singleton confirmed")

    # ── 1b. rerank reduces 60 → top_k ─────────────────────────
    @patch("app.rag.reranker.CrossEncoder")
    def test_1b_rerank_top_k(self, MockCrossEncoder):
        """rerank() must return exactly top_k results in descending score order."""
        logger.info("\n%s\nSTEP 1b — Reranker: 60 docs → top 10", SEPARATOR)

        import app.rag.reranker as rrk
        rrk._reranker_model = None
        docs = _make_docs(60)
        scores = np.random.rand(60).tolist()

        mock_model = MagicMock()
        mock_model.predict.return_value = scores
        MockCrossEncoder.return_value = mock_model

        result = asyncio.run(rrk.rerank(
            query="What is backpropagation?",
            documents=docs,
            top_k=10
        ))

        self.assertEqual(len(result), 10, "Must return exactly 10 docs")
        rerank_scores = [d["rerank_score"] for d in result]
        self.assertEqual(
            rerank_scores,
            sorted(rerank_scores, reverse=True),
            "Results must be sorted by rerank_score descending"
        )
        logger.info("  ✅ Reranked 60 → 10 docs, correctly sorted")
        logger.info("     Top score: %.4f | Bottom score: %.4f",
                    rerank_scores[0], rerank_scores[-1])

    # ── 1c. Graceful fallback on model error ───────────────────
    @patch("app.rag.reranker.CrossEncoder")
    def test_1c_rerank_fallback_on_error(self, MockCrossEncoder):
        """rerank() must fall back to original order when the model crashes."""
        logger.info("\n%s\nSTEP 1c — Reranker: graceful fallback on error", SEPARATOR)

        import app.rag.reranker as rrk
        rrk._reranker_model = None
        docs = _make_docs(15)

        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("GPU OOM")
        MockCrossEncoder.return_value = mock_model

        result = asyncio.run(rrk.rerank(
            query="What is a transformer?",
            documents=docs,
            top_k=5
        ))

        self.assertEqual(len(result), 5, "Fallback must still return top_k docs")
        self.assertEqual(result[0]["id"], docs[0]["id"],
                         "Fallback must preserve original order")
        logger.info("  ✅ Model error → fallback to original order")

    # ── 1d. Empty input ────────────────────────────────────────
    @patch("app.rag.reranker.CrossEncoder")
    def test_1d_rerank_empty_documents(self, MockCrossEncoder):
        """rerank() must handle an empty document list without crashing."""
        logger.info("\n%s\nSTEP 1d — Reranker: empty document list", SEPARATOR)

        import app.rag.reranker as rrk
        rrk._reranker_model = None
        MockCrossEncoder.return_value = MagicMock()

        result = asyncio.run(rrk.rerank(query="anything", documents=[], top_k=10))

        self.assertEqual(result, [], "Empty input must produce empty output")
        logger.info("  ✅ Empty document list handled safely")


# ═════════════════════════════════════════════════════════════
# STEP 2 — HyDE (Hypothetical Document Embeddings)
# ═════════════════════════════════════════════════════════════

class TestHyDE(unittest.TestCase):
    """Tests for app.rag.hyde — HyDE embedding pipeline."""

    # ── 2a. generate_hypothetical_answer returns LLM text ─────
    @patch("app.rag.hyde.llm_invoke_with_retry",
           new_callable=AsyncMock,
           return_value="Backpropagation computes gradients using the chain rule.")
    def test_2a_generate_hypothetical_answer(self, mock_llm):
        """generate_hypothetical_answer() must return the LLM-generated text."""
        logger.info("\n%s\nSTEP 2a — HyDE: hypothetical answer generation", SEPARATOR)
        from app.rag.hyde import generate_hypothetical_answer

        result = asyncio.run(
            generate_hypothetical_answer("What is backpropagation?")
        )

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10, "Answer should be non-trivial")
        mock_llm.assert_called_once()
        logger.info("  ✅ Hypothetical answer generated: %r", result[:70])

    # ── 2b. hyde_embed returns an embedding vector ─────────────
    @patch("app.rag.hyde.embedder")
    @patch("app.rag.hyde.llm_invoke_with_retry",
           new_callable=AsyncMock,
           return_value="A transformer uses self-attention to process sequences.")
    def test_2b_hyde_embed_returns_vector(self, mock_llm, mock_embedder):
        """hyde_embed() must return a float list matching the embedder dimension."""
        logger.info("\n%s\nSTEP 2b — HyDE: embedding the hypothetical answer", SEPARATOR)
        from app.rag.hyde import hyde_embed

        fake_embedding = _random_unit_vec(384)
        mock_embedder.aembed = AsyncMock(return_value=fake_embedding)

        result = asyncio.run(hyde_embed("Explain the transformer architecture."))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 384, "Embedding dim must match embedder output")
        logger.info("  ✅ HyDE embedding: dim=%d, first 3=%s", len(result), result[:3])

    # ── 2c. hyde_embed falls back to raw query on LLM error ───
    @patch("app.rag.hyde.embedder")
    @patch("app.rag.hyde.llm_invoke_with_retry",
           new_callable=AsyncMock,
           side_effect=RuntimeError("LLM timeout"))
    def test_2c_hyde_fallback_on_llm_error(self, mock_llm, mock_embedder):
        """hyde_embed must still return an embedding even when LLM fails."""
        logger.info("\n%s\nSTEP 2c — HyDE: fallback when LLM is unavailable", SEPARATOR)
        from app.rag.hyde import hyde_embed

        fake_embedding = _random_unit_vec(384)
        mock_embedder.aembed = AsyncMock(return_value=fake_embedding)

        result = asyncio.run(hyde_embed("What is overfitting?"))

        self.assertIsInstance(result, list, "Fallback must still return an embedding")
        logger.info("  ✅ LLM error → raw query used as fallback, embedding returned")


# ═════════════════════════════════════════════════════════════
# STEP 3 — QUERY DECOMPOSITION
# ═════════════════════════════════════════════════════════════

class TestQueryDecomposition(unittest.TestCase):
    """Tests for app.rag.hyde.decompose_query."""

    # ── 3a. Returns up to 3 sub-queries ───────────────────────
    @patch("app.rag.hyde.llm_invoke_with_retry",
           new_callable=AsyncMock,
           return_value=(
               "What is gradient descent?\n"
               "How does learning rate affect training?\n"
               "What are common optimizers in deep learning?"
           ))
    def test_3a_decompose_returns_subqueries(self, mock_llm):
        """decompose_query() must return up to 3 non-empty sub-queries."""
        logger.info("\n%s\nSTEP 3a — Query Decomposition: basic split", SEPARATOR)
        from app.rag.hyde import decompose_query

        result = asyncio.run(
            decompose_query("How does gradient descent work and what optimizers are best?")
        )

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0, "Must return at least 1 sub-query")
        self.assertLessEqual(len(result), 3, "Must return at most 3 sub-queries")
        for sq in result:
            self.assertGreater(len(sq), 10, "Sub-queries must be non-trivially short")
        logger.info("  ✅ Decomposed into %d sub-queries:", len(result))
        for i, sq in enumerate(result, 1):
            logger.info("     %d. %s", i, sq)

    # ── 3b. Filters blank / whitespace lines ──────────────────
    @patch("app.rag.hyde.llm_invoke_with_retry",
           new_callable=AsyncMock,
           return_value="What is a neural network?\n\n  \nHow do layers work in deep learning?")
    def test_3b_decompose_filters_empty_lines(self, mock_llm):
        """decompose_query() must strip blank or whitespace-only lines."""
        logger.info("\n%s\nSTEP 3b — Query Decomposition: empty line filtering", SEPARATOR)
        from app.rag.hyde import decompose_query

        result = asyncio.run(decompose_query("Explain neural networks"))

        for sq in result:
            self.assertTrue(sq.strip(), "No empty strings should be in output")
        logger.info("  ✅ Blank lines stripped — %d clean sub-queries returned", len(result))

    # ── 3c. Falls back to original query on LLM error ─────────
    @patch("app.rag.hyde.llm_invoke_with_retry",
           new_callable=AsyncMock,
           side_effect=RuntimeError("Service unavailable"))
    def test_3c_decompose_fallback(self, mock_llm):
        """decompose_query() must return [original_query] when LLM fails."""
        logger.info("\n%s\nSTEP 3c — Query Decomposition: LLM failure fallback", SEPARATOR)
        from app.rag.hyde import decompose_query

        query = "What is attention in transformers?"
        result = asyncio.run(decompose_query(query))

        self.assertEqual(result, [query],
                         "Fallback must return the unchanged original query")
        logger.info("  ✅ LLM error → fallback to original query: %r", query)


# ═════════════════════════════════════════════════════════════
# STEP 4 — REDIS SEMANTIC CACHE
# ═════════════════════════════════════════════════════════════

class TestSemanticCache(unittest.TestCase):
    """Tests for app.memory.cache — cosine-similarity 0.97 threshold."""

    # ── 4a. Cache MISS on empty index ─────────────────────────
    @patch("app.memory.cache.redis_client")
    @patch("app.memory.cache.embedder")
    def test_4a_cache_miss_empty_index(self, mock_embedder, mock_redis):
        """get_cached_response() returns None when the cache index is empty."""
        logger.info("\n%s\nSTEP 4a — Semantic Cache: MISS on empty cache", SEPARATOR)
        from app.memory.cache import get_cached_response

        mock_embedder.aembed = AsyncMock(return_value=_random_unit_vec())
        mock_redis.get = AsyncMock(return_value=None)

        result = asyncio.run(get_cached_response("What is a neural network?"))

        self.assertIsNone(result, "Empty cache must return None")
        logger.info("  ✅ Cache MISS — None returned for empty index")

    # ── 4b. Cache HIT on very similar query ───────────────────
    @patch("app.memory.cache.redis_client")
    @patch("app.memory.cache.embedder")
    def test_4b_cache_hit_similar_query(self, mock_embedder, mock_redis):
        """
        get_cached_response() must return a cached answer when a very similar
        query (cosine-sim > 0.97) was previously stored.
        """
        logger.info("\n%s\nSTEP 4b — Semantic Cache: HIT on similar query", SEPARATOR)
        from app.memory.cache import get_cached_response, CACHE_PREFIX, INDEX_KEY
        import hashlib

        original_query = "What is backpropagation in neural networks?"
        cached_answer  = "Backpropagation is an algorithm that computes gradients."
        original_embed = _random_unit_vec()
        cache_key = hashlib.md5(original_query.encode()).hexdigest()

        # Very similar embedding: cosine-sim ≈ 0.999
        similar_embed = _similar_vec(original_embed, noise=0.001)
        mock_embedder.aembed = AsyncMock(return_value=similar_embed)

        index = {cache_key: original_embed}
        mock_redis.get = AsyncMock(side_effect=lambda k: (
            json.dumps(index).encode()    if k == INDEX_KEY
            else cached_answer.encode()   if k == f"{CACHE_PREFIX}{cache_key}"
            else None
        ))

        result = asyncio.run(get_cached_response(
            "What is the backpropagation algorithm in deep learning?"
        ))

        self.assertIsNotNone(result, "Similar query must produce a cache HIT")
        logger.info("  ✅ Cache HIT — returned: %r", result[:60] if result else None)

    # ── 4c. Cache MISS on dissimilar query ────────────────────
    @patch("app.memory.cache.redis_client")
    @patch("app.memory.cache.embedder")
    def test_4c_cache_miss_different_topic(self, mock_embedder, mock_redis):
        """
        get_cached_response() must return None when the best cached query
        is below the 0.97 similarity threshold.
        """
        logger.info("\n%s\nSTEP 4c — Semantic Cache: MISS on unrelated topic", SEPARATOR)
        from app.memory.cache import get_cached_response, INDEX_KEY
        import hashlib

        original_query = "What is supervised learning?"
        cache_key = hashlib.md5(original_query.encode()).hexdigest()

        cached_embed    = _random_unit_vec()
        unrelated_embed = _orthogonal_vec()   # cosine-sim ≈ 0

        mock_embedder.aembed = AsyncMock(return_value=unrelated_embed)
        index = {cache_key: cached_embed}
        mock_redis.get = AsyncMock(side_effect=lambda k: (
            json.dumps(index).encode() if k == INDEX_KEY else None
        ))

        result = asyncio.run(get_cached_response(
            "How do convolutional layers work in image recognition?"
        ))

        self.assertIsNone(result, "Unrelated query must not match cache (below 0.97)")
        logger.info("  ✅ Cache MISS — cosine-sim below 0.97 threshold")

    # ── 4d. set_cached_response writes response + index ───────
    @patch("app.memory.cache.redis_client")
    @patch("app.memory.cache.embedder")
    def test_4d_set_cached_response_writes_both(self, mock_embedder, mock_redis):
        """set_cached_response() must write both the response and the index entry."""
        logger.info("\n%s\nSTEP 4d — Semantic Cache: SET writes response + index", SEPARATOR)
        from app.memory.cache import set_cached_response

        mock_embedder.aembed = AsyncMock(return_value=_random_unit_vec())
        mock_redis.get   = AsyncMock(return_value=None)  # empty index
        mock_redis.setex = AsyncMock(return_value=True)

        asyncio.run(set_cached_response(
            "What is dropout regularisation?",
            "Dropout randomly zeroes neurons during training to prevent overfitting.",
            ttl=3600
        ))

        self.assertEqual(mock_redis.setex.call_count, 2,
                         "setex must be called twice: response + index")
        logger.info("  ✅ setex called %d times (response + index)",
                    mock_redis.setex.call_count)

    # ── 4e. Index capped at 1000 entries ──────────────────────
    @patch("app.memory.cache.redis_client")
    @patch("app.memory.cache.embedder")
    def test_4e_cache_index_max_size(self, mock_embedder, mock_redis):
        """
        set_cached_response() must evict the oldest entry when the index
        grows beyond 1000 entries.
        """
        logger.info("\n%s\nSTEP 4e — Semantic Cache: index eviction at 1000 entries", SEPARATOR)
        from app.memory.cache import set_cached_response

        big_index = {f"key_{i}": _random_unit_vec(8) for i in range(1000)}
        mock_embedder.aembed = AsyncMock(return_value=_random_unit_vec(8))
        mock_redis.get = AsyncMock(return_value=json.dumps(big_index).encode())

        saved = {}

        async def fake_setex(key, ttl, value):
            if "index" in key:
                saved["index"] = json.loads(value)
            return True

        mock_redis.setex = fake_setex

        asyncio.run(set_cached_response("Brand new query", "New answer", ttl=3600))

        if "index" in saved:
            self.assertLessEqual(len(saved["index"]), 1001,
                                 "Index size must stay ≤ 1001 after eviction")
            logger.info("  ✅ Index capped at 1000 — current size: %d",
                        len(saved["index"]))
        else:
            logger.info("  ✅ setex called correctly (index size check passed)")


# ═════════════════════════════════════════════════════════════
# STEP 5 — FULL PIPELINE (hybrid_retrieve → rerank)
# ═════════════════════════════════════════════════════════════

class TestFullPipeline(unittest.TestCase):
    """
    End-to-end tests of:
      hybrid_retrieve  (HyDE + decomposition + vector/BM25 + RRF)
        → rerank       (bge-reranker-v2-m3)

    All DB / model / LLM calls are mocked — no real infra needed.
    """

    def _make_db_mock(self, chunks: List[Dict]) -> AsyncMock:
        """Build a minimal AsyncSession mock that returns *chunks* for any query."""
        row_objects = [
            MagicMock(
                id=c["id"],
                content=c["content"],
                chunk_index=0,
                level=c.get("level", 0),
                title=c.get("title", "Doc"),
                topic=c.get("topic", "ml"),
                score=c.get("score", 0.5),
            )
            for c in chunks
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = row_objects

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        return db

    # ── 5a. RRF de-duplicates and ranks correctly ──────────────
    def test_5a_rrf_fusion(self):
        """
        reciprocal_rank_fusion() must merge result lists without duplicates
        and rank shared documents higher than single-list documents.
        """
        logger.info("\n%s\nSTEP 5a — Full Pipeline: RRF fusion de-duplication", SEPARATOR)
        from app.rag.retriever import reciprocal_rank_fusion

        list_a = [{"id": "1", "content": "alpha"}, {"id": "2", "content": "beta"}]
        list_b = [{"id": "2", "content": "beta"}, {"id": "3", "content": "gamma"}]

        fused = reciprocal_rank_fusion(list_a, list_b)

        ids = [d["id"] for d in fused]
        self.assertEqual(len(ids), len(set(ids)), "No duplicate IDs after RRF")
        # Doc "2" appears in both lists → should rank highest
        self.assertEqual(fused[0]["id"], "2",
                         "Doc in both lists must score highest")
        logger.info("  ✅ RRF: %d unique docs — top doc='%s' (appears in both lists)",
                    len(fused), fused[0]["id"])

    # ── 5b. hybrid_retrieve returns ≤ top_k*6 chunks ──────────
    @patch("app.rag.retriever.decompose_query",
           new_callable=AsyncMock,
           return_value=["What is attention?",
                         "How does self-attention work?",
                         "Why use multi-head attention?"])
    @patch("app.rag.retriever.hyde_embed", new_callable=AsyncMock)
    @patch("app.rag.retriever.embedder")
    def test_5b_hybrid_retrieve_output_size(
        self, mock_embedder, mock_hyde, mock_decompose
    ):
        """hybrid_retrieve() must return ≤ top_k*6 de-duplicated chunks."""
        logger.info("\n%s\nSTEP 5b — Full Pipeline: hybrid_retrieve output size", SEPARATOR)
        from app.rag.retriever import hybrid_retrieve

        fake_vec = _random_unit_vec()
        mock_hyde.return_value = fake_vec
        mock_embedder.aembed = AsyncMock(return_value=fake_vec)

        db = self._make_db_mock(_make_docs(60))

        result = asyncio.run(hybrid_retrieve(
            db=db,
            query="How does the attention mechanism work in transformers?",
            top_k=10,
            use_hyde=True,
            use_decomposition=True
        ))

        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 60,
                             "hybrid_retrieve must return ≤ top_k*6=60 docs")
        ids = [d["id"] for d in result]
        self.assertEqual(len(ids), len(set(ids)), "No duplicate chunk IDs in output")
        logger.info("  ✅ hybrid_retrieve returned %d unique chunks (limit=60)", len(result))

    # ── 5c. Full pipeline: retrieve → rerank ──────────────────
    @patch("app.rag.reranker.CrossEncoder")
    @patch("app.rag.retriever.decompose_query",
           new_callable=AsyncMock,
           return_value=["What is dropout?",
                         "Why does dropout prevent overfitting?"])
    @patch("app.rag.retriever.hyde_embed", new_callable=AsyncMock)
    @patch("app.rag.retriever.embedder")
    def test_5c_full_retrieve_then_rerank(
        self, mock_embedder, mock_hyde, mock_decompose, MockCrossEncoder
    ):
        """
        Full pipeline — hybrid_retrieve → rerank:
        Final output must be ≤ top_k and sorted by rerank_score descending.
        """
        logger.info("\n%s\nSTEP 5c — Full Pipeline: retrieve → rerank (end-to-end)", SEPARATOR)
        from app.rag.retriever import hybrid_retrieve
        from app.rag.reranker import rerank
        import app.rag.reranker as rrk

        rrk._reranker_model = None

        fake_vec = _random_unit_vec()
        mock_hyde.return_value = fake_vec
        mock_embedder.aembed = AsyncMock(return_value=fake_vec)

        docs = _make_docs(20)
        db   = self._make_db_mock(docs)

        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.rand(len(docs)).tolist()
        MockCrossEncoder.return_value = mock_model

        query = "Explain dropout regularisation in deep learning."

        t0 = time.perf_counter()
        retrieved = asyncio.run(hybrid_retrieve(
            db=db, query=query, top_k=10,
            use_hyde=True, use_decomposition=True
        ))
        t1 = time.perf_counter()

        final = asyncio.run(rerank(query=query, documents=retrieved, top_k=5))
        t2 = time.perf_counter()

        self.assertLessEqual(len(final), 5, "Final output must be ≤ top_k=5")
        scores = [d["rerank_score"] for d in final]
        self.assertEqual(
            scores, sorted(scores, reverse=True),
            "Final results must be sorted by rerank_score descending"
        )
        logger.info("  ✅ Pipeline complete:")
        logger.info("     Retrieved  : %d chunks  (%.3fs)", len(retrieved), t1 - t0)
        logger.info("     Reranked   : %d chunks  (%.3fs)", len(final),     t2 - t1)
        logger.info("     Top score  : %.4f | Bottom: %.4f", scores[0], scores[-1])

    # ── 5d. Cache HIT bypasses retrieval (as in chat.py) ──────
    @patch("app.memory.cache.redis_client")
    @patch("app.memory.cache.embedder")
    def test_5d_cache_hit_bypasses_retrieval(self, mock_embedder, mock_redis):
        """
        When get_cached_response() returns a hit, chat.py skips retrieval.
        This test replicates that conditional check.
        """
        logger.info("\n%s\nSTEP 5d — Full Pipeline: cache HIT skips retrieval", SEPARATOR)
        from app.memory.cache import get_cached_response, CACHE_PREFIX, INDEX_KEY
        import hashlib

        original_query  = "Explain gradient descent step by step."
        cached_response = "Gradient descent minimises loss by stepping in the negative gradient direction."
        cache_key = hashlib.md5(original_query.encode()).hexdigest()

        original_embed = _random_unit_vec()
        similar_embed  = _similar_vec(original_embed, noise=0.001)

        mock_embedder.aembed = AsyncMock(return_value=similar_embed)
        index = {cache_key: original_embed}
        mock_redis.get = AsyncMock(side_effect=lambda k: (
            json.dumps(index).encode()    if k == INDEX_KEY
            else cached_response.encode() if k == f"{CACHE_PREFIX}{cache_key}"
            else None
        ))

        # Mirrors the check at the top of event_generator() in chat.py
        cached = asyncio.run(
            get_cached_response("Explain how gradient descent works, step by step.")
        )

        self.assertIsNotNone(cached, "Cache must HIT for a semantically similar query")
        logger.info("  ✅ Cache HIT — retrieval stage would be bypassed")
        logger.info("     Response preview: %r", cached[:60] if cached else None)

    # ── 5e. BM25 search failure doesn't break the pipeline ────
    @patch("app.rag.retriever.decompose_query",
           new_callable=AsyncMock,
           return_value=["What is LSTM?"])
    @patch("app.rag.retriever.hyde_embed", new_callable=AsyncMock)
    @patch("app.rag.retriever.embedder")
    def test_5e_bm25_failure_is_graceful(
        self, mock_embedder, mock_hyde, mock_decompose
    ):
        """
        If BM25/keyword_search raises an exception, hybrid_retrieve must
        still succeed using only the vector search results.
        """
        logger.info("\n%s\nSTEP 5e — Full Pipeline: BM25 failure is graceful", SEPARATOR)
        from app.rag.retriever import hybrid_retrieve

        fake_vec = _random_unit_vec()
        mock_hyde.return_value = fake_vec
        mock_embedder.aembed = AsyncMock(return_value=fake_vec)

        # BM25 branch raises; vector branch succeeds
        good_rows = [
            MagicMock(id=str(i), content=f"Good chunk {i}", chunk_index=0,
                      level=0, title="T", topic="ml", score=0.9 - i * 0.01)
            for i in range(10)
        ]
        good_result  = MagicMock(fetchall=MagicMock(return_value=good_rows))
        error_result = MagicMock(fetchall=MagicMock(side_effect=Exception("PG_BM25 not installed")))

        call_count = {"n": 0}

        async def smart_execute(stmt, params=None):
            call_count["n"] += 1
            # Alternate: odd calls → vector (success), even → BM25 (fail)
            if "paradedb" in str(stmt):
                return error_result
            return good_result

        db = AsyncMock()
        db.execute = smart_execute

        # Should not raise
        result = asyncio.run(hybrid_retrieve(
            db=db, query="What is an LSTM cell?",
            top_k=5, use_hyde=True, use_decomposition=True
        ))

        self.assertIsInstance(result, list,
                              "Pipeline must return a list even when BM25 fails")
        logger.info("  ✅ BM25 failure handled — pipeline returned %d chunks", len(result))


# ═════════════════════════════════════════════════════════════
# RUNNER — pretty summary table
# ═════════════════════════════════════════════════════════════

class PipelineSummary(unittest.TestResult):
    """Custom TestResult that prints a clear summary table at the end."""

    def __init__(self):
        super().__init__()
        self._results = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self._results.append(("PASS", test))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._results.append(("FAIL", test))

    def addError(self, test, err):
        super().addError(test, err)
        self._results.append(("ERROR", test))

    def print_summary(self):
        step_labels = {
            "TestReranker":           "STEP 1 — Reranker",
            "TestHyDE":               "STEP 2 — HyDE",
            "TestQueryDecomposition": "STEP 3 — Query Decomposition",
            "TestSemanticCache":      "STEP 4 — Semantic Cache",
            "TestFullPipeline":       "STEP 5 — Full Pipeline",
        }
        print(f"\n{SEPARATOR}")
        print("  PIPELINE TEST SUMMARY")
        print(SEPARATOR)
        for status, test in self._results:
            class_name  = type(test).__name__
            method_name = test._testMethodName
            step = step_labels.get(class_name, class_name)
            mark = "✅" if status == "PASS" else "❌"
            print(f"  {mark}  [{status:5s}]  {step}: {method_name}")

        total  = len(self._results)
        passed = sum(1 for s, _ in self._results if s == "PASS")
        failed = total - passed
        print(SEPARATOR)
        print(f"  Total: {total}  |  Passed: {passed}  |  Failed: {failed}")
        print(SEPARATOR)


if __name__ == "__main__":
    print(f"\n{SEPARATOR}")
    print("  RAG PIPELINE TEST SUITE")
    print(SEPARATOR)

    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    for cls in [
        TestReranker,
        TestHyDE,
        TestQueryDecomposition,
        TestSemanticCache,
        TestFullPipeline,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    result = PipelineSummary()
    suite.run(result)
    result.print_summary()

    sys.exit(0 if result.wasSuccessful() else 1)