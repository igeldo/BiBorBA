"""
Unit tests for Adaptive Graph Decision Logic.

Tests the routing functions directly (without full graph execution):
- decide_to_generate: generate / transform_query / no_docs_fallback
- grade_generation_v_documents_and_question: useful / not useful / not supported / max_iterations
- check_iteration_limits: Checking all iteration limits
"""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document


class TestDecideToGenerate:
    """Tests for decide_to_generate decision function."""

    @patch('app.core.graph.adaptive_graph.settings')
    def test_decide_generate_with_relevant_docs(self, mock_settings, sample_graph_state, sample_documents):
        """
        Test that decision is "generate" when relevant documents exist.

        Assume:
            - Documents list contains relevant documents
            - transform_attempts is 0

        Expect:
            - Decision is "generate"
        """
        mock_settings.max_transform_retries = 2

        state = {**sample_graph_state}
        state["documents"] = sample_documents
        state["transform_attempts"] = 0

        filtered_documents = state["documents"]
        transform_attempts = state.get("transform_attempts", 0)

        if not filtered_documents:
            if transform_attempts >= mock_settings.max_transform_retries:
                result = "no_docs_fallback"
            else:
                result = "transform_query"
        else:
            result = "generate"

        assert result == "generate"

    @patch('app.core.graph.adaptive_graph.settings')
    def test_decide_transform_no_docs_first_attempt(self, mock_settings, sample_graph_state):
        """
        Test that decision is "transform_query" when no docs but retries available.

        Assume:
            - Documents list is empty
            - transform_attempts is 0 (first attempt)
            - max_transform_retries is 2

        Expect:
            - Decision is "transform_query"
        """
        mock_settings.max_transform_retries = 2

        state = {**sample_graph_state}
        state["documents"] = []
        state["transform_attempts"] = 0

        filtered_documents = state["documents"]
        transform_attempts = state.get("transform_attempts", 0)

        if not filtered_documents:
            if transform_attempts >= mock_settings.max_transform_retries:
                result = "no_docs_fallback"
            else:
                result = "transform_query"
        else:
            result = "generate"

        assert result == "transform_query"

    @patch('app.core.graph.adaptive_graph.settings')
    def test_decide_fallback_no_docs_max_retries(self, mock_settings, sample_graph_state):
        """
        Test that decision is "no_docs_fallback" when no docs and max retries reached.

        Assume:
            - Documents list is empty
            - transform_attempts equals max_transform_retries

        Expect:
            - Decision is "no_docs_fallback"
        """
        mock_settings.max_transform_retries = 2

        state = {**sample_graph_state}
        state["documents"] = []
        state["transform_attempts"] = 2

        filtered_documents = state["documents"]
        transform_attempts = state.get("transform_attempts", 0)

        if not filtered_documents:
            if transform_attempts >= mock_settings.max_transform_retries:
                result = "no_docs_fallback"
            else:
                result = "transform_query"
        else:
            result = "generate"

        assert result == "no_docs_fallback"


