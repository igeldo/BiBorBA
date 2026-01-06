"""
Zentrale Dependency Injection Konfiguration

Alle Services werden hier erstellt. Routes importieren nur von hier.

Verwendung:
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
    from app.services.embedding_service import EmbeddingService
    from app.services.stackoverflow_connector import StackOverflowConnector
    from app.services.collection_manager import CollectionManager
    from app.services.graph_service import GraphService
    from app.services.collection_health_service import CollectionHealthService
    from app.services.batch_query_service import BatchQueryService
    from app.core.graph.tools.vector_store import VectorStoreService


# =============================================================================
# Application-Scoped Singletons (teure Ressourcen, stateless)
# =============================================================================

@lru_cache()
def get_model_manager() -> "ModelManager":
    """Singleton - lädt teure ML-Modelle."""
    from app.core.model_manager import ModelManager
    return ModelManager()


@lru_cache()
def get_prompt_manager() -> "PromptManager":
    """Singleton - read-only Prompt-Templates."""
    from app.core.prompts import PromptManager
    return PromptManager()


@lru_cache()
def get_settings() -> "Settings":
    """Singleton - Konfiguration aus Environment."""
    from app.config import Settings
    return Settings()


@lru_cache()
def get_bert_service() -> "BERTEvaluationService":
    """Singleton - lädt teures BERT-Modell."""
    from app.evaluation.bert_evaluation import BERTEvaluationService
    return BERTEvaluationService()


# Alias für Konsistenz
def get_bert_evaluation_service() -> "BERTEvaluationService":
    """Alias für get_bert_service."""
    return get_bert_service()


# =============================================================================
# Request-Scoped Services (mit DB-Session)
# =============================================================================

@lru_cache()
def get_embedding_service() -> "EmbeddingService":
    """Singleton - nutzt ModelManager für Embeddings."""
    from app.services.embedding_service import EmbeddingService
    return EmbeddingService(model_manager=get_model_manager())


def get_stackoverflow_connector(
    db: Session = Depends(get_db)
) -> "StackOverflowConnector":
    """Factory - DB-Zugriff für StackOverflow-Daten."""
    from app.services.stackoverflow_connector import StackOverflowConnector
    return StackOverflowConnector(db=db)


def get_collection_manager(
    db: Session = Depends(get_db)
) -> "CollectionManager":
    """Factory - verwaltet Custom Collections."""
    from app.services.collection_manager import CollectionManager
    return CollectionManager(db=db)


# =============================================================================
# Stateless Services (keine DB-Session nötig)
# =============================================================================

def get_graph_service() -> "GraphService":
    """Factory - Graph-Ausführung."""
    from app.services.graph_service import GraphService
    return GraphService()


def get_evaluation_service() -> "EvaluationService":
    """Factory - Evaluation Service mit BERT."""
    from app.evaluation.evaluation_service import EvaluationService
    return EvaluationService()


def get_collection_health_service() -> "CollectionHealthService":
    """Factory - Collection Health Check."""
    from app.services.collection_health_service import CollectionHealthService
    return CollectionHealthService()


def get_vector_store_service() -> "VectorStoreService":
    """Factory - Vector Store Operations."""
    from app.core.graph.tools.vector_store import VectorStoreService
    return VectorStoreService()


def get_batch_query_service() -> "BatchQueryService":
    """Factory - Batch Query Service."""
    from app.services.batch_query_service import BatchQueryService
    return BatchQueryService()


# =============================================================================
# Hilfsfunktionen für Tests
# =============================================================================

def clear_all_caches():
    """Leert Singleton-Caches für Tests."""
    get_model_manager.cache_clear()
    get_prompt_manager.cache_clear()
    get_settings.cache_clear()
    get_bert_service.cache_clear()
    get_embedding_service.cache_clear()
