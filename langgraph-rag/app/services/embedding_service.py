# services/embedding_service.py
import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING, Callable

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import settings
from app.database import SessionLocal, DocumentEmbedding
from app.utils.timing import TimingContext

if TYPE_CHECKING:
    from app.core.model_manager import ModelManager

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for managing document embeddings and vector stores

    Args:
        model_manager: ModelManager instance for embeddings model access.
    """

    def __init__(self, model_manager: "ModelManager"):
        self.model_manager = model_manager
        self._vector_stores: Dict[str, Chroma] = {}

    def get_or_create_vector_store(
            self,
            collection_name: str,
            documents: Optional[List[Document]] = None,
            force_rebuild: bool = False,
            batch_size: int = None,
            progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Chroma:
        """Get existing vector store or create new one

        Args:
            collection_name: Name of the collection
            documents: Documents to embed (required for new collections)
            force_rebuild: Force rebuild even if collection exists
            batch_size: Number of documents to embed per batch (uses settings.embedding_batch_size if None)
            progress_callback: Optional callback to report embedding progress
        """
        if batch_size is None:
            batch_size = settings.embedding_batch_size

        if collection_name in self._vector_stores and not force_rebuild:
            logger.info(f"Reusing cached vector store: {collection_name}")
            return self._vector_stores[collection_name]

        persist_dir = settings.chroma_persist_dir
        persist_dir.mkdir(parents=True, exist_ok=True)

        with TimingContext("Get embeddings model", logger):
            embeddings = self.model_manager.get_embeddings_model()

        # Check if collection exists on disk
        with TimingContext(f"Check if collection '{collection_name}' exists on disk", logger):
            collection_exists = self._collection_exists_on_disk(persist_dir, collection_name)

        if force_rebuild or not collection_exists:
            if documents is None:
                raise ValueError("Documents required for new vector store creation")

            logger.info(f"Creating new vector store: {collection_name}")

            # Delete existing collection if force rebuild
            if force_rebuild and collection_exists:
                with TimingContext(f"Delete existing collection '{collection_name}'", logger):
                    self._delete_collection(persist_dir, collection_name, embeddings)

            # Create new vector store with batched embedding
            with TimingContext(f"Create embeddings for {len(documents)} documents", logger):
                vector_store = self._create_vector_store_batched(
                    documents=documents,
                    collection_name=collection_name,
                    embeddings=embeddings,
                    persist_dir=persist_dir,
                    batch_size=batch_size,
                    progress_callback=progress_callback
                )

            # Track in database
            with TimingContext("Track embedding creation in database", logger):
                self._track_embedding_creation(collection_name, documents)

        else:
            logger.info(f"Loading existing vector store: {collection_name}")
            with TimingContext(f"Load existing vector store '{collection_name}'", logger):
                vector_store = Chroma(
                    collection_name=collection_name,
                    persist_directory=str(persist_dir),
                    embedding_function=embeddings
                )

            # Update last used timestamp
            with TimingContext("Update last used timestamp in database", logger):
                self._update_last_used(collection_name)

        # Cache the vector store
        self._vector_stores[collection_name] = vector_store
        return vector_store

    def _collection_exists_on_disk(self, persist_dir: Path, collection_name: str) -> bool:
        """Check if ChromaDB collection exists on disk"""
        try:
            chroma_sqlite = persist_dir / "chroma.sqlite3"
            if not chroma_sqlite.exists():
                return False

            embeddings = self.model_manager.get_embeddings_model()
            vector_store = Chroma(
                collection_name=collection_name,
                persist_directory=str(persist_dir),
                embedding_function=embeddings
            )

            # Try to get collection count
            collection_count = vector_store._collection.count()
            logger.info(f"Collection '{collection_name}' has {collection_count} documents")

            return collection_count > 0

        except Exception as e:
            logger.warning(f"Error checking collection existence: {e}")
            return False

    def _delete_collection(self, persist_dir: Path, collection_name: str, embeddings):
        """Delete existing collection"""
        try:
            old_vector_store = Chroma(
                collection_name=collection_name,
                persist_directory=str(persist_dir),
                embedding_function=embeddings
            )
            old_vector_store.delete_collection()
            logger.info(f"Deleted existing collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Error deleting collection: {e}")

    def _create_vector_store_batched(
        self,
        documents: List[Document],
        collection_name: str,
        embeddings,
        persist_dir: Path,
        batch_size: int = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Chroma:
        """
        Create vector store with batched embedding to avoid context length errors

        Args:
            documents: Documents to embed
            collection_name: Name of the collection
            embeddings: Embedding function
            persist_dir: Directory to persist the vector store
            batch_size: Number of documents to process per batch
            progress_callback: Optional callback to report progress

        Returns:
            Chroma vector store with all documents
        """
        if batch_size is None:
            batch_size = settings.embedding_batch_size

        total_docs = len(documents)
        total_batches = max(1, (total_docs + batch_size - 1) // batch_size)

        def report_progress(current_batch: int, processed_docs: int):
            """Report progress via callback if provided"""
            if progress_callback:
                progress_callback({
                    "current_batch": current_batch,
                    "total_batches": total_batches,
                    "processed_documents": processed_docs,
                    "total_documents": total_docs,
                    "phase": "embedding"
                })

        # Report initial progress
        report_progress(0, 0)

        if total_docs <= batch_size:
            # Small enough to process in one go
            logger.info(f"Processing {total_docs} documents in single batch")
            result = Chroma.from_documents(
                documents=documents,
                collection_name=collection_name,
                embedding=embeddings,
                persist_directory=str(persist_dir)
            )
            report_progress(1, total_docs)
            return result

        # Process in batches
        logger.info(f"Processing {total_docs} documents in batches of {batch_size}")

        # Create initial vector store with first batch
        first_batch = documents[:batch_size]
        logger.info(f"Creating vector store with first batch (0-{batch_size})")

        vector_store = Chroma.from_documents(
            documents=first_batch,
            collection_name=collection_name,
            embedding=embeddings,
            persist_directory=str(persist_dir)
        )
        report_progress(1, batch_size)

        # Add remaining documents in batches
        batch_num = 1
        for i in range(batch_size, total_docs, batch_size):
            batch_num += 1
            batch_end = min(i + batch_size, total_docs)
            batch = documents[i:batch_end]

            logger.info(f"Adding batch {batch_num}: documents {i}-{batch_end} ({len(batch)} docs)")

            try:
                vector_store.add_documents(batch)
                report_progress(batch_num, batch_end)
            except Exception as e:
                logger.error(f"Error adding batch {batch_num}: {e}")
                # Try with smaller batch size on error
                fallback_size = settings.embedding_fallback_batch_size
                if len(batch) > fallback_size:
                    logger.info(f"Retrying with smaller sub-batches (size {fallback_size})")
                    for j in range(0, len(batch), fallback_size):
                        sub_batch = batch[j:min(j + fallback_size, len(batch))]
                        try:
                            vector_store.add_documents(sub_batch)
                            logger.info(f"Successfully added sub-batch {j//fallback_size + 1}")
                        except Exception as sub_e:
                            logger.error(f"Failed to add sub-batch: {sub_e}")
                            raise
                    # Report progress after fallback processing
                    report_progress(batch_num, batch_end)
                else:
                    raise

        logger.info(f"Successfully created vector store with {total_docs} documents in batches")
        return vector_store

    def _track_embedding_creation(self, collection_name: str, documents: List[Document]):
        """Track embedding creation in database"""
        db = SessionLocal()
        try:
            # Calculate document hash for tracking
            doc_content = "\n".join([doc.page_content for doc in documents])
            doc_hash = hashlib.sha256(doc_content.encode()).hexdigest()

            # Get embedding model name
            embedding_model = settings.ollama_models.get("embedding", "unknown")

            # Check if embedding already tracked
            existing = db.query(DocumentEmbedding).filter(
                DocumentEmbedding.document_hash == doc_hash
            ).first()

            if existing:
                existing.last_used = datetime.utcnow()
                existing.document_count = len(documents)
            else:
                embedding_record = DocumentEmbedding(
                    document_source=collection_name,
                    document_hash=doc_hash,
                    embedding_model=embedding_model,
                    vector_store_id=collection_name,
                    document_count=len(documents)
                )
                db.add(embedding_record)

            db.commit()
            logger.info(f"Tracked embedding creation for {len(documents)} documents")

        except Exception as e:
            logger.error(f"Error tracking embedding creation: {e}")
        finally:
            db.close()

    def _update_last_used(self, collection_name: str):
        """Update last used timestamp for collection"""
        db = SessionLocal()
        try:
            embedding_record = db.query(DocumentEmbedding).filter(
                DocumentEmbedding.vector_store_id == collection_name
            ).first()

            if embedding_record:
                embedding_record.last_used = datetime.utcnow()
                db.commit()

        except Exception as e:
            logger.error(f"Error updating last used timestamp: {e}")
        finally:
            db.close()

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a collection"""
        try:
            vector_store = self._vector_stores.get(collection_name)
            if not vector_store:
                # Try to load it
                persist_dir = settings.chroma_persist_dir
                embeddings = self.model_manager.get_embeddings_model()
                vector_store = Chroma(
                    collection_name=collection_name,
                    persist_directory=str(persist_dir),
                    embedding_function=embeddings
                )

            collection_count = vector_store._collection.count()

            # Get database info
            db = SessionLocal()
            try:
                db_record = db.query(DocumentEmbedding).filter(
                    DocumentEmbedding.vector_store_id == collection_name
                ).first()

                return {
                    "collection_name": collection_name,
                    "document_count": collection_count,
                    "embedding_model": db_record.embedding_model if db_record else "unknown",
                    "created_at": db_record.created_at if db_record else None,
                    "last_used": db_record.last_used if db_record else None
                }
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return None

    def list_collections(self) -> List[Dict[str, Any]]:
        """List all available collections"""
        collections = []

        db = SessionLocal()
        try:
            records = db.query(DocumentEmbedding).all()

            for record in records:
                info = self.get_collection_info(record.vector_store_id)
                if info:
                    collections.append(info)

        except Exception as e:
            logger.error(f"Error listing collections: {e}")
        finally:
            db.close()

        return collections

    def cleanup_unused_collections(self, days_threshold: int = 30):
        """Clean up collections not used for specified days"""
        from datetime import timedelta

        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)

        db = SessionLocal()
        try:
            old_records = db.query(DocumentEmbedding).filter(
                DocumentEmbedding.last_used < threshold_date
            ).all()

            for record in old_records:
                try:
                    # Delete from ChromaDB
                    persist_dir = settings.chroma_persist_dir
                    embeddings = self.model_manager.get_embeddings_model()

                    vector_store = Chroma(
                        collection_name=record.vector_store_id,
                        persist_directory=str(persist_dir),
                        embedding_function=embeddings
                    )
                    vector_store.delete_collection()

                    # Remove from app.database
                    db.delete(record)

                    logger.info(f"Cleaned up old collection: {record.vector_store_id}")

                except Exception as e:
                    logger.error(f"Error cleaning up collection {record.vector_store_id}: {e}")

            db.commit()

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            db.close()


