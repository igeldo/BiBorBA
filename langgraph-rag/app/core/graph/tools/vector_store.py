
import logging
from typing import List, Optional, Dict, Any, Callable

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from app.config import settings
from app.api.schemas.schemas import RetrieverType
from .document_loaders import PDFDocumentLoader, StackOverflowDocumentLoader

logger = logging.getLogger(__name__)


def _get_embedding_service():
    """Helper to get EmbeddingService with proper model_manager"""
    from app.dependencies import get_model_manager
    from app.services.embedding_service import EmbeddingService
    return EmbeddingService(model_manager=get_model_manager())


class VectorStoreService:
    """Vector Store Service mit Document Loader Pattern"""

    def __init__(self):
        self.embedding_service = _get_embedding_service()
        self._loaders = {
            RetrieverType.PDF: PDFDocumentLoader(),
            RetrieverType.STACKOVERFLOW: StackOverflowDocumentLoader()
        }

    def get_retriever(
            self,
            retriever_type: RetrieverType,
            force_rebuild: bool = False,
            search_kwargs: Optional[Dict[str, Any]] = None
    ) -> VectorStoreRetriever:
        """Get a retriever for the specified type"""

        collection_name = self._get_collection_name(retriever_type)

        documents = None
        if force_rebuild or not self._collection_exists(collection_name):
            documents = self._load_documents(retriever_type)
            logger.info(f"Loaded {len(documents)} documents for {retriever_type.value}")

        vector_store = self.embedding_service.get_or_create_vector_store(
            collection_name=collection_name,
            documents=documents,
            force_rebuild=force_rebuild
        )

        search_config = {
            "k": 5,
        }
        if search_kwargs:
            supported_params = ["k", "filter", "fetch_k"]
            search_config.update({k: v for k, v in search_kwargs.items() if k in supported_params})

        return vector_store.as_retriever(search_kwargs=search_config)

    def _get_collection_name(self, retriever_type: RetrieverType) -> str:
        """Generate collection name for retriever type"""
        return f"{retriever_type.value}_collection"

    def _collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists"""
        info = self.embedding_service.get_collection_info(collection_name)
        return info is not None and info.get("document_count", 0) > 0

    def _load_documents(self, retriever_type: RetrieverType) -> List[Document]:
        """Load documents using appropriate loader"""
        if retriever_type not in self._loaders:
            raise ValueError(f"Unsupported retriever type: {retriever_type}")

        loader = self._loaders[retriever_type]

        try:
            if retriever_type == RetrieverType.STACKOVERFLOW:
                filters = getattr(settings, 'stackoverflow_default_filters', {})
                documents = loader.load_documents(filters=filters)
            else:
                documents = loader.load_documents()

            logger.info(f"Loader {retriever_type.value} loaded {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"Error loading documents with {retriever_type.value} loader: {e}")
            raise



def get_custom_collection_retriever(
    collection_id: int,
    force_rebuild: bool = False,
    search_kwargs: Optional[Dict[str, Any]] = None
) -> VectorStoreRetriever:
    """
    Get a retriever for a custom collection

    Args:
        collection_id: ID of the collection configuration
        force_rebuild: Force rebuild the vector store
        search_kwargs: Optional search parameters

    Returns:
        VectorStoreRetriever for the custom collection
    """
    from app.database import SessionLocal
    from app.services.collection_manager import CollectionManager

    db = SessionLocal()
    try:
        collection_manager = CollectionManager(db=db)
        embedding_service = _get_embedding_service()

        collection = collection_manager.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        logger.info(f"Getting retriever for custom collection '{collection.name}' (ID: {collection_id})")

        collection_name = f"custom_collection_{collection_id}"

        collection_exists = False
        info = embedding_service.get_collection_info(collection_name)
        if info and info.get("document_count", 0) > 0:
            collection_exists = True

        documents = None
        if force_rebuild or not collection_exists:
            logger.info(f"Loading documents for collection {collection_id} (type: {collection.collection_type})")

            if collection.collection_type == "stackoverflow":
                from app.core.graph.tools.document_loaders.custom_collection_loader import CustomCollectionDocumentLoader
                loader = CustomCollectionDocumentLoader(collection_id)
            elif collection.collection_type == "pdf":
                from app.core.graph.tools.document_loaders.pdf_collection_loader import PDFCollectionDocumentLoader
                loader = PDFCollectionDocumentLoader(collection_id)
            else:
                raise ValueError(f"Unknown collection type: {collection.collection_type}")

            documents = loader.load_documents()

            if not documents:
                error_msg = f"No documents loaded for collection {collection_id} (type: {collection.collection_type})"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"Loaded {len(documents)} documents for collection '{collection.name}'")

        vector_store = embedding_service.get_or_create_vector_store(
            collection_name=collection_name,
            documents=documents,
            force_rebuild=force_rebuild
        )

        search_config = {
            "k": 5,
        }
        if search_kwargs:
            supported_params = ["k", "filter", "fetch_k"]
            search_config.update({k: v for k, v in search_kwargs.items() if k in supported_params})

        logger.info(f"Returning retriever for collection '{collection.name}' with search config: {search_config}")
        return vector_store.as_retriever(search_kwargs=search_config)
    finally:
        db.close()


def sync_collection_count(collection_id: int) -> int:
    """
    Synchronisiert question_count einer Collection mit der tatsächlichen Anzahl.

    Args:
        collection_id: ID der Collection

    Returns:
        Aktualisierter Count
    """
    from app.database import get_db, CollectionConfiguration, CollectionQuestion, CollectionDocument

    db = next(get_db())
    try:
        collection = db.query(CollectionConfiguration).filter(
            CollectionConfiguration.id == collection_id
        ).first()

        if not collection:
            logger.warning(f"Collection {collection_id} not found for count sync")
            return 0

        if collection.collection_type == 'stackoverflow':
            actual_count = db.query(CollectionQuestion).filter(
                CollectionQuestion.collection_id == collection_id
            ).count()
        else:
            actual_count = db.query(CollectionDocument).filter(
                CollectionDocument.collection_id == collection_id
            ).count()

        if collection.question_count != actual_count:
            logger.info(f"Syncing collection {collection_id} count: {collection.question_count} -> {actual_count}")
            collection.question_count = actual_count
            db.commit()

        return actual_count
    finally:
        db.close()


def rebuild_custom_collection(
    collection_id: int,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Force rebuild a custom collection

    Args:
        collection_id: ID of the collection configuration
        progress_callback: Optional callback to report progress during embedding

    Returns:
        Dict with rebuild statistics
    """
    from app.database import SessionLocal
    from app.services.collection_manager import CollectionManager

    db = SessionLocal()
    try:
        collection_manager = CollectionManager(db=db)
        embedding_service = _get_embedding_service()

        collection = collection_manager.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        logger.info(f"Rebuilding custom collection '{collection.name}' (ID: {collection_id})")

        collection_name = f"custom_collection_{collection_id}"

        if collection.collection_type == "stackoverflow":
            from app.core.graph.tools.document_loaders.custom_collection_loader import CustomCollectionDocumentLoader
            loader = CustomCollectionDocumentLoader(collection_id)
        elif collection.collection_type == "pdf":
            from app.core.graph.tools.document_loaders.pdf_collection_loader import PDFCollectionDocumentLoader
            loader = PDFCollectionDocumentLoader(collection_id)
        else:
            raise ValueError(f"Unknown collection type: {collection.collection_type}")

        documents = loader.load_documents()

        logger.info(f"Loaded {len(documents)} documents for rebuild")

        if progress_callback:
            progress_callback({
                "total_documents": len(documents),
                "processed_documents": 0,
                "current_batch": 0,
                "total_batches": 0,
                "phase": "documents_loaded"
            })

        if not documents:
            error_msg = f"No documents loaded for collection {collection_id} (type: {collection.collection_type})"
            logger.error(error_msg)
            raise ValueError(error_msg)

        vector_store = embedding_service.get_or_create_vector_store(
            collection_name=collection_name,
            documents=documents,
            force_rebuild=True,
            progress_callback=progress_callback
        )

        sync_collection_count(collection_id)

        stats = {
            "collection_id": collection_id,
            "collection_name": collection.name,
            "document_count": len(documents),
            "status": "rebuilt",
            "vector_store_size": vector_store._collection.count() if hasattr(vector_store, '_collection') else len(documents)
        }

        logger.info(f"Rebuild complete: {stats}")
        return stats
    finally:
        db.close()