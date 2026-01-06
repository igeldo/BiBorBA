# core/model_manager.py
import logging
from functools import lru_cache
from typing import Dict, Optional, Any

from langchain_ollama import ChatOllama

from app.config import settings
from app.core.batched_embeddings import BatchedOllamaEmbeddings

logger = logging.getLogger(__name__)


class ModelManager:
    """Centralized management of Ollama models"""

    def __init__(self):
        self._chat_models: Dict[str, ChatOllama] = {}
        self._embeddings_model: Optional[BatchedOllamaEmbeddings] = None

    def get_chat_model(self,
                       model_type: str = "chat",
                       temperature: float = 0.2,
                       **kwargs) -> ChatOllama:
        """Get a chat model instance"""

        if model_type not in settings.ollama_models:
            raise ValueError(f"Model type '{model_type}' not configured")

        model_name = settings.ollama_models[model_type]
        cache_key = f"{model_name}_{temperature}_{hash(str(kwargs))}"

        if cache_key not in self._chat_models:
            logger.info(f"Creating new chat model: {model_name}")
            self._chat_models[cache_key] = ChatOllama(
                model=model_name,
                base_url=settings.ollama_base_url,
                temperature=temperature,
                **kwargs
            )

        return self._chat_models[cache_key]

    def get_embeddings_model(self, batch_size: int = 10) -> BatchedOllamaEmbeddings:
        """Get embeddings model instance with batching support

        Args:
            batch_size: Number of documents to embed per batch (default: 10)
        """

        if self._embeddings_model is None:
            model_name = settings.ollama_models["embedding"]
            logger.info(f"Creating batched embeddings model: {model_name} (batch_size={batch_size})")
            self._embeddings_model = BatchedOllamaEmbeddings(
                model=model_name,
                base_url=settings.ollama_base_url,
                batch_size=batch_size
            )

        return self._embeddings_model

    def get_structured_model(self,
                             model_type: str = "grader",
                             output_schema: Any = None,
                             **kwargs) -> ChatOllama:
        """Get a model with structured output"""

        base_model = self.get_chat_model(model_type, **kwargs)

        if output_schema:
            return base_model.with_structured_output(output_schema)

        return base_model

    def list_available_models(self) -> Dict[str, str]:
        """List all configured models"""
        return settings.ollama_models.copy()

    def health_check(self) -> Dict[str, bool]:
        """Check if all models are accessible"""
        health_status = {}

        for model_type, model_name in settings.ollama_models.items():
            try:
                if model_type == "embedding":
                    model = self.get_embeddings_model()
                    # Simple test embedding
                    model.embed_query("test")
                else:
                    model = self.get_chat_model(model_type)
                    # Simple test message
                    model.invoke("Hello")

                health_status[f"{model_type}_{model_name}"] = True
                logger.info(f"Model {model_name} is healthy")

            except Exception as e:
                health_status[f"{model_type}_{model_name}"] = False
                logger.error(f"Model {model_name} health check failed: {e}")

        return health_status


@lru_cache()
def get_model_manager() -> ModelManager:
    """Dependency for accessing model manager (cached singleton)"""
    return ModelManager()