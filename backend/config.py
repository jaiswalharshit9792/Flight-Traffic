from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "mariadb+mariadbconnector://flightuser:C0lumnStore!@mariadb:3306/flights"
    USE_LOCAL_MODELS: bool = True
    OLLAMA_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = 384
    ENVIRONMENT: str = "production"

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()
