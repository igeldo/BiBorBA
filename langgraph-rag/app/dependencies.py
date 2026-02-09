"""
Central dependency injection configuration.

All services are created here. Routes only import from this module.

Usage:
    from app.dependencies import get_graph_service, get_embedding_service

    @router.post("/query")
    async def query(
        graph_service: GraphService = Depends(get_graph_service)
    ):
        ...
"""
from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

if TYPE_CHECKING:
    from app.core.model_manager import ModelManager
    from app.core.prompts import PromptManager
    from app.config import Settings
    from app.evaluation.bert_evaluation import BERTEvaluationService
    from app.evaluation.evaluation_service import EvaluationService
    from app.evaluation.llm_correctness_service import LLMCorrectnessService
    from app.services.embedding_service import EmbeddingService
    from app.services.stackoverflow_connector import StackOverflowConnector
    from app.services.collection_manager import CollectionManager
    from app.services.graph_service import GraphService
    from app.services.collection_health_service import CollectionHealthService
    from app.services.batch_query_service import BatchQueryService
    from app.core.graph.tools.vector_store import VectorStoreService



@lru_cache()
def get_model_manager() -> "ModelManager":
    """Singleton - loads expensive ML models."""
    from app.core.model_manager import ModelManager
    return ModelManager()


@lru_cache()
def get_prompt_manager() -> "PromptManager":
    """Singleton - read-only prompt templates."""
    from app.core.prompts import PromptManager
    return PromptManager()


@lru_cache()
def get_settings() -> "Settings":
    """Singleton - configuration from environment."""
    from app.config import Settings
    return Settings()


@lru_cache()
def get_bert_service() -> "BERTEvaluationService":
    """Singleton - loads expensive BERT model."""
    from app.evaluation.bert_evaluation import BERTEvaluationService
    return BERTEvaluationService()


def get_bert_evaluation_service() -> "BERTEvaluationService":
    """Alias for get_bert_service."""
    return get_bert_service()


@lru_cache()
def get_llm_correctness_service() -> "LLMCorrectnessService":
    """Singleton - LLM-as-Judge for correctness evaluation."""
    from app.evaluation.llm_correctness_service import LLMCorrectnessService
    return LLMCorrectnessService(
        model_manager=get_model_manager(),
        prompt_manager=get_prompt_manager()
    )



@lru_cache()
def get_embedding_service() -> "EmbeddingService":
    """Singleton - uses ModelManager for embeddings."""
    from app.services.embedding_service import EmbeddingService
    return EmbeddingService(model_manager=get_model_manager())


def get_stackoverflow_connector(
    db: Session = Depends(get_db)
) -> "StackOverflowConnector":
    """Factory - DB access for StackOverflow data."""
    from app.services.stackoverflow_connector import StackOverflowConnector
    return StackOverflowConnector(db=db)


def get_collection_manager(
    db: Session = Depends(get_db)
) -> "CollectionManager":
    """Factory - manages custom collections."""
    from app.services.collection_manager import CollectionManager
    return CollectionManager(db=db)



def get_graph_service() -> "GraphService":
    """Factory - graph execution."""
    from app.services.graph_service import GraphService
    return GraphService()


def get_evaluation_service() -> "EvaluationService":
    """Factory - evaluation service with BERT."""
    from app.evaluation.evaluation_service import EvaluationService
    return EvaluationService()


def get_collection_health_service() -> "CollectionHealthService":
    """Factory - collection health check."""
    from app.services.collection_health_service import CollectionHealthService
    return CollectionHealthService()


def get_vector_store_service() -> "VectorStoreService":
    """Factory - vector store operations."""
    from app.core.graph.tools.vector_store import VectorStoreService
    return VectorStoreService()


def get_batch_query_service() -> "BatchQueryService":
    """Factory - batch query service."""
    from app.services.batch_query_service import BatchQueryService
    return BatchQueryService()



def clear_all_caches():
    """Clear singleton caches for tests."""
    get_model_manager.cache_clear()
    get_prompt_manager.cache_clear()
    get_settings.cache_clear()
    get_bert_service.cache_clear()
    get_embedding_service.cache_clear()
    get_llm_correctness_service.cache_clear()
