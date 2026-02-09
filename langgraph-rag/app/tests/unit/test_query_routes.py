"""
Unit tests for Query API Routes schemas.

Tests:
- Query Response Schema structure
- IterationMetrics Schema
- RetrievedDocument Schema
- QueryRatingRequest Schema
- Request/Response schema validation
"""
import pytest
from unittest.mock import MagicMock

from app.api.schemas.schemas import (
    QueryResponse,
    IterationMetrics,
    RetrievedDocument,
    QueryRatingRequest,
    CollectionQueryRequest,
    QueryRequest,
    GraphType
)


class TestIterationMetricsSchema:
    """Tests for IterationMetrics schema."""

    def test_basic_iteration_metrics(self):
        """
        Test that IterationMetrics has all required fields.

        Assume:
            - Creating IterationMetrics with all fields populated

        Expect:
            - All fields are accessible
            - Values match input
        """
        metrics = IterationMetrics(
            generation_attempts=1,
            transform_attempts=0,
            total_iterations=2,
            max_iterations_reached=False,
            no_relevant_docs_fallback=False,
            disclaimer=None
        )

        assert metrics.generation_attempts == 1
        assert metrics.transform_attempts == 0
        assert metrics.total_iterations == 2
        assert metrics.max_iterations_reached is False
        assert metrics.no_relevant_docs_fallback is False
        assert metrics.disclaimer is None

    def test_iteration_metrics_with_max_iterations_disclaimer(self):
        """
        Test IterationMetrics with max_iterations disclaimer.

        Assume:
            - max_iterations_reached is True
            - Disclaimer text is provided

        Expect:
            - max_iterations_reached flag is True
            - Disclaimer contains expected text
        """
        metrics = IterationMetrics(
            generation_attempts=2,
            transform_attempts=2,
            total_iterations=5,
            max_iterations_reached=True,
            no_relevant_docs_fallback=False,
            disclaimer="Diese Antwort konnte nicht vollständig verifiziert werden."
        )

        assert metrics.max_iterations_reached is True
        assert metrics.no_relevant_docs_fallback is False
        assert "verifiziert" in metrics.disclaimer

    def test_iteration_metrics_with_no_docs_fallback_disclaimer(self):
        """
        Test IterationMetrics with no_relevant_docs_fallback disclaimer.

        Assume:
            - no_relevant_docs_fallback is True
            - Disclaimer text mentions general knowledge

        Expect:
            - no_relevant_docs_fallback flag is True
            - Disclaimer contains "allgemeinem Wissen"
        """
        metrics = IterationMetrics(
            generation_attempts=1,
            transform_attempts=2,
            total_iterations=4,
            max_iterations_reached=True,
            no_relevant_docs_fallback=True,
            disclaimer="Diese Antwort basiert auf allgemeinem Wissen, nicht auf Dokumenten aus der Wissensbasis."
        )

        assert metrics.no_relevant_docs_fallback is True
        assert "allgemeinem Wissen" in metrics.disclaimer


class TestRetrievedDocumentSchema:
    """Tests for RetrievedDocument schema."""

    def test_retrieved_document_pdf_source(self):
        """
        Test RetrievedDocument with PDF source.

        Assume:
            - Document is from PDF source
            - All optional fields are populated

        Expect:
            - All fields accessible
            - Metadata includes page number
        """
        doc = RetrievedDocument(
            source="pdf",
            title="SQL Documentation",
            content_preview="SQL JOIN combines...",
            full_content="SQL JOIN combines rows from multiple tables based on related columns.",
            relevance_score=0.95,
            metadata={"page": 1, "file_path": "sql.pdf"}
        )

        assert doc.source == "pdf"
        assert doc.title == "SQL Documentation"
        assert doc.relevance_score == 0.95
        assert doc.metadata["page"] == 1

    def test_retrieved_document_optional_fields(self):
        """
        Test RetrievedDocument with only required fields.

        Assume:
            - Only required fields are provided

        Expect:
            - Optional fields are None
        """
        doc = RetrievedDocument(
            source="stackoverflow",
            title="SQL JOIN Question",
            content_preview="How to use JOIN?"
        )

        assert doc.source == "stackoverflow"
        assert doc.full_content is None
        assert doc.relevance_score is None
        assert doc.metadata is None