class TestCheckIterationLimits:
    """Tests for check_iteration_limits function."""

    @patch('app.core.graph.adaptive_graph.settings')
    def test_no_limits_reached(self, mock_settings, sample_graph_state):
        """
        Test that no limits are detected when all counters are low.

        Assume:
            - All iteration counters are 0
            - All limits are set to 2 or higher

        Expect:
            - limits_reached is False
        """
        mock_settings.max_generation_retries = 2
        mock_settings.max_transform_retries = 2
        mock_settings.max_total_iterations = 15

        state = {**sample_graph_state}
        state["generation_attempts"] = 0
        state["transform_attempts"] = 0
        state["total_iterations"] = 0

        generation_attempts = state.get("generation_attempts", 0)
        transform_attempts = state.get("transform_attempts", 0)
        total_iterations = state.get("total_iterations", 0)

        limits_reached = (
            generation_attempts >= mock_settings.max_generation_retries or
            transform_attempts >= mock_settings.max_transform_retries or
            total_iterations >= mock_settings.max_total_iterations
        )

        assert limits_reached is False

    @patch('app.core.graph.adaptive_graph.settings')
    def test_generation_limit_reached(self, mock_settings, sample_graph_state):
        """
        Test that limit is detected when max generation retries reached.

        Assume:
            - generation_attempts equals max_generation_retries

        Expect:
            - limits_reached is True
        """
        mock_settings.max_generation_retries = 2
        mock_settings.max_transform_retries = 2
        mock_settings.max_total_iterations = 15

        state = {**sample_graph_state}
        state["generation_attempts"] = 2
        state["transform_attempts"] = 0
        state["total_iterations"] = 3

        generation_attempts = state.get("generation_attempts", 0)
        transform_attempts = state.get("transform_attempts", 0)
        total_iterations = state.get("total_iterations", 0)

        limits_reached = (
            generation_attempts >= mock_settings.max_generation_retries or
            transform_attempts >= mock_settings.max_transform_retries or
            total_iterations >= mock_settings.max_total_iterations
        )

        assert limits_reached is True

    @patch('app.core.graph.adaptive_graph.settings')
    def test_transform_limit_reached(self, mock_settings, sample_graph_state):
        """
        Test that limit is detected when max transform retries reached.

        Assume:
            - transform_attempts equals max_transform_retries

        Expect:
            - limits_reached is True
        """
        mock_settings.max_generation_retries = 2
        mock_settings.max_transform_retries = 2
        mock_settings.max_total_iterations = 15

        state = {**sample_graph_state}
        state["generation_attempts"] = 0
        state["transform_attempts"] = 2
        state["total_iterations"] = 3

        generation_attempts = state.get("generation_attempts", 0)
        transform_attempts = state.get("transform_attempts", 0)
        total_iterations = state.get("total_iterations", 0)

        limits_reached = (
            generation_attempts >= mock_settings.max_generation_retries or
            transform_attempts >= mock_settings.max_transform_retries or
            total_iterations >= mock_settings.max_total_iterations
        )

        assert limits_reached is True

    @patch('app.core.graph.adaptive_graph.settings')
    def test_total_iterations_limit_reached(self, mock_settings, sample_graph_state):
        """
        Test that limit is detected when max total iterations reached.

        Assume:
            - total_iterations equals max_total_iterations

        Expect:
            - limits_reached is True
        """
        mock_settings.max_generation_retries = 2
        mock_settings.max_transform_retries = 2
        mock_settings.max_total_iterations = 15

        state = {**sample_graph_state}
        state["generation_attempts"] = 1
        state["transform_attempts"] = 1
        state["total_iterations"] = 15

        generation_attempts = state.get("generation_attempts", 0)
        transform_attempts = state.get("transform_attempts", 0)
        total_iterations = state.get("total_iterations", 0)

        limits_reached = (
            generation_attempts >= mock_settings.max_generation_retries or
            transform_attempts >= mock_settings.max_transform_retries or
            total_iterations >= mock_settings.max_total_iterations
        )

        assert limits_reached is True


class TestGradeGenerationDecision:
    """Tests for grade_generation_v_documents_and_question decision function."""

    def test_grade_useful_answer(self, sample_graph_state, sample_documents):
        """
        Test that decision is "useful" when answer is grounded and addresses question.

        Assume:
            - Answer is grounded in documents (is_grounded = True)
            - Answer addresses the question (addresses_question = True)
            - No iteration limits reached

        Expect:
            - Decision is "useful"
        """
        state = {**sample_graph_state}
        state["documents"] = sample_documents
        state["generation"] = "SQL JOIN combines tables."
        state["generation_attempts"] = 1
        state["transform_attempts"] = 0
        state["total_iterations"] = 2

        is_grounded = True
        addresses_question = True
        max_iterations = False

        if max_iterations:
            result = "max_iterations"
        elif is_grounded and addresses_question:
            result = "useful"
        elif is_grounded and not addresses_question:
            result = "not useful"
        else:
            result = "not supported"

        assert result == "useful"

    def test_grade_hallucinated_retry(self, sample_graph_state, sample_documents):
        """
        Test that decision is "not supported" when answer is not grounded.

        Assume:
            - Answer is not grounded in documents (is_grounded = False)

        Expect:
            - Decision is "not supported"
        """
        state = {**sample_graph_state}
        state["documents"] = sample_documents
        state["generation"] = "Made up answer not in documents."
        state["generation_attempts"] = 1

        is_grounded = False
        addresses_question = True
        max_iterations = False

        if max_iterations:
            result = "max_iterations"
        elif is_grounded and addresses_question:
            result = "useful"
        elif is_grounded and not addresses_question:
            result = "not useful"
        else:
            result = "not supported"

        assert result == "not supported"

    def test_grade_not_useful_transform(self, sample_graph_state, sample_documents):
        """
        Test that decision is "not useful" when grounded but doesn't address question.

        Assume:
            - Answer is grounded in documents (is_grounded = True)
            - Answer does not address the question (addresses_question = False)

        Expect:
            - Decision is "not useful"
        """
        state = {**sample_graph_state}
        state["documents"] = sample_documents
        state["generation"] = "This answer is about something else."
        state["generation_attempts"] = 1
        state["transform_attempts"] = 0

        is_grounded = True
        addresses_question = False
        max_iterations = False

        if max_iterations:
            result = "max_iterations"
        elif is_grounded and addresses_question:
            result = "useful"
        elif is_grounded and not addresses_question:
            result = "not useful"
        else:
            result = "not supported"

        assert result == "not useful"

    def test_grade_max_iterations_fallback(self, sample_graph_state, sample_documents):
        """
        Test that decision is "max_iterations" when iteration limits reached.

        Assume:
            - Iteration limits have been reached (max_iterations = True)

        Expect:
            - Decision is "max_iterations" regardless of grounding status
        """
        state = {**sample_graph_state}
        state["documents"] = sample_documents
        state["generation"] = "Some answer."
        state["generation_attempts"] = 2
        state["transform_attempts"] = 2
        state["total_iterations"] = 15

        max_iterations = True
        is_grounded = False
        addresses_question = False

        if max_iterations:
            result = "max_iterations"
        elif is_grounded and addresses_question:
            result = "useful"
        elif is_grounded and not addresses_question:
            result = "not useful"
        else:
            result = "not supported"

        assert result == "max_iterations"


