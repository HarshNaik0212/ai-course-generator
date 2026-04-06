from FlagEmbedding import FlagReranker
from typing import List, Dict
import logging
import asyncio

logger = logging.getLogger(__name__)


class Reranker:
    _instance = None

    def __init__(self):
        logger.info("Loading bge-reranker-v2-m3 on CPU...")
        self.model = FlagReranker(
            "BAAI/bge-reranker-v2-m3",
            use_fp16=False     # CPU — use fp32
        )
        logger.info("Reranker loaded ✅")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """
        Rerank chunks using cross-encoder scoring.
        Input:  top 60 candidates from hybrid retrieval
        Output: top_k most relevant chunks
        """
        if not chunks:
            return []

        # Build pairs: [query, chunk_content]
        pairs = [[query, c["content"]] for c in chunks]

        # Score on CPU (run in executor to not block async loop)
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            None,
            lambda: self.model.compute_score(pairs, normalize=True)
        )

        # Attach scores and sort
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
        logger.info(f"Reranked {len(chunks)} → top {top_k}")
        return reranked[:top_k]


reranker = Reranker.get_instance()