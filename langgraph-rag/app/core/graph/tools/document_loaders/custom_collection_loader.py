# core/graph/tools/document_loaders/custom_collection_loader.py
"""
Custom Collection Document Loader
Loads documents based on collection configuration
"""

import logging
from typing import List, Dict, Any

from langchain_core.documents import Document

from .base_loader import BaseDocumentLoader

logger = logging.getLogger(__name__)


class CustomCollectionDocumentLoader(BaseDocumentLoader):
    """Loads documents from a custom collection"""

    def __init__(self, collection_id: int):
        super().__init__()
        self.collection_id = collection_id
        self._db_session = None
        self.collection_manager = None
        self.connector = None
        self._init_services()

    def _init_services(self):
        """Initialize services with own database session"""
        from app.database import SessionLocal
        from app.services.collection_manager import CollectionManager
        from app.services.stackoverflow_connector import StackOverflowConnector

        self._db_session = SessionLocal()
        self.collection_manager = CollectionManager(db=self._db_session)
        self.connector = StackOverflowConnector(db=self._db_session)

        # StackOverflow-specific separators (same as StackOverflowDocumentLoader)
        self.stackoverflow_separators = [
            "\n\nAntwort:",  # Separator between question and answer
            "\n\nFrage:",  # Separator between different questions
            "\n\n",  # Paragraph breaks
            "\n",  # Line breaks
            " ",  # Word breaks
            ""  # Character breaks
        ]

    def close(self):
        """Close the database session"""
        if self._db_session:
            self._db_session.close()
            self._db_session = None

    def load_documents(self) -> List[Document]:
        """Load documents from the collection"""

        try:
            # Verify collection exists
            collection = self.collection_manager.get_collection(self.collection_id)
            if not collection:
                logger.error(f"Collection {self.collection_id} not found")
                return []

            logger.info(f"Loading documents for collection '{collection.name}' (ID: {self.collection_id})")

            # Get all question IDs in this collection
            question_ids = self.collection_manager.get_collection_question_ids(self.collection_id)

            if not question_ids:
                logger.warning(f"No questions in collection {self.collection_id}")
                return []

            logger.info(f"Found {len(question_ids)} questions in collection")

            # Load Q&A pairs from database
            qa_pairs = self.connector.get_questions_by_ids(question_ids)

            if not qa_pairs:
                logger.warning(f"No Q&A pairs found for collection {self.collection_id}")
                return []

            logger.info(f"Loaded {len(qa_pairs)} Q&A pairs from database")

            # Convert to LangChain Documents
            documents = self.connector.convert_to_documents(
                qa_pairs=qa_pairs,
                include_answers=True,
                combine_qa=True  # Combine question with best answer
            )

            logger.info(f"Created {len(documents)} LangChain documents")

            # Process metadata
            documents = self._process_collection_metadata(documents, collection.name)

            # Validate documents
            documents = self.validate_documents(documents)

            # Split documents
            documents = self.split_documents(documents, custom_separators=self.stackoverflow_separators)

            # Log statistics
            stats = self.get_stats(documents)
            logger.info(f"Collection loading complete: {stats}")

            return documents

        except Exception as e:
            logger.error(f"Error loading documents for collection {self.collection_id}: {e}")
            return []

    def _process_collection_metadata(self, documents: List[Document], collection_name: str) -> List[Document]:
        """
        Add collection-specific metadata to documents

        Args:
            documents: List of documents to process
            collection_name: Name of the collection

        Returns:
            Documents with updated metadata
        """
        for doc in documents:
            if not hasattr(doc, 'metadata') or doc.metadata is None:
                doc.metadata = {}

            # Add collection information
            doc.metadata["collection_id"] = self.collection_id
            doc.metadata["collection_name"] = collection_name
            doc.metadata["source_type"] = "custom_collection"

            # Add document type if not present
            if "document_type" not in doc.metadata:
                doc.metadata["document_type"] = "stackoverflow_qa"

        logger.info(f"Added collection metadata to {len(documents)} documents")
        return documents

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection

        Returns:
            Dict with collection information
        """
        try:
            collection = self.collection_manager.get_collection(self.collection_id)
            if not collection:
                return {}

            stats = self.collection_manager.get_collection_statistics(self.collection_id)
            return stats

        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}
