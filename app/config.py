from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    embedding_model: str = "qwen3-embedding"
    secret_key: str = "0cca648a49fe25f736c43770fb86fa61421bb1b2ec871464554466ec317dac45"
    groq_api_key: str = ""

    # AMD instance
    amd_llm_url: str = "http://165.245.136.218:8000"
    amd_embedding_url: str = "http://129.212.183.140:8000"
    embedding_dim: int = 1536
    
    # amd_reranker_url: str = "http://165.245.136.218:8002"


    class Config:
        env_file = ".env"

settings = Settings()