class TestQueryResponseSchema:
    """Tests for QueryResponse schema."""

    def test_basic_query_response(self):
        """
        Test basic QueryResponse with required fields.

        Assume:
            - Required fields are provided
            - Optional fields are omitted or have defaults

        Expect:
            - All required fields are accessible
            - Values match input
        """
        response = QueryResponse(
            answer="SQL JOIN is used to combine rows from multiple tables.",
            session_id="test-session-123",
            graph_type="adaptive_rag",
            documents_retrieved=3,
            stackoverflow_documents=0,
            processing_time_ms=150,
            source_breakdown={"pdf": 3}
        )

        assert response.answer.startswith("SQL JOIN")
        assert response.session_id == "test-session-123"
        assert response.graph_type == "adaptive_rag"
        assert response.documents_retrieved == 3

    def test_query_response_with_iteration_metrics(self):
        """
        Test QueryResponse with IterationMetrics included.

        Assume:
            - IterationMetrics object is provided

        Expect:
            - iteration_metrics is accessible
            - Nested fields are correct
        """
        metrics = IterationMetrics(
            generation_attempts=1,
            transform_attempts=0,
            total_iterations=2,
            max_iterations_reached=False,
            no_relevant_docs_fallback=False,
            disclaimer=None
        )

        response = QueryResponse(
            answer="Answer",
            session_id="session-1",
            graph_type="adaptive_rag",
            documents_retrieved=2,
            stackoverflow_documents=0,
            processing_time_ms=100,
            source_breakdown={},
            iteration_metrics=metrics
        )

        assert response.iteration_metrics is not None
        assert response.iteration_metrics.generation_attempts == 1

    def test_query_response_with_retrieved_documents(self):
        """
        Test QueryResponse with RetrievedDocuments list.

        Assume:
            - List of RetrievedDocument objects is provided

        Expect:
            - retrieved_documents list is accessible
            - Contains correct number of documents
        """
        docs = [
            RetrievedDocument(
                source="pdf",
                title="Doc 1",
                content_preview="Preview 1"
            ),
            RetrievedDocument(
                source="pdf",
                title="Doc 2",
                content_preview="Preview 2"
            )
        ]

        response = QueryResponse(
            answer="Answer based on documents",
            session_id="session-2",
            graph_type="simple_rag",
            documents_retrieved=2,
            stackoverflow_documents=0,
            processing_time_ms=200,
            source_breakdown={"pdf": 2},
            retrieved_documents=docs
        )

        assert response.retrieved_documents is not None
        assert len(response.retrieved_documents) == 2

    def test_query_response_with_rewritten_question(self):
        """
        Test QueryResponse with rewritten_question field.

        Assume:
            - Query was transformed during processing
            - rewritten_question is provided

        Expect:
            - rewritten_question is accessible and contains new question
        """
        response = QueryResponse(
            answer="Answer",
            session_id="session-3",
            graph_type="adaptive_rag",
            documents_retrieved=1,
            stackoverflow_documents=0,
            processing_time_ms=250,
            source_breakdown={},
            rewritten_question="What are the different types of SQL JOINs?"
        )

        assert response.rewritten_question is not None
        assert "SQL JOINs" in response.rewritten_question


class TestQueryRatingRequestSchema:
    """Tests for QueryRatingRequest schema."""

    def test_valid_rating(self):
        """
        Test QueryRatingRequest with valid rating.

        Assume:
            - session_id and rating are provided
            - Rating is within valid range

        Expect:
            - Request object is created successfully
            - Fields match input
        """
        request = QueryRatingRequest(
            session_id="session-to-rate",
            rating=5
        )

        assert request.session_id == "session-to-rate"
        assert request.rating == 5

    def test_rating_with_comment(self):
        """
        Test QueryRatingRequest with optional comment.

        Assume:
            - Rating and comment are both provided

        Expect:
            - Comment is accessible
        """
        request = QueryRatingRequest(
            session_id="session-123",
            rating=4,
            comment="Very helpful answer!"
        )

        assert request.rating == 4
        assert request.comment == "Very helpful answer!"

    def test_rating_without_comment(self):
        """
        Test QueryRatingRequest without comment.

        Assume:
            - Only required fields are provided

        Expect:
            - Comment is None
        """
        request = QueryRatingRequest(
            session_id="session-456",
            rating=3
        )

        assert request.rating == 3
        assert request.comment is None


