# config.py
from pathlib import Path
from typing import Dict, Any, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized configuration management"""

    # Database
    database_url: str = Field(default="sqlite:///../data/langgraph_rag.db")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_models: Dict[str, str] = Field(default={
        "embedding": "embeddinggemma:latest",
        "chat": "gemma3:12b",
        "grader": "gemma3:12b",
        "rewriter": "gemma3:12b"
    })

    # Paths
    chroma_persist_dir: Path = Field(default_factory=lambda: Path.cwd() / "data" / "chroma")
    pdf_path: Path = Field(default_factory=lambda: Path.cwd() / "resources" / "documents")

    # Text Processing
    chunk_size: int = Field(default=800)
    chunk_overlap: int = Field(default=100)
    max_pdf_size_mb: int = Field(default=100, description="Maximum PDF size in MB")

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=False)
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
        description="Allowed CORS origins"
    )

    # StackOverflow Filters
    stackoverflow_default_filters: Dict[str, Any] = Field(
        default={
            "min_score": 1,
            "tags": ["sql", "mysql", "postgresql", "database"],
            "only_accepted_answers": False,
            "limit": 200
        },
        description="Default filters for StackOverflow data loading"
    )

    # Graph Loop Protection
    max_generation_retries: int = Field(default=2, description="Max hallucination retries")
    max_transform_retries: int = Field(default=2, description="Max query transformations")
    max_total_iterations: int = Field(default=15, description="Max total graph iterations")
    graph_recursion_limit: int = Field(default=20, description="LangGraph recursion_limit")

    # Document Grading
    document_grading_batch_size: int = Field(default=4, description="Documents to grade in parallel (max 4)")
    document_grading_retry_attempts: int = Field(default=2, description="Max retry attempts for TCP errors")
    document_grading_confidence_threshold: float = Field(default=0.6, description="Min confidence for relevance")

    # Retry Variation
    enable_retry_variation: bool = Field(default=True, description="Increase temperature on retries")
    retry_temperature_increment: float = Field(default=0.1, description="Temperature increase per retry")

    # Retrieval
    retrieval_k: int = Field(default=4, description="Number of documents to retrieve")

    # Embedding
    embedding_batch_size: int = Field(default=50, description="Batch size for embedding operations")
    embedding_fallback_batch_size: int = Field(default=10, description="Fallback batch size on error")

    # Hallucination Grading
    hallucination_batch_size: int = Field(default=3, description="Batch size for hallucination check")

    @field_validator('pdf_path', 'chroma_persist_dir')
    @classmethod
    def resolve_paths(cls, v):
        """Resolve paths to absolute paths"""
        if isinstance(v, str):
            path = Path(v)
        else:
            path = v

        if not path.is_absolute():
            project_root = cls._find_project_root()
            path = project_root / path

        return path.resolve()

    @classmethod
    def _find_project_root(cls) -> Path:
        current = Path.cwd()

        for parent in [current] + list(current.parents):
            if (parent / ".env").exists():
                return parent

        return current

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency for FastAPI"""
    return settings