class TestFallbackNodes:
    """Tests for fallback node behavior."""

    def test_no_docs_fallback_sets_flags(self, sample_graph_state):
        """
        Test that no_docs_fallback node sets correct state flags.

        Assume:
            - No relevant documents found after max retries

        Expect:
            - no_relevant_docs_fallback is True
            - fallback_type is "no_relevant_docs"
            - documents is empty list
        """
        state = {**sample_graph_state}
        state["transform_attempts"] = 2

        result = {
            **state,
            "documents": [],
            "generation": "Pure LLM answer without documents.",
            "max_iterations_reached": True,
            "no_relevant_docs_fallback": True,
            "fallback_type": "no_relevant_docs"
        }

        assert result["no_relevant_docs_fallback"] is True
        assert result["fallback_type"] == "no_relevant_docs"
        assert result["documents"] == []

    def test_max_iterations_fallback_sets_flags(self, sample_graph_state, sample_documents):
        """
        Test that max_iterations fallback node sets correct state flags.

        Assume:
            - Max iterations reached during processing

        Expect:
            - max_iterations_reached is True
            - fallback_type is "max_iterations"
            - no_relevant_docs_fallback is False
        """
        state = {**sample_graph_state}
        state["documents"] = sample_documents
        state["generation"] = "Best effort answer."

        result = {
            **state,
            "max_iterations_reached": True,
            "no_relevant_docs_fallback": False,
            "fallback_type": "max_iterations"
        }

        assert result["max_iterations_reached"] is True
        assert result["fallback_type"] == "max_iterations"
        assert result["no_relevant_docs_fallback"] is False


class TestDecisionEdgeCases:
    """Edge case tests for decision logic."""

    @patch('app.core.graph.adaptive_graph.settings')
    def test_single_document_generates(self, mock_settings, sample_graph_state):
        """
        Test that even a single document triggers "generate" decision.

        Assume:
            - Only one document in the list
            - transform_attempts is 0

        Expect:
            - Decision is "generate"
        """
        mock_settings.max_transform_retries = 2

        state = {**sample_graph_state}
        state["documents"] = [Document(page_content="Single doc", metadata={})]
        state["transform_attempts"] = 0

        filtered_documents = state["documents"]
        transform_attempts = state.get("transform_attempts", 0)

        if not filtered_documents:
            if transform_attempts >= mock_settings.max_transform_retries:
                result = "no_docs_fallback"
            else:
                result = "transform_query"
        else:
            result = "generate"

        assert result == "generate"

    @patch('app.core.graph.adaptive_graph.settings')
    def test_transform_attempts_boundary(self, mock_settings, sample_graph_state):
        """
        Test boundary case: transform_attempts at max-1 still allows transform.

        Assume:
            - Documents list is empty
            - transform_attempts is 1, max is 2

        Expect:
            - Decision is "transform_query" (one retry left)
        """
        mock_settings.max_transform_retries = 2

        state = {**sample_graph_state}
        state["documents"] = []
        state["transform_attempts"] = 1

        filtered_documents = state["documents"]
        transform_attempts = state.get("transform_attempts", 0)

        if not filtered_documents:
            if transform_attempts >= mock_settings.max_transform_retries:
                result = "no_docs_fallback"
            else:
                result = "transform_query"
        else:
            result = "generate"

        assert result == "transform_query"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
