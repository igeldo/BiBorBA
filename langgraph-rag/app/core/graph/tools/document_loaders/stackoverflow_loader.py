# core/graph/tools/document_loaders/stackoverflow_loader.py
"""
StackOverflow Document Loader
Spezialisiert auf StackOverflow Q&A Daten
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document

from app.config import settings
from .base_loader import BaseDocumentLoader

logger = logging.getLogger(__name__)


class StackOverflowDocumentLoader(BaseDocumentLoader):
    """Spezialisierter Loader für StackOverflow-Dokumente"""

    def __init__(self):
        super().__init__()
        self.connector = None
        # StackOverflow-spezifische Separatoren
        self.stackoverflow_separators = [
            "\n\nAntwort:",  # Trennung zwischen Frage und Antwort
            "\n\nFrage:",  # Trennung zwischen verschiedenen Fragen
            "\n\n",  # Paragraph breaks
            "\n",  # Line breaks
            " ",  # Word breaks
            ""  # Character breaks
        ]

    def load_documents(self, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Load documents from StackOverflow database"""

        connector = self._get_stackoverflow_connector()
        if connector is None:
            logger.error("StackOverflow connector not available")
            return []

        # Default filters
        default_filters = {
            "limit": 200,
            "min_score": 1,
            "tags": ["sql", "mysql", "postgresql", "database"],
            "only_accepted_answers": False
        }

        # Merge with settings and provided filters
        if hasattr(settings, 'stackoverflow_default_filters'):
            default_filters.update(settings.stackoverflow_default_filters)

        if filters:
            default_filters.update(filters)

        logger.info(f"Loading StackOverflow documents with filters: {default_filters}")

        try:
            # Q&A Paare aus DB laden
            qa_pairs = connector.get_questions_with_answers(**default_filters)

            if not qa_pairs:
                logger.warning("No StackOverflow Q&A pairs found")
                return []

            # Zu Document Objekten konvertieren
            documents = connector.convert_to_documents(
                qa_pairs=qa_pairs,
                include_answers=True,
                combine_qa=True  # Kombiniert Frage und beste Antwort
            )

            logger.info(f"Loaded {len(documents)} StackOverflow documents")

            # StackOverflow-spezifische Verarbeitung
            documents = self._process_stackoverflow_metadata(documents)
            documents = self.validate_documents(documents)

            # Splitting mit StackOverflow-spezifischen Separatoren
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

                # Create own session for the loader
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
            # Ensure metadata structure
            if not hasattr(doc, 'metadata') or doc.metadata is None:
                doc.metadata = {}

            # Add StackOverflow-specific processing
            doc.metadata.update({
                "document_type": "stackoverflow_qa",
                "source_type": "community_knowledge",
                "is_community_validated": self._is_community_validated(doc.metadata),
                "quality_score": self._calculate_quality_score(doc.metadata)
            })

            # Extract and structure tags
            if "tags" in doc.metadata and isinstance(doc.metadata["tags"], list):
                doc.metadata["primary_tag"] = doc.metadata["tags"][0] if doc.metadata["tags"] else None
                doc.metadata["tag_count"] = len(doc.metadata["tags"])

            processed_docs.append(doc)

        return processed_docs

    def _is_community_validated(self, metadata: Dict[str, Any]) -> bool:
        """Check if the Q&A is community validated"""
        # Consider validated if:
        # 1. Has accepted answer
        # 2. Question has positive score
        # 3. Answer has positive score

        is_accepted = metadata.get("is_accepted_answer", False)
        question_score = metadata.get("question_score", 0)
        answer_score = metadata.get("answer_score", 0)

        return is_accepted or (question_score > 0 and answer_score > 0)

    def _calculate_quality_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate quality score for StackOverflow content"""
        score = 0.0

        # Base score
        score += 0.3

        # Question score contribution (normalized to 0-0.3)
        question_score = metadata.get("question_score", 0)
        score += min(question_score * 0.05, 0.3)

        # Answer score contribution (normalized to 0-0.2)
        answer_score = metadata.get("answer_score", 0)
        score += min(answer_score * 0.05, 0.2)

        # Accepted answer bonus
        if metadata.get("is_accepted_answer", False):
            score += 0.2

        # View count consideration (normalized)
        view_count = metadata.get("view_count", 0)
        if view_count > 100:
            score += min(view_count / 10000, 0.1)  # Max 0.1 bonus

        return min(score, 1.0)  # Cap at 1.0

    def get_statistics(self) -> Optional[Dict[str, Any]]:
        """Get statistics about StackOverflow data"""
        connector = self._get_stackoverflow_connector()
        if connector is None:
            return None

        try:
            # Sample für Statistiken
            qa_pairs = connector.get_questions_with_answers(limit=1000)

            if not qa_pairs:
                return {"error": "No StackOverflow data available"}

            # Berechne Statistiken
            total_questions = len(qa_pairs)
            total_answers = sum(len(qa["answers"]) for qa in qa_pairs)
            avg_question_score = sum(qa["score"] for qa in qa_pairs) / total_questions if qa_pairs else 0

            answer_scores = []
            for qa in qa_pairs:
                answer_scores.extend([answer["score"] for answer in qa["answers"]])

            avg_answer_score = sum(answer_scores) / len(answer_scores) if answer_scores else 0

            # Most common tags
            all_tags = []
            for qa in qa_pairs:
                all_tags.extend(qa["tags"])

            from collections import Counter
            tag_counts = Counter(all_tags)
            most_common_tags = [tag for tag, count in tag_counts.most_common(10)]

            return {
                "total_questions": total_questions,
                "total_answers": total_answers,
                "avg_question_score": round(avg_question_score, 2),
                "avg_answer_score": round(avg_answer_score, 2),
                "most_common_tags": most_common_tags,
                "sample_size": total_questions
            }

        except Exception as e:
            logger.error(f"Error getting StackOverflow stats: {e}")
            return {"error": str(e)}

    def search_direct(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Direct search in StackOverflow database (not vector search)"""
        connector = self._get_stackoverflow_connector()
        if connector is None:
            return []

        return connector.search_questions(query, limit=limit, min_score=1)

    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """Get specific StackOverflow question with answers"""
        connector = self._get_stackoverflow_connector()
        if connector is None:
            return None

        return connector.get_question_by_id(question_id)

    def filter_by_tags(self, documents: List[Document], tags: List[str]) -> List[Document]:
        """Filter documents by specific tags"""
        if not tags:
            return documents

        filtered_docs = []
        for doc in documents:
            doc_tags = doc.metadata.get("tags", [])
            if isinstance(doc_tags, str):
                doc_tags = [tag.strip() for tag in doc_tags.split(",")]

            # Check if any of the requested tags match
            if any(tag.lower() in [t.lower() for t in doc_tags] for tag in tags):
                filtered_docs.append(doc)

        logger.info(f"Filtered {len(documents)} documents to {len(filtered_docs)} by tags: {tags}")
        return filtered_docs

    def filter_by_score(self, documents: List[Document], min_score: int = 1) -> List[Document]:
        """Filter documents by minimum score"""
        filtered_docs = []

        for doc in documents:
            question_score = doc.metadata.get("question_score", 0)
            answer_score = doc.metadata.get("answer_score", 0)

            # Include if either question or answer meets minimum score
            if question_score >= min_score or answer_score >= min_score:
                filtered_docs.append(doc)

        logger.info(f"Filtered {len(documents)} documents to {len(filtered_docs)} by min score: {min_score}")
        return filtered_docs