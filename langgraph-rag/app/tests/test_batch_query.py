"""
Konsolidierte Tests für Batch Query Funktionalität

Testet die Kernfunktionalität:
- Schema-Validierung
- Referenzantwort-Auswahl
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError


class TestBatchQuerySchemas:
    """Test Schema-Validierung"""

    def test_batch_request_max_50_questions(self):
        """Maximal 50 Fragen erlaubt"""
        from app.api.schemas.schemas import BatchQueryRequest

        # 50 sollte funktionieren
        request = BatchQueryRequest(
            question_ids=list(range(1, 51)),
            session_id="test"
        )
        assert len(request.question_ids) == 50

        # 51 sollte fehlschlagen
        with pytest.raises(ValidationError):
            BatchQueryRequest(
                question_ids=list(range(1, 52)),
                session_id="test"
            )

    def test_batch_request_requires_questions(self):
        """Mindestens eine Frage erforderlich"""
        from app.api.schemas.schemas import BatchQueryRequest

        with pytest.raises(ValidationError):
            BatchQueryRequest(question_ids=[], session_id="test")


class TestBatchQueryService:
    """Test Service-Logik"""

    def test_get_reference_answer_prefers_accepted(self):
        """Akzeptierte Antwort wird bevorzugt"""
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
        """Ohne akzeptierte Antwort -> höchster Score"""
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
        """Keine Antworten -> None"""
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
