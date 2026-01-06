# core/graph/tools/vector_store.py

import logging
from typing import List, Optional, Dict, Any, Callable

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from app.config import settings
from app.api.schemas.schemas import RetrieverType
from .document_loaders import PDFDocumentLoader, StackOverflowDocumentLoader
from .document_loaders.custom_collection_loader import CustomCollectionDocumentLoader

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

        # Load documents if needed
        documents = None
        if force_rebuild or not self._collection_exists(collection_name):
            documents = self._load_documents(retriever_type)
            logger.info(f"Loaded {len(documents)} documents for {retriever_type.value}")

        # Get or create vector store
        vector_store = self.embedding_service.get_or_create_vector_store(
            collection_name=collection_name,
            documents=documents,
            force_rebuild=force_rebuild
        )

        # Configure search parameters
        search_config = {
            "k": 5,  # Number of documents to retrieve
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
                # StackOverflow loader kann zusätzliche Filter erhalten
                filters = getattr(settings, 'stackoverflow_default_filters', {})
                documents = loader.load_documents(filters=filters)
            else:
                documents = loader.load_documents()

            logger.info(f"Loader {retriever_type.value} loaded {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"Error loading documents with {retriever_type.value} loader: {e}")
            raise

    def get_document_stats(self, retriever_type: RetrieverType) -> Dict[str, Any]:
        """Get statistics about documents for a retriever type"""
        collection_name = self._get_collection_name(retriever_type)

        # Get loader-specific stats
        if retriever_type in self._loaders:
            loader = self._loaders[retriever_type]

            if retriever_type == RetrieverType.STACKOVERFLOW:
                # StackOverflow spezifische Stats
                loader_stats = loader.get_statistics()
                if loader_stats:
                    loader_stats["collection_name"] = collection_name

                    # Kombiniere mit Vector Store Info
                    collection_info = self.embedding_service.get_collection_info(collection_name)
                    if collection_info:
                        loader_stats.update({
                            "vector_store_size": collection_info.get("document_count", 0),
                            "embedding_model": collection_info.get("embedding_model"),
                            "last_updated": collection_info.get("last_used")
                        })

                    return loader_stats

        # Standard collection info
        info = self.embedding_service.get_collection_info(collection_name)

        if not info:
            return {
                "collection_name": collection_name,
                "exists": False,
                "document_count": 0
            }

        return {
            "collection_name": collection_name,
            "exists": True,
            "document_count": info.get("document_count", 0),
            "embedding_model": info.get("embedding_model"),
            "created_at": info.get("created_at"),
            "last_used": info.get("last_used")
        }

    def rebuild_collection(self, retriever_type: RetrieverType) -> Dict[str, Any]:
        """Force rebuild a collection"""
        logger.info(f"Rebuilding collection for {retriever_type.value}")

        collection_name = self._get_collection_name(retriever_type)
        documents = self._load_documents(retriever_type)

        # Force rebuild
        vector_store = self.embedding_service.get_or_create_vector_store(
            collection_name=collection_name,
            documents=documents,
            force_rebuild=True
        )

        return {
            "collection_name": collection_name,
            "document_count": len(documents),
            "status": "rebuilt",
            "vector_store_size": vector_store._collection.count()
        }

    def search_documents(
            self,
            retriever_type: RetrieverType,
            query: str,
            k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search documents directly"""
        collection_name = self._get_collection_name(retriever_type)

        vector_store = self.embedding_service.get_or_create_vector_store(
            collection_name=collection_name
        )

        # Perform similarity search with score
        try:
            results = vector_store.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            # Fallback to basic similarity search without score
            docs = vector_store.similarity_search(query, k=k)
            results = [(doc, 0.0) for doc in docs]

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            }
            for doc, score in results
        ]

    def get_loader_stats(self, retriever_type: RetrieverType) -> Optional[Dict[str, Any]]:
        """Get loader-specific statistics"""
        if retriever_type not in self._loaders:
            return None

        loader = self._loaders[retriever_type]

        try:
            if retriever_type == RetrieverType.STACKOVERFLOW:
                return loader.get_statistics()
            else:
                # Für andere Loader: Lade Sample Dokumente für Stats
                sample_docs = loader.load_documents()
                return loader.get_stats(sample_docs)
        except Exception as e:
            logger.error(f"Error getting loader stats for {retriever_type.value}: {e}")
            return {"error": str(e)}

    # StackOverflow-spezifische Methoden
    def search_stackoverflow_directly(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Direct search in StackOverflow database (not vector search)"""
        if RetrieverType.STACKOVERFLOW not in self._loaders:
            return []

        stackoverflow_loader = self._loaders[RetrieverType.STACKOVERFLOW]
        return stackoverflow_loader.search_direct(query, limit=limit)

    def get_stackoverflow_question(self, question_id: int) -> Optional[Dict[str, Any]]:
        """Get specific StackOverflow question with answers"""
        if RetrieverType.STACKOVERFLOW not in self._loaders:
            return None

        stackoverflow_loader = self._loaders[RetrieverType.STACKOVERFLOW]
        return stackoverflow_loader.get_question_by_id(question_id)

    def filter_stackoverflow_documents(
            self,
            documents: List[Document],
            tags: List[str] = None,
            min_score: int = None
    ) -> List[Document]:
        """Filter StackOverflow documents by tags and score"""
        if RetrieverType.STACKOVERFLOW not in self._loaders:
            return documents

        stackoverflow_loader = self._loaders[RetrieverType.STACKOVERFLOW]

        if tags:
            documents = stackoverflow_loader.filter_by_tags(documents, tags)

        if min_score is not None:
            documents = stackoverflow_loader.filter_by_score(documents, min_score)

        return documents

    # Collection Management
    def list_collections(self) -> Dict[str, Dict[str, Any]]:
        """List all collections with their stats"""
        collections = {}

        for retriever_type in RetrieverType:
            try:
                stats = self.get_document_stats(retriever_type)
                collections[retriever_type.value] = stats
            except Exception as e:
                logger.warning(f"Could not get stats for {retriever_type.value}: {e}")
                collections[retriever_type.value] = {"error": str(e)}

        return collections

    def cleanup_collections(self, days_threshold: int = 30) -> Dict[str, Any]:
        """Clean up unused collections"""
        return self.embedding_service.cleanup_unused_collections(days_threshold)

    # Health Check
    def health_check(self) -> Dict[str, Any]:
        """Check health of vector store service and loaders"""
        health = {
            "vector_store_service": True,
            "embedding_service": True,
            "loaders": {}
        }

        # Test embedding service
        try:
            collections = self.embedding_service.list_collections()
            health["collections_available"] = len(collections)
        except Exception as e:
            health["embedding_service"] = False
            health["embedding_error"] = str(e)

        # Test each loader
        for retriever_type, loader in self._loaders.items():
            try:
                if retriever_type == RetrieverType.STACKOVERFLOW:
                    # Test StackOverflow connection
                    connector = loader._get_stackoverflow_connector()
                    health["loaders"][retriever_type.value] = connector is not None
                    if connector:
                        health["loaders"][f"{retriever_type.value}_connection"] = connector.test_connection()
                else:
                    # Test path existence for file-based loaders
                    if retriever_type == RetrieverType.PDF:
                        health["loaders"][retriever_type.value] = settings.pdf_path.exists()
                    else:
                        health["loaders"][retriever_type.value] = True

            except Exception as e:
                health["loaders"][retriever_type.value] = False
                health["loaders"][f"{retriever_type.value}_error"] = str(e)

        # Overall health
        health["overall"] = (
                health["vector_store_service"] and
                health["embedding_service"] and
                any(health["loaders"].values())
        )

        return health


# Custom Collection Support

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

        # Verify collection exists
        collection = collection_manager.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        logger.info(f"Getting retriever for custom collection '{collection.name}' (ID: {collection_id})")

        collection_name = f"custom_collection_{collection_id}"

        # Check if collection exists in vector store
        collection_exists = False
        info = embedding_service.get_collection_info(collection_name)
        if info and info.get("document_count", 0) > 0:
            collection_exists = True

        # Load documents if needed
        documents = None
        if force_rebuild or not collection_exists:
            logger.info(f"Loading documents for collection {collection_id} (type: {collection.collection_type})")

            # Choose loader based on collection type
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

        # Get or create vector store
        vector_store = embedding_service.get_or_create_vector_store(
            collection_name=collection_name,
            documents=documents,
            force_rebuild=force_rebuild
        )

        # Configure search parameters
        search_config = {
            "k": 5,  # Number of documents to retrieve
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
        else:  # pdf
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

        # Verify collection exists
        collection = collection_manager.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        logger.info(f"Rebuilding custom collection '{collection.name}' (ID: {collection_id})")

        collection_name = f"custom_collection_{collection_id}"

        # Choose loader based on collection type
        if collection.collection_type == "stackoverflow":
            from app.core.graph.tools.document_loaders.custom_collection_loader import CustomCollectionDocumentLoader
            loader = CustomCollectionDocumentLoader(collection_id)
        elif collection.collection_type == "pdf":
            from app.core.graph.tools.document_loaders.pdf_collection_loader import PDFCollectionDocumentLoader
            loader = PDFCollectionDocumentLoader(collection_id)
        else:
            raise ValueError(f"Unknown collection type: {collection.collection_type}")

        # Load documents
        documents = loader.load_documents()

        logger.info(f"Loaded {len(documents)} documents for rebuild")

        # Report document count if callback provided
        if progress_callback:
            progress_callback({
                "total_documents": len(documents),
                "processed_documents": 0,
                "current_batch": 0,
                "total_batches": 0,
                "phase": "documents_loaded"
            })

        # Check if documents were loaded
        if not documents:
            error_msg = f"No documents loaded for collection {collection_id} (type: {collection.collection_type})"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Force rebuild vector store with progress callback
        vector_store = embedding_service.get_or_create_vector_store(
            collection_name=collection_name,
            documents=documents,
            force_rebuild=True,
            progress_callback=progress_callback
        )

        # Sync question_count with actual count
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