"""
Unit tests for Document Grader Node.

Tests the document relevance grading with confidence scores:
- Relevant documents with high confidence are accepted
- Relevant documents with low confidence are rejected
- Irrelevant documents are rejected
- String inputs are normalized to Document objects
- Iteration counter is incremented
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.documents import Document

from app.core.graph.nodes.document_grader import (
    create_document_grader_node,
    GradeDocuments
)


class TestDocumentGrader:
    """Tests for Document Grader Node functionality."""

    @patch('app.core.graph.nodes.document_grader.settings')
    def test_grade_relevant_document_high_confidence(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that a relevant document with high confidence is accepted.

        Assume:
            - Document contains relevant SQL JOIN information
            - LLM grades document as "yes" with confidence 0.8
            - Confidence threshold is 0.5

        Expect:
            - Document is kept in filtered results
            - total_iterations is incremented
        """
        mock_settings.document_grading_batch_size = 4
        mock_settings.document_grading_retry_attempts = 2
        mock_settings.document_grading_confidence_threshold = 0.5

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=GradeDocuments(
            binary_score="yes",
            confidence=0.8,
            reasoning="Document contains relevant SQL JOIN information"
        ))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_document_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = [Document(
            page_content="SQL JOIN combines rows from multiple tables.",
            metadata={"source": "test.pdf"}
        )]

        grade_documents = create_document_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_documents(state)

        assert len(result["documents"]) == 1
        assert result["total_iterations"] == 1

    @patch('app.core.graph.nodes.document_grader.settings')
    def test_grade_relevant_document_low_confidence(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that a relevant document with low confidence is rejected.

        Assume:
            - LLM grades document as "yes" but with confidence 0.3
            - Confidence threshold is 0.5

        Expect:
            - Document is rejected (not in filtered results)
        """
        mock_settings.document_grading_batch_size = 4
        mock_settings.document_grading_retry_attempts = 2
        mock_settings.document_grading_confidence_threshold = 0.5

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=GradeDocuments(
            binary_score="yes",
            confidence=0.3,
            reasoning="Possibly relevant but uncertain"
        ))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_document_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = [Document(
            page_content="Some content about databases.",
            metadata={"source": "test.pdf"}
        )]

        grade_documents = create_document_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_documents(state)

        assert len(result["documents"]) == 0

    @patch('app.core.graph.nodes.document_grader.settings')
    def test_grade_irrelevant_document(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that an irrelevant document is rejected.

        Assume:
            - Document content is unrelated to the question
            - LLM grades document as "no"

        Expect:
            - Document is rejected (not in filtered results)
        """
        mock_settings.document_grading_batch_size = 4
        mock_settings.document_grading_retry_attempts = 2
        mock_settings.document_grading_confidence_threshold = 0.5

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=GradeDocuments(
            binary_score="no",
            confidence=0.9,
            reasoning="Document is about cooking, not SQL"
        ))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_document_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = [Document(
            page_content="Recipe for chocolate cake.",
            metadata={"source": "cooking.pdf"}
        )]

        grade_documents = create_document_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_documents(state)

        assert len(result["documents"]) == 0

    @patch('app.core.graph.nodes.document_grader.settings')
    def test_string_input_normalized_to_document(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that string input is normalized to Document object.

        Assume:
            - Input documents is a string instead of Document object
            - LLM grades it as relevant

        Expect:
            - String is converted to Document object
            - Grading proceeds normally
            - Result contains Document object with page_content attribute
        """
        mock_settings.document_grading_batch_size = 4
        mock_settings.document_grading_retry_attempts = 2
        mock_settings.document_grading_confidence_threshold = 0.5

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=GradeDocuments(
            binary_score="yes",
            confidence=0.9,
            reasoning="Relevant content"
        ))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_document_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = "SQL JOIN documentation text"

        grade_documents = create_document_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_documents(state)

        assert len(result["documents"]) == 1
        assert hasattr(result["documents"][0], 'page_content')

    @patch('app.core.graph.nodes.document_grader.settings')
    def test_total_iterations_incremented(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that total_iterations counter is incremented.

        Assume:
            - State has total_iterations = 5

        Expect:
            - Result has total_iterations = 6
        """
        mock_settings.document_grading_batch_size = 4
        mock_settings.document_grading_retry_attempts = 2
        mock_settings.document_grading_confidence_threshold = 0.5

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=GradeDocuments(
            binary_score="yes",
            confidence=0.8,
            reasoning="Relevant"
        ))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_document_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["total_iterations"] = 5
        state["documents"] = [Document(page_content="Test", metadata={})]

        grade_documents = create_document_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_documents(state)

        assert result["total_iterations"] == 6

    @patch('app.core.graph.nodes.document_grader.settings')
    def test_preserves_original_question(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that original_question is preserved unchanged.

        Assume:
            - State has different values for question and original_question

        Expect:
            - Result preserves both values unchanged
        """
        mock_settings.document_grading_batch_size = 4
        mock_settings.document_grading_retry_attempts = 2
        mock_settings.document_grading_confidence_threshold = 0.5

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=GradeDocuments(
            binary_score="yes",
            confidence=0.8,
            reasoning="Relevant"
        ))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_document_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["question"] = "Rewritten question about SQL"
        state["original_question"] = "What is SQL JOIN?"
        state["documents"] = [Document(page_content="Test", metadata={})]

        grade_documents = create_document_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_documents(state)

        assert result["original_question"] == "What is SQL JOIN?"
        assert result["question"] == "Rewritten question about SQL"


class TestDocumentGraderEdgeCases:
    """Edge case tests for Document Grader."""

    @patch('app.core.graph.nodes.document_grader.settings')
    def test_empty_document_list(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that empty document list is handled correctly.

        Assume:
            - Input documents is an empty list

        Expect:
            - Result documents is empty list
            - total_iterations is still incremented
        """
        mock_settings.document_grading_batch_size = 4
        mock_settings.document_grading_retry_attempts = 2
        mock_settings.document_grading_confidence_threshold = 0.5

        state = {**sample_graph_state}
        state["documents"] = []

        grade_documents = create_document_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_documents(state)

        assert result["documents"] == []
        assert result["total_iterations"] == 1

    @patch('app.core.graph.nodes.document_grader.settings')
    def test_mixed_relevant_irrelevant_documents(
        self, mock_settings, mock_model_manager, mock_prompt_manager, sample_graph_state
    ):
        """
        Test that only relevant documents are kept from a mixed set.

        Assume:
            - Three documents: first relevant, second irrelevant, third relevant

        Expect:
            - Only the two relevant documents are in the result
        """
        mock_settings.document_grading_batch_size = 4
        mock_settings.document_grading_retry_attempts = 2
        mock_settings.document_grading_confidence_threshold = 0.5

        responses = [
            GradeDocuments(binary_score="yes", confidence=0.9, reasoning="Relevant"),
            GradeDocuments(binary_score="no", confidence=0.8, reasoning="Not relevant"),
            GradeDocuments(binary_score="yes", confidence=0.7, reasoning="Somewhat relevant"),
        ]
        response_iter = iter(responses)

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=lambda x: next(response_iter))
        mock_model_manager.get_structured_model.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.__or__ = MagicMock(return_value=mock_llm)
        mock_prompt_manager.get_document_grader_prompt.return_value = mock_chain

        state = {**sample_graph_state}
        state["documents"] = [
            Document(page_content="Doc 1 about SQL", metadata={"id": 1}),
            Document(page_content="Doc 2 about cooking", metadata={"id": 2}),
            Document(page_content="Doc 3 about databases", metadata={"id": 3}),
        ]

        grade_documents = create_document_grader_node(mock_model_manager, mock_prompt_manager)
        result = grade_documents(state)

        assert len(result["documents"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
