# core/graph/tools/multi_source_retriever.py
"""
Multi-Source Retriever Tool
Kombiniert PDF und StackOverflow Dokumente für bessere Ergebnisse
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.tools import Tool

from app.api.schemas.schemas import RetrieverType
from app.core.graph.tools.vector_store import get_vector_store_service
from app.services.stackoverflow_connector import get_stackoverflow_connector

logger = logging.getLogger(__name__)


class MultiSourceRetriever:
    """Retriever der mehrere Quellen kombiniert"""

    def __init__(self):
        self.vector_store_service = get_vector_store_service()
        self.stackoverflow_connector = None

    def _get_stackoverflow_connector(self):
        """Lazy loading of StackOverflow connector"""
        if self.stackoverflow_connector is None:
            try:
                self.stackoverflow_connector = get_stackoverflow_connector()
                if not self.stackoverflow_connector.test_connection():
                    self.stackoverflow_connector = None
            except Exception as e:
                logger.warning(f"StackOverflow connector not available: {e}")
                self.stackoverflow_connector = None
        return self.stackoverflow_connector

    def retrieve_multi_source(
            self,
            query: str,
            sources: List[RetrieverType] = None,
            k_per_source: int = 3,
            total_k: int = 5,
            stackoverflow_filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Retrieve documents from multiple sources

        Args:
            query: Search query
            sources: List of sources to search (default: [PDF, STACKOVERFLOW])
            k_per_source: Documents per source
            total_k: Maximum total documents to return
            stackoverflow_filters: Additional filters for StackOverflow search

        Returns:
            Combined list of documents
        """
        if sources is None:
            sources = [RetrieverType.PDF, RetrieverType.STACKOVERFLOW]

        all_documents = []
        source_breakdown = {}

        logger.info(f"Multi-source retrieval for query: '{query[:50]}...' from sources: {[s.value for s in sources]}")

        for source in sources:
            try:
                if source == RetrieverType.STACKOVERFLOW:
                    docs = self._retrieve_stackoverflow(query, k_per_source, stackoverflow_filters)
                else:
                    docs = self._retrieve_standard(source, query, k_per_source)

                if docs:
                    all_documents.extend(docs)
                    source_breakdown[source.value] = len(docs)
                    logger.info(f"Retrieved {len(docs)} documents from {source.value}")
                else:
                    source_breakdown[source.value] = 0
                    logger.info(f"No documents found in {source.value}")

            except Exception as e:
                logger.error(f"Error retrieving from {source.value}: {e}")
                source_breakdown[source.value] = 0

        # Score and rank documents
        ranked_documents = self._rank_documents(all_documents, query, total_k)

        final_breakdown = self._calculate_final_breakdown(ranked_documents)

        logger.info(f"Multi-source retrieval complete: {len(ranked_documents)} total documents")
        logger.info(f"Source breakdown: {final_breakdown}")

        # Add source breakdown to metadata of first document for tracking
        if ranked_documents:
            if "multi_source_breakdown" not in ranked_documents[0].metadata:
                ranked_documents[0].metadata["multi_source_breakdown"] = final_breakdown

        return ranked_documents

    def _retrieve_standard(self, source: RetrieverType, query: str, k: int) -> List[Document]:
        """Retrieve from standard sources (PDF)"""
        try:
            retriever = self.vector_store_service.get_retriever(
                retriever_type=source,
                search_kwargs={"k": k}
            )

            documents = retriever.invoke(query)

            # Ensure we have Document objects
            if isinstance(documents, list):
                return [doc for doc in documents if hasattr(doc, 'page_content')]
            elif hasattr(documents, 'page_content'):
                return [documents]
            else:
                return []

        except Exception as e:
            logger.error(f"Error in standard retrieval for {source.value}: {e}")
            return []

    def _retrieve_stackoverflow(
            self,
            query: str,
            k: int,
            filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Retrieve from StackOverflow with both vector search and direct search"""
        documents = []

        try:
            # 1. Vector search in StackOverflow collection
            vector_docs = self._retrieve_standard(RetrieverType.STACKOVERFLOW, query, k // 2)
            documents.extend(vector_docs)
            logger.info(f"StackOverflow vector search returned {len(vector_docs)} documents")

            # 2. Direct database search als Fallback/Ergänzung
            connector = self._get_stackoverflow_connector()
            if connector:
                direct_results = connector.search_questions(
                    search_term=query,
                    limit=k // 2,
                    min_score=1
                )

                # Convert to Documents
                direct_docs = connector.convert_to_documents(
                    qa_pairs=direct_results,
                    include_answers=True,
                    combine_qa=True
                )

                # Avoid duplicates based on question_id
                existing_question_ids = set()
                for doc in documents:
                    if "question_id" in doc.metadata:
                        existing_question_ids.add(doc.metadata["question_id"])

                new_docs = []
                for doc in direct_docs:
                    if "question_id" in doc.metadata:
                        if doc.metadata["question_id"] not in existing_question_ids:
                            new_docs.append(doc)
                            existing_question_ids.add(doc.metadata["question_id"])

                documents.extend(new_docs)
                logger.info(f"StackOverflow direct search added {len(new_docs)} new documents")

        except Exception as e:
            logger.error(f"Error in StackOverflow retrieval: {e}")

        return documents[:k]  # Limit to requested number

    def _rank_documents(self, documents: List[Document], query: str, total_k: int) -> List[Document]:
        """
        Rank documents based on relevance and source credibility

        Simple ranking strategy:
        1. StackOverflow documents with accepted answers get boost
        2. Documents with higher scores get boost
        3. PDF documents get consistent baseline score
        """

        def calculate_score(doc: Document) -> float:
            base_score = 0.5
            metadata = doc.metadata

            # Source-specific scoring
            source = metadata.get("source", "unknown")

            if source == "stackoverflow":
                # StackOverflow specific scoring
                question_score = metadata.get("question_score", 0)
                answer_score = metadata.get("answer_score", 0)
                is_accepted = metadata.get("is_accepted_answer", False)

                # Score based on community validation
                base_score += min(question_score * 0.1, 0.3)  # Question score boost (max 0.3)
                base_score += min(answer_score * 0.1, 0.2)  # Answer score boost (max 0.2)

                if is_accepted:
                    base_score += 0.3  # Accepted answer bonus

            elif source == "pdf" or "pdf" in source.lower():
                # PDF documents get consistent moderate score
                base_score += 0.2

            else:
                # Other sources baseline
                base_score += 0.1

            # Content length consideration (prefer substantial content)
            content_length = len(doc.page_content)
            if content_length > 500:
                base_score += 0.1
            if content_length > 1500:
                base_score += 0.1

            return min(base_score, 1.0)  # Cap at 1.0

        # Score and sort documents
        scored_docs = [(doc, calculate_score(doc)) for doc in documents]
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Take top documents and add score to metadata
        top_docs = []
        for doc, score in scored_docs[:total_k]:
            doc.metadata["retrieval_score"] = round(score, 3)
            top_docs.append(doc)

        return top_docs

    def _calculate_final_breakdown(self, documents: List[Document]) -> Dict[str, int]:
        """Calculate source breakdown of final document set"""
        breakdown = {}

        for doc in documents:
            source = doc.metadata.get("source", "unknown")

            # Normalize source names
            if "stackoverflow" in source.lower():
                source_key = "stackoverflow"
            elif "pdf" in source.lower() or source.endswith(".pdf"):
                source_key = "pdf"
            else:
                source_key = source

            breakdown[source_key] = breakdown.get(source_key, 0) + 1

        return breakdown


class MultiSourceRetrieverTool:
    """Tool wrapper for multi-source retrieval"""

    def __init__(self, default_sources: List[RetrieverType] = None):
        self.retriever = MultiSourceRetriever()
        self.default_sources = default_sources or [RetrieverType.PDF, RetrieverType.STACKOVERFLOW]

    def create_tool(self, sources: List[RetrieverType] = None) -> Tool:
        """Create LangChain tool for multi-source retrieval"""

        def retrieve_func(query: str) -> List[Document]:
            """Tool function that returns documents"""
            return self.retriever.retrieve_multi_source(
                query=query,
                sources=sources or self.default_sources,
                k_per_source=3,
                total_k=5
            )

        source_names = [s.value for s in (sources or self.default_sources)]

        return Tool(
            name="multi_source_retriever",
            description=f"Search and retrieve information from multiple sources: {', '.join(source_names)}. "
                        f"Combines PDF documents and StackOverflow Q&A for comprehensive answers.",
            func=retrieve_func
        )


# Global instances
_multi_source_retriever = None
_multi_source_tool = None


def get_multi_source_retriever() -> MultiSourceRetriever:
    """Get global multi-source retriever instance"""
    global _multi_source_retriever
    if _multi_source_retriever is None:
        _multi_source_retriever = MultiSourceRetriever()
    return _multi_source_retriever


def get_multi_source_tool(sources: List[RetrieverType] = None) -> Tool:
    """Get multi-source retriever tool"""
    global _multi_source_tool
    if _multi_source_tool is None:
        tool_manager = MultiSourceRetrieverTool()
        _multi_source_tool = tool_manager.create_tool(sources)
    return _multi_source_tool