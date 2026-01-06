# app/api/routes/collections.py
"""
Collection Management Endpoints
- List Collections
- Rebuild Collections
"""

import logging

from fastapi import APIRouter, Depends, BackgroundTasks

from app.api.schemas.schemas import RetrieverType
from app.config import settings
from app.dependencies import get_vector_store_service

router = APIRouter(prefix="/collections", tags=["Collections"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_collections(
        vector_store_service=Depends(get_vector_store_service)
):
    """
    List all available document collections including StackOverflow

    Zeigt Statistiken für alle verfügbaren Collections (PDF, StackOverflow, etc.).
    """
    collections = {}

    for retriever_type in RetrieverType:
        try:
            stats = vector_store_service.get_document_stats(retriever_type)
            collections[retriever_type.value] = stats
        except Exception as e:
            logger.warning(f"Could not get stats for {retriever_type.value}: {e}")
            collections[retriever_type.value] = {"error": str(e)}

    return {
        "collections": collections
    }


@router.post("/{collection_type}/rebuild")
async def rebuild_collection(
        collection_type: RetrieverType,
        background_tasks: BackgroundTasks,
        vector_store_service=Depends(get_vector_store_service)
):
    """
    Rebuild a specific collection

    Baut eine Collection neu auf. Der Prozess läuft im Hintergrund.
    Unterstützt alle RetrieverTypes (PDF, STACKOVERFLOW, etc.).
    """

    def rebuild_task():
        try:
            result = vector_store_service.rebuild_collection(collection_type)
            logger.info(f"Collection {collection_type.value} rebuilt: {result}")
        except Exception as e:
            logger.error(f"Collection {collection_type.value} rebuild failed: {e}")

    background_tasks.add_task(rebuild_task)

    return {
        "message": f"Collection {collection_type.value} rebuild started",
        "status": "running"
    }