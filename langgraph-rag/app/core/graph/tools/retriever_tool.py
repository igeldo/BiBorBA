import logging
from typing import List

from langchain_core.documents import Document

from app.api.schemas.schemas import RetrieverType
from app.dependencies import get_vector_store_service, get_prompt_manager

logger = logging.getLogger(__name__)


class RetrieverToolManager:
    """Manages retriever tools for different document types"""

    def __init__(self):
        self.vector_store_service = get_vector_store_service()
        self.prompt_manager = get_prompt_manager()
        self._tools = {}

    def get_tool(self, retriever_type: RetrieverType, force_rebuild: bool = False):
        """Get or create a retriever tool"""
        tool_key = f"{retriever_type.value}_retriever"

        if tool_key not in self._tools or force_rebuild:
            self._tools[tool_key] = self._create_tool(retriever_type, force_rebuild)

        return self._tools[tool_key]

    def _create_tool(self, retriever_type: RetrieverType, force_rebuild: bool = False):
        """Create a new retriever tool that preserves document list"""
        logger.info(f"Creating retriever tool for: {retriever_type.value}")

        retriever = self.vector_store_service.get_retriever(
            retriever_type=retriever_type,
            force_rebuild=force_rebuild,
            search_kwargs={"k": 5}
        )

        def custom_retriever_func(query: str) -> List[Document]:
            """Custom retriever function that returns list of documents"""
            try:
                results = retriever.invoke(query)

                if isinstance(results, list):
                    logger.info(f"Custom retriever returned {len(results)} documents for query: {query[:50]}")
                    return results
                else:
                    logger.warning(f"Retriever returned single result, wrapping in list")
                    return [results] if results else []

            except Exception as e:
                logger.error(f"Error in custom retriever: {e}")
                return []

        try:
            test_results = custom_retriever_func("test medication treatment")
            logger.info(f"Custom retriever test: {len(test_results)} documents returned")
        except Exception as e:
            logger.warning(f"Custom retriever test failed: {e}")

        from langchain_core.tools import Tool

        return Tool(
            name=f"retrieve_{retriever_type.value}_documents",
            description=self._get_tool_description(retriever_type),
            func=custom_retriever_func
        )

    def _get_tool_description(self, retriever_type: RetrieverType) -> str:
        """Get appropriate tool description"""
        if retriever_type == RetrieverType.PDF:
            return "Search and retrieve information from PDF documents about SQL."
        else:
            return self.prompt_manager.RETRIEVER_TOOL_DESCRIPTION



def get_retriever_tool(retriever_type: RetrieverType, force_rebuild: bool = False):
    """Get retriever tool for the specified type"""
    manager = RetrieverToolManager()
    return manager.get_tool(retriever_type, force_rebuild)