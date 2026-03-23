from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    llm_url: str = "http://localhost:8001"
    embedding_model: str = "all-MiniLM-L6-v2"
    secret_key: str = ""
    groq_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()