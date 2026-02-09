"""
Service for collection health checks.
Validates whether Chroma collections exist for DB entries.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import CollectionConfiguration
from app.dependencies import get_embedding_service

logger = logging.getLogger(__name__)


class CollectionHealthService:
    """Service for validating collections"""

    def __init__(self):
        self.embedding_service = get_embedding_service()

    def check_collection_health(self, collection_id: int, db: Session) -> Dict[str, Any]:
        """
        Check if Chroma collection exists for DB entry

        Args:
            collection_id: Collection ID
            db: Database session

        Returns:
            Dict mit 'exists', 'needs_rebuild', 'document_count'
        """
        collection = db.query(CollectionConfiguration).filter(
            CollectionConfiguration.id == collection_id
        ).first()

        if not collection:
            return {"exists": False, "needs_rebuild": True, "document_count": 0}

        collection_name = f"custom_collection_{collection_id}"

        try:
            info = self.embedding_service.get_collection_info(collection_name)

            if info and info.get("document_count", 0) > 0:
                return {
                    "exists": True,
                    "needs_rebuild": False,
                    "document_count": info.get("document_count", 0)
                }
            else:
                return {
                    "exists": False,
                    "needs_rebuild": True,
                    "document_count": 0
                }
        except Exception as e:
            logger.warning(f"Error checking collection {collection_id}: {e}")
            return {
                "exists": False,
                "needs_rebuild": True,
                "document_count": 0,
                "error": str(e)
            }

    def check_all_collections(self, db: Session) -> Dict[str, Any]:
        """
        Check all collections at app startup (lightweight)

        Returns:
            Summary mit total, healthy, needs_rebuild
        """
        collections = db.query(CollectionConfiguration).all()

        summary = {
            "total": len(collections),
            "healthy": 0,
            "needs_rebuild": 0,
            "checked_at": datetime.utcnow().isoformat()
        }

        for collection in collections:
            health = self.check_collection_health(collection.id, db)

            collection.chroma_exists = health["exists"]
            collection.needs_rebuild = health["needs_rebuild"]
            collection.last_health_check = datetime.utcnow()

            if health["exists"]:
                summary["healthy"] += 1
            else:
                summary["needs_rebuild"] += 1
                logger.warning(
                    f"Collection '{collection.name}' (ID: {collection.id}) "
                    f"missing in Chroma - needs rebuild"
                )

        db.commit()
        return summary
