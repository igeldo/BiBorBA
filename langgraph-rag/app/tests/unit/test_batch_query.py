"""
Unit tests for Batch Query functionality.

Tests the core functionality:
- Schema validation for batch requests
- Reference answer selection logic
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError


class TestBatchQuerySchemas:
    """Tests for batch query schema validation."""

    def test_batch_request_max_50_questions(self):
        """
        Test that batch request accepts maximum 50 questions.

        Assume:
            - BatchQueryRequest schema has max_length=50 for question_ids

        Expect:
            - Request with 50 questions succeeds
            - Request with 51 questions raises ValidationError
        """
        from app.api.schemas.schemas import BatchQueryRequest

        request = BatchQueryRequest(
            question_ids=list(range(1, 51)),
            session_id="test"
        )
        assert len(request.question_ids) == 50

        with pytest.raises(ValidationError):
            BatchQueryRequest(
                question_ids=list(range(1, 52)),
                session_id="test"
            )

    def test_batch_request_requires_questions(self):
        """
        Test that batch request requires at least one question.

        Assume:
            - BatchQueryRequest schema has min_length=1 for question_ids

        Expect:
            - Request with empty question_ids raises ValidationError
        """
        from app.api.schemas.schemas import BatchQueryRequest

        with pytest.raises(ValidationError):
            BatchQueryRequest(question_ids=[], session_id="test")


class TestBatchQueryService:
    """Tests for BatchQueryService logic."""

    def test_get_reference_answer_prefers_accepted(self):
        """
        Test that accepted answer is preferred over higher-scored non-accepted answers.

        Assume:
            - Question has two answers: one with score=100 (not accepted),
              one with score=50 (accepted)

        Expect:
            - _get_reference_answer returns the accepted answer body
        """
        with patch('app.services.batch_query_service.get_graph_service'), \
             patch('app.services.batch_query_service.SessionLocal') as mock_session, \
             patch('app.services.batch_query_service.StackOverflowConnector'), \
             patch('app.services.batch_query_service.get_evaluation_service'):

            mock_session.return_value = MagicMock()

            from app.services.batch_query_service import BatchQueryService
            service = BatchQueryService()

            question_data = {
                "answers": [
                    {"body": "High score", "score": 100, "is_accepted": False},
                    {"body": "Accepted", "score": 50, "is_accepted": True},
                ]
            }

            result = service._get_reference_answer(question_data)
            assert result == "Accepted"

    def test_get_reference_answer_falls_back_to_highest_score(self):
        """
        Test that highest-scored answer is selected when no accepted answer exists.

        Assume:
            - Question has two answers, neither is accepted
            - One has score=5, other has score=100

        Expect:
            - _get_reference_answer returns the answer with highest score
        """
        with patch('app.services.batch_query_service.get_graph_service'), \
             patch('app.services.batch_query_service.SessionLocal') as mock_session, \
             patch('app.services.batch_query_service.StackOverflowConnector'), \
             patch('app.services.batch_query_service.get_evaluation_service'):

            mock_session.return_value = MagicMock()

            from app.services.batch_query_service import BatchQueryService
            service = BatchQueryService()

            question_data = {
                "answers": [
                    {"body": "Low score", "score": 5, "is_accepted": False},
                    {"body": "High score", "score": 100, "is_accepted": False},
                ]
            }

            result = service._get_reference_answer(question_data)
            assert result == "High score"

    def test_get_reference_answer_returns_none_when_no_answers(self):
        """
        Test that None is returned when question has no answers.

        Assume:
            - Question has empty answers list

        Expect:
            - _get_reference_answer returns None
        """
        with patch('app.services.batch_query_service.get_graph_service'), \
             patch('app.services.batch_query_service.SessionLocal') as mock_session, \
             patch('app.services.batch_query_service.StackOverflowConnector'), \
             patch('app.services.batch_query_service.get_evaluation_service'):

            mock_session.return_value = MagicMock()

            from app.services.batch_query_service import BatchQueryService
            service = BatchQueryService()
            result = service._get_reference_answer({"answers": []})
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