class TestQueryRequestSchema:
    """Tests for QueryRequest schema."""

    def test_basic_query_request(self):
        """
        Test QueryRequest with required fields.

        Assume:
            - question, session_id, and graph_type are provided

        Expect:
            - Request object is created successfully
            - graph_type matches input enum
        """
        request = QueryRequest(
            question="What is SQL JOIN?",
            session_id="query-session-1",
            graph_type=GraphType.ADAPTIVE_RAG
        )

        assert request.question == "What is SQL JOIN?"
        assert request.graph_type == GraphType.ADAPTIVE_RAG

    def test_query_request_with_llm_config(self):
        """
        Test QueryRequest with LLM config.

        Assume:
            - llm_config with temperature and top_p is provided

        Expect:
            - llm_config is accessible with correct values
        """
        request = QueryRequest(
            question="Explain SQL transactions",
            session_id="query-session-2",
            graph_type=GraphType.SIMPLE_RAG,
            llm_config={"temperature": 0.5, "top_p": 0.9}
        )

        assert request.llm_config is not None
        assert request.llm_config["temperature"] == 0.5

    def test_query_request_with_collection_ids(self):
        """
        Test QueryRequest with collection_ids.

        Assume:
            - collection_ids is provided

        Expect:
            - collection_ids is accessible with correct values
        """
        request = QueryRequest(
            question="Explain SQL transactions",
            session_id="query-session-3",
            graph_type=GraphType.ADAPTIVE_RAG,
            collection_ids=[1, 2, 3]
        )

        assert request.collection_ids is not None
        assert len(request.collection_ids) == 3
        assert 1 in request.collection_ids


class TestCollectionQueryRequestSchema:
    """Tests for CollectionQueryRequest schema."""

    def test_collection_query_request(self):
        """
        Test CollectionQueryRequest with collection_ids.

        Assume:
            - Multiple collection_ids are provided

        Expect:
            - collection_ids list is accessible
            - All IDs are present
        """
        request = CollectionQueryRequest(
            question="How do SQL JOINs work?",
            session_id="collection-query-1",
            graph_type=GraphType.ADAPTIVE_RAG,
            collection_ids=[1, 2, 3]
        )

        assert request.question == "How do SQL JOINs work?"
        assert len(request.collection_ids) == 3
        assert 1 in request.collection_ids

    def test_collection_query_empty_ids_allowed_in_schema(self):
        """
        Test that schema allows empty collection_ids (validation in route).

        Assume:
            - Empty collection_ids list is provided
            - Note: Route handler validates this, not the schema

        Expect:
            - Schema accepts empty list
        """
        request = CollectionQueryRequest(
            question="Test",
            session_id="test-session",
            graph_type=GraphType.ADAPTIVE_RAG,
            collection_ids=[]
        )

        assert request.collection_ids == []


class TestGraphTypeEnum:
    """Tests for GraphType enum."""

    def test_graph_type_values(self):
        """
        Test that GraphType enum has correct values.

        Assume:
            - Accessing enum values

        Expect:
            - ADAPTIVE_RAG, SIMPLE_RAG, PURE_LLM have correct string values
        """
        assert GraphType.ADAPTIVE_RAG.value == "adaptive_rag"
        assert GraphType.SIMPLE_RAG.value == "simple_rag"
        assert GraphType.PURE_LLM.value == "pure_llm"

    def test_graph_type_from_string(self):
        """
        Test creating GraphType from string value.

        Assume:
            - Using string values to create enum

        Expect:
            - Correct enum members are returned
        """
        assert GraphType("adaptive_rag") == GraphType.ADAPTIVE_RAG
        assert GraphType("simple_rag") == GraphType.SIMPLE_RAG
        assert GraphType("pure_llm") == GraphType.PURE_LLM


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
