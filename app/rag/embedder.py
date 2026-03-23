from sentence_transformers import SentenceTransformer
from app.config import settings
import asyncio

class EmbeddingModel:
    _instance = None

    def __init__(self):
        print(f"Loading embedding model: {settings.embedding_model}")
        self.model = SentenceTransformer(settings.embedding_model)
        self.dimension = 384  # all-MiniLM-L6-v2 output size
        print("Embedding model loaded ✅")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed(self, text: str) -> list[float]:
        return self.model.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            texts, normalize_embeddings=True, batch_size=32
        ).tolist()

    async def aembed(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed, text)

    async def aembed_batch(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_batch, texts)

# Singleton — load once, reuse everywhere
embedder = EmbeddingModel.get_instance()