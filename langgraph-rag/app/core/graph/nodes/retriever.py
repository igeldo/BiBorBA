# core/graph/nodes/retriever.py (Updated with collection support)
from typing import Dict, Any, List
import logging
import time

from app.config import settings
from app.core.graph.tools.retriever_tool import get_retriever_tool
from app.core.graph.tools.vector_store import get_custom_collection_retriever
from app.api.schemas.schemas import RetrieverType
from app.utils.timing import TimingContext

logger = logging.getLogger(__name__)


def create_retriever_node(retriever_type: RetrieverType):
    """Create a retriever node that can retrieve from collections or standard retrievers"""

    def retrieve(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve documents from collections (if collection_ids provided) or standard retrievers

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updated state with retrieved documents
        """
        logger.info("---RETRIEVE---")
        question = state["question"]
        collection_ids = state.get("collection_ids", [])

        total_iterations = state.get("total_iterations", 0) + 1

        try:
            if collection_ids:
                logger.info(f"Retrieving from {len(collection_ids)} collections: {collection_ids}")

                all_documents = []
                for coll_id in collection_ids:
                    try:
                        with TimingContext(f"Retrieve from collection {coll_id}", logger):
                            retriever = get_custom_collection_retriever(
                                collection_id=coll_id,
                                search_kwargs={"k": settings.retrieval_k}
                            )
                            docs = retriever.invoke(question)
                            all_documents.extend(docs)
                            logger.info(f"Retrieved {len(docs)} docs from collection {coll_id}")
                    except Exception as e:
                        logger.warning(f"Failed to retrieve from collection {coll_id}: {e}")

                raw_documents = all_documents
                logger.info(f"Total documents from collections: {len(all_documents)}")

            else:
                with TimingContext("Get retriever tool", logger):
                    retriever_tool = get_retriever_tool(retriever_type)

                with TimingContext(f"Invoke retriever for query: '{question[:50]}...'", logger):
                    raw_documents = retriever_tool.invoke(question)

            logger.debug(f"Raw retrieval result type: {type(raw_documents)}")
            logger.debug(f"Raw retrieval result: {raw_documents}")

            if raw_documents is None:
                documents = []
            elif isinstance(raw_documents, str):
                from langchain_core.documents import Document
                documents = [Document(page_content=raw_documents, metadata={"source": "retriever_string"})]
            elif isinstance(raw_documents, list):
                documents = []
                for item in raw_documents:
                    if hasattr(item, 'page_content'):
                        documents.append(item)
                    else:
                        from langchain_core.documents import Document
                        documents.append(Document(
                            page_content=str(item),
                            metadata={"source": "converted_from_list"}
                        ))
            else:
                from langchain_core.documents import Document
                documents = [Document(
                    page_content=str(raw_documents),
                    metadata={"source": "converted_single_item"}
                )]

            if documents:
                logger.info(f"Successfully retrieved {len(documents)} documents for query: {question[:50]}...")
                for i, doc in enumerate(documents):
                    logger.info(f"Document {i + 1}: {doc.page_content[:100]}...")
            else:
                logger.warning(f"No documents retrieved for query: {question[:50]}...")

            return {
                "documents": documents,
                "question": question,
                "original_question": state.get("original_question", question),  # Preserve original
                "generation": state.get("generation", ""),
                "model_config": state.get("model_config", {}),
                "collection_ids": collection_ids,
                "generation_attempts": state.get("generation_attempts", 0),
                "transform_attempts": state.get("transform_attempts", 0),
                "total_iterations": total_iterations,
                "max_iterations_reached": False,
                "no_relevant_docs_fallback": False,
                "fallback_type": ""
            }

        except FileNotFoundError as e:
            logger.error(f"Document path not found: {e}")
            logger.info("Please check your PDF_PATH in .env file")
            return {
                "documents": [],
                "question": question,
                "original_question": state.get("original_question", question),
                "generation": state.get("generation", ""),
                "model_config": state.get("model_config", {}),
                "collection_ids": collection_ids,
                "generation_attempts": state.get("generation_attempts", 0),
                "transform_attempts": state.get("transform_attempts", 0),
                "total_iterations": total_iterations,
                "max_iterations_reached": False,
                "no_relevant_docs_fallback": False,
                "fallback_type": ""
            }
        except Exception as e:
            logger.error(f"Error in retrieval: {e}")
            logger.info("Continuing with empty documents...")
            return {
                "documents": [],
                "question": question,
                "original_question": state.get("original_question", question),
                "generation": state.get("generation", ""),
                "model_config": state.get("model_config", {}),
                "collection_ids": collection_ids,
                "generation_attempts": state.get("generation_attempts", 0),
                "transform_attempts": state.get("transform_attempts", 0),
                "total_iterations": total_iterations,
                "max_iterations_reached": False,
                "no_relevant_docs_fallback": False,
                "fallback_type": ""
            }

    return retrieve