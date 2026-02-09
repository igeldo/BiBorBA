"""
StackOverflow Document Loader
Specialized for StackOverflow Q&A data
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document

from app.config import settings
from .base_loader import BaseDocumentLoader

logger = logging.getLogger(__name__)


class StackOverflowDocumentLoader(BaseDocumentLoader):
    """Specialized loader for StackOverflow documents"""

    def __init__(self):
        super().__init__()
        self.connector = None
        self.stackoverflow_separators = [
            "\n\nAntwort:",
            "\n\nFrage:",
            "\n\n",
            "\n",
            " ",
            ""
        ]

    def load_documents(self, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Load documents from StackOverflow database"""

        connector = self._get_stackoverflow_connector()
        if connector is None:
            logger.error("StackOverflow connector not available")
            return []

        default_filters = {
            "limit": 200,
            "min_score": 1,
            "tags": ["sql", "mysql", "postgresql", "database"],
            "only_accepted_answers": False
        }

        if hasattr(settings, 'stackoverflow_default_filters'):
            default_filters.update(settings.stackoverflow_default_filters)

        if filters:
            default_filters.update(filters)

        logger.info(f"Loading StackOverflow documents with filters: {default_filters}")

        try:
            qa_pairs = connector.get_questions_with_answers(**default_filters)

            if not qa_pairs:
                logger.warning("No StackOverflow Q&A pairs found")
                return []

            documents = connector.convert_to_documents(
                qa_pairs=qa_pairs,
                include_answers=True,
                combine_qa=True
            )

            logger.info(f"Loaded {len(documents)} StackOverflow documents")

            documents = self._process_stackoverflow_metadata(documents)
            documents = self.validate_documents(documents)

            return self.split_documents(documents, custom_separators=self.stackoverflow_separators)

        except Exception as e:
            logger.error(f"Error loading StackOverflow documents: {e}")
            return []

    def _get_stackoverflow_connector(self):
        """Lazy loading of StackOverflow connector with own session"""
        if self.connector is None:
            try:
                from app.database import SessionLocal
                from app.services.stackoverflow_connector import StackOverflowConnector

                self._db_session = SessionLocal()
                self.connector = StackOverflowConnector(db=self._db_session)
                logger.info("StackOverflow connector initialized")

            except Exception as e:
                logger.warning(f"StackOverflow connector initialization failed: {e}")
                self.connector = None

        return self.connector

    def close(self):
        """Close the connector's database session"""
        if hasattr(self, '_db_session') and self._db_session:
            self._db_session.close()
            self._db_session = None
            self.connector = None

    def _process_stackoverflow_metadata(self, documents: List[Document]) -> List[Document]:
        """Process and enrich StackOverflow-specific metadata"""
        processed_docs = []

        for doc in documents:
            if not hasattr(doc, 'metadata') or doc.metadata is None:
                doc.metadata = {}

            doc.metadata.update({
                "document_type": "stackoverflow_qa",
                "source_type": "community_knowledge",
                "is_community_validated": self._is_community_validated(doc.metadata),
                "quality_score": self._calculate_quality_score(doc.metadata)
            })

            if "tags" in doc.metadata and isinstance(doc.metadata["tags"], list):
                doc.metadata["primary_tag"] = doc.metadata["tags"][0] if doc.metadata["tags"] else None
                doc.metadata["tag_count"] = len(doc.metadata["tags"])

            processed_docs.append(doc)

        return processed_docs

    def _is_community_validated(self, metadata: Dict[str, Any]) -> bool:
        """Check if the Q&A is community validated"""

        is_accepted = metadata.get("is_accepted_answer", False)
        question_score = metadata.get("question_score", 0)
        answer_score = metadata.get("answer_score", 0)

        return is_accepted or (question_score > 0 and answer_score > 0)

    def _calculate_quality_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate quality score for StackOverflow content"""
        score = 0.0

        score += 0.3

        question_score = metadata.get("question_score", 0)
        score += min(question_score * 0.05, 0.3)

        answer_score = metadata.get("answer_score", 0)
        score += min(answer_score * 0.05, 0.2)

        if metadata.get("is_accepted_answer", False):
            score += 0.2

        view_count = metadata.get("view_count", 0)
        if view_count > 100:
            score += min(view_count / 10000, 0.1)

        return min(score, 1.0)

