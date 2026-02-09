"""
Unit tests for Rewriter Node (Query Transformer).

Tests the question rewriting functionality:
- Produces new/better question
- original_question remains unchanged
- transform_attempts is incremented
- total_iterations is incremented
- State fields are preserved
"""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document

from app.core.graph.nodes.rewriter import create_rewriter_node


class TestRewriter:
    """Tests for Rewriter Node functionality."""

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_transform_produces_new_question(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that rewriter produces a rewritten question.

        Assume:
            - Original question is "What is SQL JOIN?"
            - LLM returns a rewritten version

        Expect:
            - Result question is different from input
            - Result contains the LLM-generated rewrite
        """
        mock_settings.max_transform_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(
            return_value="How do I combine data from multiple SQL tables using JOIN?"
        )

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["question"] = "What is SQL JOIN?"

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["question"] == "How do I combine data from multiple SQL tables using JOIN?"
        assert result["question"] != "What is SQL JOIN?"

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_original_question_preserved(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that original_question is preserved unchanged.

        Assume:
            - State has original_question different from question

        Expect:
            - original_question remains unchanged in result
            - question is updated to rewritten version
        """
        mock_settings.max_transform_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="Rewritten question")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["question"] = "Modified question"
        state["original_question"] = "Original user question"

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["original_question"] == "Original user question"
        assert result["question"] == "Rewritten question"

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_transform_attempts_incremented(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that transform_attempts counter is incremented.

        Assume:
            - State has transform_attempts = 1

        Expect:
            - Result has transform_attempts = 2
        """
        mock_settings.max_transform_retries = 3

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="New question")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["transform_attempts"] = 1

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["transform_attempts"] == 2

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_total_iterations_incremented(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that total_iterations counter is incremented.

        Assume:
            - State has total_iterations = 3

        Expect:
            - Result has total_iterations = 4
        """
        mock_settings.max_transform_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="New question")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["total_iterations"] = 3

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["total_iterations"] == 4


class TestRewriterEdgeCases:
    """Edge case tests for Rewriter."""

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_preserves_documents(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that documents are preserved in result.

        Assume:
            - State has documents from previous retrieval

        Expect:
            - Documents are unchanged in result
        """
        mock_settings.max_transform_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="New question")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["documents"] = sample_documents

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["documents"] == sample_documents

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_preserves_generation(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that existing generation is preserved in result.

        Assume:
            - State has a previous generation value

        Expect:
            - Generation is unchanged in result
        """
        mock_settings.max_transform_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="New question")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["generation"] = "Previous answer"

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["generation"] == "Previous answer"

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_preserves_model_config(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that model_config is preserved in result.

        Assume:
            - State has model_config with temperature and top_p

        Expect:
            - model_config is unchanged in result
        """
        mock_settings.max_transform_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="New question")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["model_config"] = {"temperature": 0.5, "top_p": 0.9}

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["model_config"] == {"temperature": 0.5, "top_p": 0.9}

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_preserves_collection_ids(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that collection_ids are preserved in result.

        Assume:
            - State has collection_ids = [1, 2, 3]

        Expect:
            - collection_ids are unchanged in result
        """
        mock_settings.max_transform_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="New question")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["collection_ids"] = [1, 2, 3]

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["collection_ids"] == [1, 2, 3]

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_preserves_generation_attempts(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that generation_attempts is preserved (not incremented).

        Assume:
            - State has generation_attempts = 1

        Expect:
            - generation_attempts remains 1 (not changed by rewriter)
        """
        mock_settings.max_transform_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="New question")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["generation_attempts"] = 1

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["generation_attempts"] == 1

    @patch('app.core.graph.nodes.rewriter.settings')
    def test_fallback_flags_reset(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that fallback flags are set to False.

        Assume:
            - Rewriter is called during normal graph execution

        Expect:
            - max_iterations_reached is False
            - no_relevant_docs_fallback is False
            - fallback_type is empty string
        """
        mock_settings.max_transform_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="New question")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_question_rewriter_prompt.return_value = mock_prompt

        state = {**sample_graph_state}

        transform_query = create_rewriter_node(mock_model_manager, mock_prompt_manager)
        result = transform_query(state)

        assert result["max_iterations_reached"] is False
        assert result["no_relevant_docs_fallback"] is False
        assert result["fallback_type"] == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
