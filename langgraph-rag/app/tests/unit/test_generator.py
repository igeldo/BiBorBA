"""
Unit tests for Generator Node.

Tests the answer generation functionality:
- Generates answer from documents
- Uses original_question instead of rewritten question
- generation_attempts is incremented
- total_iterations is incremented
- Temperature variation on retries
"""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document

from app.core.graph.nodes.generator import create_generator_node


class TestGenerator:
    """Tests for Generator Node functionality."""

    @patch('app.core.graph.nodes.generator.settings')
    def test_generate_produces_answer(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that generator produces an answer based on documents.

        Assume:
            - Documents contain SQL JOIN information
            - LLM chain is properly mocked

        Expect:
            - Result contains generated answer text
        """
        mock_settings.enable_retry_variation = False
        mock_settings.max_generation_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="SQL JOIN combines tables based on related columns.")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_answer_generator_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["documents"] = sample_documents

        generate = create_generator_node(mock_model_manager, mock_prompt_manager)
        result = generate(state)

        assert result["generation"] == "SQL JOIN combines tables based on related columns."

    @patch('app.core.graph.nodes.generator.settings')
    def test_uses_original_question_not_rewritten(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that generator uses original_question for answer generation.

        Assume:
            - State has different values for question and original_question

        Expect:
            - LLM chain is invoked with original_question
            - Both question values are preserved in result
        """
        mock_settings.enable_retry_variation = False
        mock_settings.max_generation_retries = 2

        mock_chain = MagicMock()
        captured_input = {}

        def capture_invoke(input_dict):
            captured_input.update(input_dict)
            return "Generated answer"

        mock_chain.invoke = capture_invoke

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_answer_generator_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["question"] = "Rewritten: SQL table combination"
        state["original_question"] = "What is SQL JOIN?"
        state["documents"] = sample_documents

        generate = create_generator_node(mock_model_manager, mock_prompt_manager)
        result = generate(state)

        assert captured_input.get("question") == "What is SQL JOIN?"
        assert result["original_question"] == "What is SQL JOIN?"

    @patch('app.core.graph.nodes.generator.settings')
    def test_generation_attempts_incremented(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that generation_attempts counter is incremented.

        Assume:
            - State has generation_attempts = 1

        Expect:
            - Result has generation_attempts = 2
        """
        mock_settings.enable_retry_variation = False
        mock_settings.max_generation_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="Answer")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_answer_generator_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["generation_attempts"] = 1
        state["documents"] = sample_documents

        generate = create_generator_node(mock_model_manager, mock_prompt_manager)
        result = generate(state)

        assert result["generation_attempts"] == 2

    @patch('app.core.graph.nodes.generator.settings')
    def test_total_iterations_incremented(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that total_iterations counter is incremented.

        Assume:
            - State has total_iterations = 5

        Expect:
            - Result has total_iterations = 6
        """
        mock_settings.enable_retry_variation = False
        mock_settings.max_generation_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="Answer")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_answer_generator_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["total_iterations"] = 5
        state["documents"] = sample_documents

        generate = create_generator_node(mock_model_manager, mock_prompt_manager)
        result = generate(state)

        assert result["total_iterations"] == 6

    @patch('app.core.graph.nodes.generator.settings')
    def test_temperature_variation_on_retry(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that temperature is increased on retries when enabled.

        Assume:
            - enable_retry_variation is True
            - retry_temperature_increment is 0.1
            - This is the second generation attempt (generation_attempts=1)
            - Base temperature is 0.0

        Expect:
            - Temperature is increased by 0.1 (0.0 + 0.1 = 0.1)
            - model_config in result reflects the increased temperature
        """
        mock_settings.enable_retry_variation = True
        mock_settings.retry_temperature_increment = 0.1
        mock_settings.max_generation_retries = 3

        captured_config = {}

        def capture_chat_model(name, **kwargs):
            captured_config.update(kwargs)
            return MagicMock()

        mock_model_manager.get_chat_model = capture_chat_model

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="Answer")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_prompt_manager.get_answer_generator_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["generation_attempts"] = 1
        state["model_config"] = {"temperature": 0.0}
        state["documents"] = sample_documents

        generate = create_generator_node(mock_model_manager, mock_prompt_manager)
        result = generate(state)

        assert captured_config.get("temperature") == 0.1
        assert result["model_config"]["temperature"] == 0.1

    @patch('app.core.graph.nodes.generator.settings')
    def test_temperature_capped_at_one(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that temperature is capped at 1.0.

        Assume:
            - High base temperature (0.7)
            - Third attempt (generation_attempts=2)
            - Increment of 0.5 per retry

        Expect:
            - Temperature is capped at 1.0 (not 1.7)
        """
        mock_settings.enable_retry_variation = True
        mock_settings.retry_temperature_increment = 0.5
        mock_settings.max_generation_retries = 5

        captured_config = {}

        def capture_chat_model(name, **kwargs):
            captured_config.update(kwargs)
            return MagicMock()

        mock_model_manager.get_chat_model = capture_chat_model

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="Answer")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_prompt_manager.get_answer_generator_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["generation_attempts"] = 2
        state["model_config"] = {"temperature": 0.7}
        state["documents"] = sample_documents

        generate = create_generator_node(mock_model_manager, mock_prompt_manager)
        result = generate(state)

        assert captured_config.get("temperature") == 1.0


class TestGeneratorEdgeCases:
    """Edge case tests for Generator."""

    @patch('app.core.graph.nodes.generator.settings')
    def test_empty_documents(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that empty document list is handled.

        Assume:
            - Documents list is empty

        Expect:
            - Generator still produces an answer
            - Documents in result is empty list
        """
        mock_settings.enable_retry_variation = False
        mock_settings.max_generation_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="Answer without documents")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_answer_generator_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["documents"] = []

        generate = create_generator_node(mock_model_manager, mock_prompt_manager)
        result = generate(state)

        assert result["generation"] == "Answer without documents"
        assert result["documents"] == []

    @patch('app.core.graph.nodes.generator.settings')
    def test_preserves_collection_ids(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that collection_ids are preserved in result.

        Assume:
            - State has collection_ids = [1, 2, 3]

        Expect:
            - Result has same collection_ids
        """
        mock_settings.enable_retry_variation = False
        mock_settings.max_generation_retries = 2

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="Answer")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_model_manager.get_chat_model.return_value = MagicMock()
        mock_prompt_manager.get_answer_generator_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["collection_ids"] = [1, 2, 3]
        state["documents"] = sample_documents

        generate = create_generator_node(mock_model_manager, mock_prompt_manager)
        result = generate(state)

        assert result["collection_ids"] == [1, 2, 3]

    @patch('app.core.graph.nodes.generator.settings')
    def test_no_temperature_variation_on_first_attempt(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state, sample_documents
    ):
        """
        Test that no temperature variation occurs on first attempt.

        Assume:
            - enable_retry_variation is True
            - This is the first attempt (generation_attempts=0)

        Expect:
            - Temperature remains at base value (0.0)
        """
        mock_settings.enable_retry_variation = True
        mock_settings.retry_temperature_increment = 0.2
        mock_settings.max_generation_retries = 3

        captured_config = {}

        def capture_chat_model(name, **kwargs):
            captured_config.update(kwargs)
            return MagicMock()

        mock_model_manager.get_chat_model = capture_chat_model

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="Answer")

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock())
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_prompt_manager.get_answer_generator_prompt.return_value = mock_prompt

        state = {**sample_graph_state}
        state["generation_attempts"] = 0
        state["model_config"] = {"temperature": 0.0}
        state["documents"] = sample_documents

        generate = create_generator_node(mock_model_manager, mock_prompt_manager)
        result = generate(state)

        assert captured_config.get("temperature") == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
