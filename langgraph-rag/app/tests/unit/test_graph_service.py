"""
Unit tests for GraphService.

Tests:
- execute_query return fields
- Execution is stored in database
- Disclaimer texts for fallback scenarios
- Graph caching behavior
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from app.services.graph_service import GraphService
from app.api.schemas.schemas import GraphType, RetrieverType


class TestGraphServiceDisclaimers:
    """Tests for disclaimer text generation."""

    def test_disclaimer_for_no_docs_fallback(self):
        """
        Test that correct disclaimer is returned for no_relevant_docs_fallback.

        Assume:
            - Final state has no_relevant_docs_fallback = True

        Expect:
            - Disclaimer mentions "allgemeinem Wissen" (general knowledge)
            - Disclaimer mentions "nicht auf Dokumenten" (not from documents)
        """
        service = GraphService()

        final_state = {
            "no_relevant_docs_fallback": True,
            "max_iterations_reached": False
        }

        disclaimer = service._get_disclaimer_text(final_state)

        assert disclaimer is not None
        assert "allgemeinem Wissen" in disclaimer
        assert "nicht auf Dokumenten" in disclaimer

    def test_disclaimer_for_max_iterations(self):
        """
        Test that correct disclaimer is returned for max_iterations_reached.

        Assume:
            - Final state has max_iterations_reached = True

        Expect:
            - Disclaimer mentions "nicht vollständig verifiziert"
        """
        service = GraphService()

        final_state = {
            "no_relevant_docs_fallback": False,
            "max_iterations_reached": True
        }

        disclaimer = service._get_disclaimer_text(final_state)

        assert disclaimer is not None
        assert "nicht vollständig verifiziert" in disclaimer

    def test_no_disclaimer_for_normal_answer(self):
        """
        Test that no disclaimer is returned for normal successful answer.

        Assume:
            - Final state has both fallback flags set to False

        Expect:
            - Disclaimer is None
        """
        service = GraphService()

        final_state = {
            "no_relevant_docs_fallback": False,
            "max_iterations_reached": False
        }

        disclaimer = service._get_disclaimer_text(final_state)

        assert disclaimer is None

    def test_no_docs_fallback_takes_priority(self):
        """
        Test that no_docs_fallback disclaimer takes priority when both flags set.

        Assume:
            - Final state has both no_relevant_docs_fallback and max_iterations_reached True

        Expect:
            - Disclaimer is for no_docs_fallback (checked first)
        """
        service = GraphService()

        final_state = {
            "no_relevant_docs_fallback": True,
            "max_iterations_reached": True
        }

        disclaimer = service._get_disclaimer_text(final_state)

        assert "allgemeinem Wissen" in disclaimer


class TestGraphServiceGetGraph:
    """Tests for get_graph method and caching."""

    @patch('app.services.graph_service.create_adaptive_graph')
    def test_get_graph_creates_new_graph(self, mock_create_graph):
        """
        Test that a new graph is created when not cached.

        Assume:
            - Graph cache is empty
            - Requesting ADAPTIVE_RAG with PDF retriever

        Expect:
            - create_adaptive_graph is called once
            - Returned graph matches the created one
        """
        mock_graph = MagicMock()
        mock_create_graph.return_value = mock_graph

        service = GraphService()
        service._graphs = {}

        result = service.get_graph(GraphType.ADAPTIVE_RAG, RetrieverType.PDF)

        mock_create_graph.assert_called_once_with(RetrieverType.PDF)
        assert result == mock_graph

    @patch('app.services.graph_service.create_adaptive_graph')
    def test_get_graph_returns_cached(self, mock_create_graph):
        """
        Test that cached graph is returned without creating new one.

        Assume:
            - Graph for adaptive_rag_pdf is already in cache

        Expect:
            - create_adaptive_graph is NOT called
            - Cached graph is returned
        """
        mock_graph = MagicMock()

        service = GraphService()
        service._graphs = {"adaptive_rag_pdf": mock_graph}

        result = service.get_graph(GraphType.ADAPTIVE_RAG, RetrieverType.PDF)

        mock_create_graph.assert_not_called()
        assert result == mock_graph

    @patch('app.services.graph_service.create_rag_graph')
    def test_get_graph_simple_rag(self, mock_create_graph):
        """
        Test that SIMPLE_RAG graph type creates correct graph.

        Assume:
            - Graph cache is empty
            - Requesting SIMPLE_RAG type

        Expect:
            - create_rag_graph is called
        """
        mock_graph = MagicMock()
        mock_create_graph.return_value = mock_graph

        service = GraphService()
        service._graphs = {}

        result = service.get_graph(GraphType.SIMPLE_RAG, RetrieverType.PDF)

        mock_create_graph.assert_called_once()

    @patch('app.services.graph_service.create_pure_llm_graph')
    def test_get_graph_pure_llm(self, mock_create_graph):
        """
        Test that PURE_LLM graph type creates correct graph.

        Assume:
            - Graph cache is empty
            - Requesting PURE_LLM type

        Expect:
            - create_pure_llm_graph is called
        """
        mock_graph = MagicMock()
        mock_create_graph.return_value = mock_graph

        service = GraphService()
        service._graphs = {}

        result = service.get_graph(GraphType.PURE_LLM, RetrieverType.PDF)

        mock_create_graph.assert_called_once()


class TestGraphServiceExecuteQuery:
    """Tests for execute_query method."""

    @pytest.mark.asyncio
    @patch('app.services.graph_service.GraphService._store_execution_details')
    @patch('app.services.graph_service.GraphService.get_graph')
    async def test_execute_query_returns_required_fields(
        self, mock_get_graph, mock_store
    ):
        """
        Test that execute_query returns all required response fields.

        Assume:
            - Graph executes successfully
            - Final state contains all expected data

        Expect:
            - Result contains: answer, documents_retrieved, graph_trace,
              processing_time_ms, iteration_metrics, retrieved_documents,
              node_timings, graph_execution_id
        """
        mock_store.return_value = 1

        mock_graph = MagicMock()
        mock_graph.stream = MagicMock(return_value=[
            {"retrieve": {"documents": [], "question": "test"}},
            {"generate": {
                "generation": "Test answer",
                "documents": [],
                "question": "test",
                "original_question": "test",
                "generation_attempts": 1,
                "transform_attempts": 0,
                "total_iterations": 2,
                "max_iterations_reached": False,
                "no_relevant_docs_fallback": False,
                "fallback_type": ""
            }}
        ])
        mock_get_graph.return_value = mock_graph

        service = GraphService()
        result = await service.execute_query(
            question="What is SQL JOIN?",
            session_id="test-session-123",
            graph_type=GraphType.ADAPTIVE_RAG,
            retriever_type=RetrieverType.PDF
        )

        assert "answer" in result
        assert "documents_retrieved" in result
        assert "graph_trace" in result
        assert "processing_time_ms" in result
        assert "iteration_metrics" in result
        assert "retrieved_documents" in result
        assert "node_timings" in result
        assert "graph_execution_id" in result

    @pytest.mark.asyncio
    @patch('app.services.graph_service.GraphService._store_execution_details')
    @patch('app.services.graph_service.GraphService.get_graph')
    async def test_execute_query_stores_execution(
        self, mock_get_graph, mock_store
    ):
        """
        Test that GraphExecution is stored in database.

        Assume:
            - Graph executes successfully

        Expect:
            - _store_execution_details is called with success=True
            - graph_execution_id is included in result
        """
        mock_store.return_value = 42

        mock_graph = MagicMock()
        mock_graph.stream = MagicMock(return_value=[
            {"generate": {
                "generation": "Answer",
                "documents": [],
                "question": "test",
                "original_question": "test",
                "generation_attempts": 1,
                "transform_attempts": 0,
                "total_iterations": 1,
                "max_iterations_reached": False,
                "no_relevant_docs_fallback": False,
                "fallback_type": ""
            }}
        ])
        mock_get_graph.return_value = mock_graph

        service = GraphService()
        result = await service.execute_query(
            question="Test",
            session_id="session-123",
            graph_type=GraphType.ADAPTIVE_RAG,
            retriever_type=RetrieverType.PDF
        )

        mock_store.assert_called_once()
        call_kwargs = mock_store.call_args[1]
        assert call_kwargs["session_id"] == "session-123"
        assert call_kwargs["success"] is True

        assert result["graph_execution_id"] == 42

    @pytest.mark.asyncio
    @patch('app.services.graph_service.GraphService._store_execution_details')
    @patch('app.services.graph_service.GraphService.get_graph')
    async def test_execute_query_handles_rewritten_question(
        self, mock_get_graph, mock_store
    ):
        """
        Test that rewritten_question is captured when question was transformed.

        Assume:
            - Query transformation occurred during execution
            - Final question differs from original

        Expect:
            - rewritten_question is set to the transformed question
        """
        mock_store.return_value = 1

        mock_graph = MagicMock()
        mock_graph.stream = MagicMock(return_value=[
            {"transform_query": {"question": "Better question about SQL"}},
            {"generate": {
                "generation": "Answer",
                "documents": [],
                "question": "Better question about SQL",
                "original_question": "SQL?",
                "generation_attempts": 1,
                "transform_attempts": 1,
                "total_iterations": 3,
                "max_iterations_reached": False,
                "no_relevant_docs_fallback": False,
                "fallback_type": ""
            }}
        ])
        mock_get_graph.return_value = mock_graph

        service = GraphService()
        result = await service.execute_query(
            question="SQL?",
            session_id="session-123",
            graph_type=GraphType.ADAPTIVE_RAG,
            retriever_type=RetrieverType.PDF
        )

        assert result["rewritten_question"] == "Better question about SQL"

    @pytest.mark.asyncio
    @patch('app.services.graph_service.GraphService._store_execution_details')
    @patch('app.services.graph_service.GraphService.get_graph')
    async def test_execute_query_includes_disclaimer(
        self, mock_get_graph, mock_store
    ):
        """
        Test that disclaimer is included in iteration_metrics when fallback used.

        Assume:
            - no_docs_fallback was triggered

        Expect:
            - iteration_metrics contains disclaimer text
            - no_relevant_docs_fallback is True in metrics
        """
        mock_store.return_value = 1

        mock_graph = MagicMock()
        mock_graph.stream = MagicMock(return_value=[
            {"no_docs_fallback": {
                "generation": "Pure LLM answer",
                "documents": [],
                "question": "test",
                "original_question": "test",
                "generation_attempts": 1,
                "transform_attempts": 2,
                "total_iterations": 5,
                "max_iterations_reached": True,
                "no_relevant_docs_fallback": True,
                "fallback_type": "no_relevant_docs"
            }}
        ])
        mock_get_graph.return_value = mock_graph

        service = GraphService()
        result = await service.execute_query(
            question="Test",
            session_id="session-123",
            graph_type=GraphType.ADAPTIVE_RAG,
            retriever_type=RetrieverType.PDF
        )

        assert result["iteration_metrics"]["disclaimer"] is not None
        assert result["iteration_metrics"]["no_relevant_docs_fallback"] is True


class TestGraphServiceErrorHandling:
    """Tests for error handling in GraphService."""

    @pytest.mark.asyncio
    @patch('app.services.graph_service.GraphService._store_execution_details')
    @patch('app.services.graph_service.GraphService.get_graph')
    async def test_execute_query_stores_failure(
        self, mock_get_graph, mock_store
    ):
        """
        Test that failed executions are stored with error details.

        Assume:
            - Graph execution raises an exception

        Expect:
            - Exception is re-raised
            - _store_execution_details is called with success=False
            - error_message contains the exception message
        """
        mock_store.return_value = None

        mock_graph = MagicMock()
        mock_graph.stream = MagicMock(side_effect=Exception("Graph execution failed"))
        mock_get_graph.return_value = mock_graph

        service = GraphService()

        with pytest.raises(Exception) as excinfo:
            await service.execute_query(
                question="Test",
                session_id="session-123",
                graph_type=GraphType.ADAPTIVE_RAG,
                retriever_type=RetrieverType.PDF
            )

        assert "Graph execution failed" in str(excinfo.value)

        mock_store.assert_called_once()
        call_kwargs = mock_store.call_args[1]
        assert call_kwargs["success"] is False
        assert call_kwargs["error_message"] == "Graph execution failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
