"""Environment-based configuration. No hardcoded secrets."""
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# absolute paths anchored to the project root: correct no matter the CWD
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEMBER_ASSISTANT_", env_file=".env", extra="ignore")

    # service
    host: str = "0.0.0.0"
    port: int = 8001
    member_id_header: str = "X-Member-Id"
    version: str = "1.0.0"

    # paths (env can override, defaults are absolute)
    kb_dir: str = os.path.join(_PROJECT_ROOT, "data", "kb")
    index_dir: str = os.path.join(_PROJECT_ROOT, "data", "index")
    db_path: str = os.path.join(_PROJECT_ROOT, "data", "member.db")

    # rag
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    top_k: int = 4
    chunk_size: int = 500
    chunk_overlap: int = 100
    # cosine similarity below this => not confident, fall back to human
    confidence_threshold: float = 0.30

    # llm (OpenAI-compatible endpoint; point to the internal model in production)
    llm_base_url: str = "https://opencode.ai/zen/v1"
    llm_api_key: str = ""
    llm_model: str = "glm-5.3-flash-free"
    llm_timeout: int = 60
    llm_max_tool_rounds: int = 2


settings = Settings()
