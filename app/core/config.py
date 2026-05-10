from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GEMINI_API_KEY: str
    FAISS_INDEX_DIR: str = "faiss_index"
    UPLOAD_DIR: str = "uploads"
    
    # AI Provider Settings
    AI_PROVIDER: str = "gemini" # 'gemini' or 'ollama'
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen3.5:9b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
