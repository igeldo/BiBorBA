"""
Unit tests for Hallucination Grader Node.

Tests the batch-based grounding verification:
- Answer grounded in first batch returns True with early exit
- Answer not grounded after all batches returns False
- Early exit on successful grounding
- Empty documents returns False
"""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document

from app.core.graph.nodes.hallucination_grader import (
    create_hallucination_grader_node,
    GradeHallucinations
)


class TestHallucinationGrader:
    """Tests for Hallucination Grader Node functionality."""

    @patch('app.core.graph.nodes.hallucination_grader.settings')
    def test_grounded_in_first_batch(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that answer grounded in first batch returns True with early exit.

        Assume:
            - Generation is grounded in the first batch of documents
            - LLM returns "yes" for grounding check

        Expect:
            - is_grounded is True
            - LLM is called only once (early exit)
        """
        mock_settings.hallucination_batch_size = 3

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=GradeHallucinations(binary_score="yes"))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_hallucination_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = sample_documents
        state["generation"] = "SQL JOIN is used to combine tables."

        grade_hallucination = create_hallucination_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_hallucination(state)

        assert result["is_grounded"] is True
        assert mock_llm.invoke.call_count == 1

    @patch('app.core.graph.nodes.hallucination_grader.settings')
    def test_not_grounded_after_all_batches(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that answer not grounded in any batch returns False.

        Assume:
            - Generation is not grounded in any document batch
            - LLM returns "no" for all batches

        Expect:
            - is_grounded is False
            - All batches are checked (2 batches for 3 docs with batch_size=2)
        """
        mock_settings.hallucination_batch_size = 2

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=GradeHallucinations(binary_score="no"))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_hallucination_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = sample_documents
        state["generation"] = "Hallucinated answer not in documents."

        grade_hallucination = create_hallucination_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_hallucination(state)

        assert result["is_grounded"] is False
        assert mock_llm.invoke.call_count == 2

    @patch('app.core.graph.nodes.hallucination_grader.settings')
    def test_early_exit_on_grounding(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that grading stops after first successful batch.

        Assume:
            - First batch returns "no", second batch returns "yes"
            - There are 3 documents with batch_size=1

        Expect:
            - is_grounded is True
            - Only 2 calls made (stops after finding grounding)
        """
        mock_settings.hallucination_batch_size = 1

        responses = [
            GradeHallucinations(binary_score="no"),
            GradeHallucinations(binary_score="yes"),
            GradeHallucinations(binary_score="no"),
        ]
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(side_effect=responses)
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_hallucination_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = [
            Document(page_content="Doc 1", metadata={}),
            Document(page_content="Doc 2 with grounding info", metadata={}),
            Document(page_content="Doc 3", metadata={}),
        ]
        state["generation"] = "Answer based on Doc 2."

        grade_hallucination = create_hallucination_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_hallucination(state)

        assert result["is_grounded"] is True
        assert mock_llm.invoke.call_count == 2

    @patch('app.core.graph.nodes.hallucination_grader.settings')
    def test_empty_documents_not_grounded(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that empty document list results in not grounded.

        Assume:
            - Documents list is empty

        Expect:
            - is_grounded is False
        """
        mock_settings.hallucination_batch_size = 3

        state = {**sample_graph_state}
        state["documents"] = []
        state["generation"] = "Some answer without documents."

        grade_hallucination = create_hallucination_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_hallucination(state)

        assert result["is_grounded"] is False


class TestHallucinationGraderEdgeCases:
    """Edge case tests for Hallucination Grader."""

    @patch('app.core.graph.nodes.hallucination_grader.settings')
    def test_llm_error_continues_to_next_batch(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that LLM error skips batch and continues to next one.

        Assume:
            - First batch throws an exception
            - Second batch returns "yes"

        Expect:
            - is_grounded is True (found in second batch)
            - Both calls are made
        """
        mock_settings.hallucination_batch_size = 1

        responses = [
            Exception("LLM Error"),
            GradeHallucinations(binary_score="yes"),
        ]
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(side_effect=responses)
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_hallucination_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = [
            Document(page_content="Doc 1", metadata={}),
            Document(page_content="Doc 2", metadata={}),
        ]
        state["generation"] = "Answer text."

        grade_hallucination = create_hallucination_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_hallucination(state)

        assert result["is_grounded"] is True
        assert mock_llm.invoke.call_count == 2

    @patch('app.core.graph.nodes.hallucination_grader.settings')
    def test_single_document_single_batch(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that single document is processed as one batch.

        Assume:
            - Only one document in the list
            - Batch size is 3

        Expect:
            - Document is processed correctly
            - Only one LLM call is made
        """
        mock_settings.hallucination_batch_size = 3

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=GradeHallucinations(binary_score="yes"))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_hallucination_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = [Document(page_content="Single doc", metadata={})]
        state["generation"] = "Answer based on single doc."

        grade_hallucination = create_hallucination_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_hallucination(state)

        assert result["is_grounded"] is True
        assert mock_llm.invoke.call_count == 1

    @patch('app.core.graph.nodes.hallucination_grader.settings')
    def test_case_insensitive_score(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that binary_score is checked case-insensitively.

        Assume:
            - LLM returns "YES" instead of "yes"

        Expect:
            - is_grounded is True (case-insensitive check)
        """
        mock_settings.hallucination_batch_size = 3

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=GradeHallucinations(binary_score="YES"))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_hallucination_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = sample_documents
        state["generation"] = "Answer text."

        grade_hallucination = create_hallucination_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_hallucination(state)

        assert result["is_grounded"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
