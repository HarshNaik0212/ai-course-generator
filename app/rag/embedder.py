import httpx
import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingModel:
    _instance = None

    def __init__(self):
        self.url = f"{settings.amd_embedding_url}/v1/embeddings"
        self.model_name = "qwen3-embedding"
        self.dimension = settings.embedding_dim  # 1536 dimensions
        print(f"Embedding model: Qwen3-Embedding-8B @ {self.url} [OK]")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed(self, text: str) -> list[float]:
        return asyncio.get_event_loop().run_until_complete(self.aembed(text))

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return asyncio.get_event_loop().run_until_complete(self.aembed_batch(texts))

    async def aembed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.url,
                json={"model": self.model_name, "input": text, "dimensions": 1536}
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]

    async def aembed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed with chunking to avoid timeout on large batches."""
        all_embeddings = []
        batch_size = 16  # process 16 at a time

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.url,
                    json={"model": self.model_name, "input": batch, "dimensions": 1536}
                )
                response.raise_for_status()
                data = response.json()["data"]
                # Sort by index to maintain order
                data.sort(key=lambda x: x["index"])
                batch_embeddings = [d["embedding"] for d in data]
                all_embeddings.extend(batch_embeddings)
            logger.info(f"Embedded batch {i//batch_size + 1} ({len(batch)} texts)")

        return all_embeddings


# Singleton
embedder = EmbeddingModel.get_instance()