# core/graph/tools/document_loaders/pdf_collection_loader.py
"""
PDF Collection Document Loader
Loads PDF documents from a custom collection
"""

import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from app.config import settings
from .base_loader import BaseDocumentLoader
from .pdf_loader import PDFDocumentLoader

logger = logging.getLogger(__name__)


class PDFCollectionDocumentLoader(BaseDocumentLoader):
    """Loads PDF documents from a custom collection"""

    def __init__(self, collection_id: int):
        super().__init__()
        self.collection_id = collection_id
        self._db_session = None
        self.collection_manager = None
        self._init_services()
        self.pdf_loader = PDFDocumentLoader()

    def _init_services(self):
        """Initialize services with own database session"""
        from app.database import SessionLocal
        from app.services.collection_manager import CollectionManager

        self._db_session = SessionLocal()
        self.collection_manager = CollectionManager(db=self._db_session)

    def close(self):
        """Close the database session"""
        if self._db_session:
            self._db_session.close()
            self._db_session = None

    def load_documents(self) -> List[Document]:
        """Load PDF documents from the collection"""

        try:
            # Verify collection exists
            collection = self.collection_manager.get_collection(self.collection_id)
            if not collection:
                logger.error(f"Collection {self.collection_id} not found")
                return []

            if collection.collection_type != "pdf":
                logger.error(f"Collection {self.collection_id} is not a PDF collection (type: {collection.collection_type})")
                return []

            logger.info(f"Loading PDF documents for collection '{collection.name}' (ID: {self.collection_id})")

            # Get all document paths in this collection
            result = self.collection_manager.get_collection_documents(
                collection_id=self.collection_id,
                page=1,
                page_size=1000  # Load all documents
            )

            collection_docs = result.get("documents", [])

            if not collection_docs:
                logger.warning(f"No documents in PDF collection {self.collection_id}")
                return []

            logger.info(f"Found {len(collection_docs)} PDF documents in collection")

            all_documents = []

            # Load each PDF document
            for col_doc in collection_docs:
                try:
                    # Construct full path
                    pdf_path = Path(settings.pdf_path) / col_doc.document_path

                    if not pdf_path.exists():
                        logger.warning(f"PDF file not found: {pdf_path}, skipping")
                        continue

                    logger.info(f"Loading PDF: {col_doc.document_name}")

                    # Load PDF using existing PDFDocumentLoader
                    docs = self.pdf_loader._load_single_pdf(pdf_path)

                    # Add collection metadata to each document
                    for doc in docs:
                        if not hasattr(doc, 'metadata') or doc.metadata is None:
                            doc.metadata = {}

                        doc.metadata["collection_id"] = self.collection_id
                        doc.metadata["collection_name"] = collection.name
                        doc.metadata["source_type"] = "pdf_collection"
                        doc.metadata["document_name"] = col_doc.document_name
                        doc.metadata["document_path"] = col_doc.document_path
                        doc.metadata["source"] = str(pdf_path)

                    all_documents.extend(docs)
                    logger.info(f"Loaded {len(docs)} pages from {col_doc.document_name}")

                except Exception as e:
                    logger.error(f"Error loading PDF {col_doc.document_name}: {e}")
                    # Continue with other documents

            logger.info(f"Loaded total of {len(all_documents)} pages from {len(collection_docs)} PDF documents")

            # Validate documents
            all_documents = self.validate_documents(all_documents)

            # Split documents
            all_documents = self.split_documents(all_documents)

            # Log statistics
            stats = self.get_stats(all_documents)
            logger.info(f"PDF collection loading complete: {stats}")

            return all_documents

        except Exception as e:
            logger.error(f"Error loading documents for PDF collection {self.collection_id}: {e}")
            return []

    def get_collection_info(self):
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
