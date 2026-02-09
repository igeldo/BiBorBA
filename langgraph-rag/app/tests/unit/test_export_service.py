"""
Unit tests for ExportService.

Tests the core export functionality:
- Reference answer filter (questions without reference_answer are excluded)
- Deduplication (only newest evaluation per key combination)
- Statistics respect deduplication
"""
import pytest
from datetime import datetime, timedelta

from app.evaluation.models import AnswerEvaluation
from app.database import SOQuestion, SOAnswer
from app.services.export_service import ExportService
from app.api.schemas.export_schemas import ExportFilterRequest


def _create_evaluation(db_session, **kwargs):
    """Helper to create an AnswerEvaluation with sensible defaults."""
    defaults = dict(
        question_text="Test question",
        generated_answer="Test answer",
        stackoverflow_question_id=1000,
        reference_answer="Reference answer text",
        graph_type="adaptive_rag",
        llm_model="gemma3:12b",
        embedding_model="nomic-embed-text",
        llm_correctness_model="gemma3:12b",
        llm_correctness_score=0.8,
        bert_f1=0.75,
        bert_precision=0.80,
        bert_recall=0.70,
        processing_time_ms=500,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
    )
    defaults.update(kwargs)
    eval_obj = AnswerEvaluation(**defaults)
    db_session.add(eval_obj)
    db_session.flush()
    return eval_obj


class TestReferenceAnswerFilter:
    """Tests that evaluations without reference_answer are excluded from exports."""

    def test_reference_answer_filter_excludes_no_reference(self, db_session, sample_questions):
        """
        Test that full export excludes evaluations without a reference answer.

        Assume:
            - 2 evaluations exist for the same question
            - One has a reference_answer, the other has None

        Expect:
            - Full export only contains the evaluation with a reference answer
        """
        q = sample_questions[0]

        _create_evaluation(
            db_session,
            stackoverflow_question_id=q.stack_overflow_id,
            reference_answer="This is a valid reference",
            bert_f1=0.9,
        )
        _create_evaluation(
            db_session,
            stackoverflow_question_id=q.stack_overflow_id,
            reference_answer=None,
            bert_f1=0.5,
        )
        db_session.commit()

        service = ExportService(db_session)
        result = service.fetch_full_export_data(filters=None)

        all_eval_ids = [
            e.evaluation_id
            for question in result.questions
            for e in question.evaluations
        ]
        assert len(all_eval_ids) == 1

    def test_reference_answer_filter_excludes_empty_string(self, db_session, sample_questions):
        """
        Test that full export excludes evaluations with empty-string reference_answer.

        Assume:
            - 2 evaluations: one with reference_answer="valid", one with reference_answer=""

        Expect:
            - Only the evaluation with non-empty reference_answer is exported
        """
        q = sample_questions[0]

        _create_evaluation(
            db_session,
            stackoverflow_question_id=q.stack_overflow_id,
            reference_answer="Valid reference",
            bert_f1=0.9,
        )
        _create_evaluation(
            db_session,
            stackoverflow_question_id=q.stack_overflow_id,
            reference_answer="",
            bert_f1=0.5,
        )
        db_session.commit()

        service = ExportService(db_session)
        result = service.fetch_full_export_data(filters=None)

        total_evals = sum(len(q.evaluations) for q in result.questions)
        assert total_evals == 1


class TestDeduplication:
    """Tests for the deduplicate_latest_only functionality."""

    def test_deduplicate_keeps_latest_only(self, db_session, sample_questions):
        """
        Test that deduplication keeps only the newest evaluation per key combination.

        Assume:
            - 3 evaluations for the same (question, llm, embedding, graph, evaluator)
              with different created_at timestamps

        Expect:
            - With deduplicate_latest_only=True, only the newest is returned
        """
        q = sample_questions[0]
        common = dict(
            stackoverflow_question_id=q.stack_overflow_id,
            reference_answer="Reference",
            graph_type="adaptive_rag",
            llm_model="gemma3:12b",
            embedding_model="nomic-embed-text",
            llm_correctness_model="gemma3:12b",
        )

        _create_evaluation(db_session, bert_f1=0.5, created_at=datetime(2025, 1, 1), **common)
        _create_evaluation(db_session, bert_f1=0.7, created_at=datetime(2025, 1, 2), **common)
        newest = _create_evaluation(db_session, bert_f1=0.9, created_at=datetime(2025, 1, 3), **common)
        db_session.commit()

        service = ExportService(db_session)
        filters = ExportFilterRequest(deduplicate_latest_only=True)
        result = service.fetch_full_export_data(filters=filters)

        all_evals = [e for question in result.questions for e in question.evaluations]
        assert len(all_evals) == 1
        assert all_evals[0].evaluation_id == newest.id
        assert all_evals[0].bert_scores.f1 == 0.9

    def test_deduplicate_different_combinations_kept(self, db_session, sample_questions):
        """
        Test that deduplication preserves evaluations with different key combinations.

        Assume:
            - 2 evaluations for the same question but different graph_type
            - deduplicate_latest_only=True

        Expect:
            - Both evaluations are kept (different keys)
        """
        q = sample_questions[0]
        common = dict(
            stackoverflow_question_id=q.stack_overflow_id,
            reference_answer="Reference",
            llm_model="gemma3:12b",
            embedding_model="nomic-embed-text",
            llm_correctness_model="gemma3:12b",
            created_at=datetime(2025, 1, 1),
        )

        _create_evaluation(db_session, graph_type="adaptive_rag", bert_f1=0.8, **common)
        _create_evaluation(db_session, graph_type="simple_rag", bert_f1=0.6, **common)
        db_session.commit()

        service = ExportService(db_session)
        filters = ExportFilterRequest(deduplicate_latest_only=True)
        result = service.fetch_full_export_data(filters=filters)

        all_evals = [e for question in result.questions for e in question.evaluations]
        assert len(all_evals) == 2
        graph_types = {e.graph_type for e in all_evals}
        assert graph_types == {"adaptive_rag", "simple_rag"}

    def test_no_dedup_without_flag(self, db_session, sample_questions):
        """
        Test that without deduplicate_latest_only all evaluations are returned.

        Assume:
            - 3 evaluations for the same key combination
            - deduplicate_latest_only=False (default)

        Expect:
            - All 3 evaluations are returned
        """
        q = sample_questions[0]
        common = dict(
            stackoverflow_question_id=q.stack_overflow_id,
            reference_answer="Reference",
            graph_type="adaptive_rag",
            llm_model="gemma3:12b",
            embedding_model="nomic-embed-text",
            llm_correctness_model="gemma3:12b",
        )

        _create_evaluation(db_session, bert_f1=0.5, created_at=datetime(2025, 1, 1), **common)
        _create_evaluation(db_session, bert_f1=0.7, created_at=datetime(2025, 1, 2), **common)
        _create_evaluation(db_session, bert_f1=0.9, created_at=datetime(2025, 1, 3), **common)
        db_session.commit()

        service = ExportService(db_session)
        filters = ExportFilterRequest(deduplicate_latest_only=False)
        result = service.fetch_full_export_data(filters=filters)

        all_evals = [e for question in result.questions for e in question.evaluations]
        assert len(all_evals) == 3


class TestStatisticsDeduplication:
    """Tests that statistics export respects deduplication."""

    def test_statistics_respects_deduplication(self, db_session, sample_questions):
        """
        Test that statistics are computed on deduplicated data.

        Assume:
            - 2 evaluations for the same key combination: bert_f1=0.5 (older), bert_f1=0.9 (newer)
            - deduplicate_latest_only=True

        Expect:
            - Statistics reflect only the newest evaluation (mean bert_f1 = 0.9)
        """
        q = sample_questions[0]
        common = dict(
            stackoverflow_question_id=q.stack_overflow_id,
            reference_answer="Reference",
            graph_type="adaptive_rag",
            llm_model="gemma3:12b",
            embedding_model="nomic-embed-text",
            llm_correctness_model="gemma3:12b",
        )

        _create_evaluation(db_session, bert_f1=0.5, created_at=datetime(2025, 1, 1), **common)
        _create_evaluation(db_session, bert_f1=0.9, created_at=datetime(2025, 1, 2), **common)
        db_session.commit()

        service = ExportService(db_session)
        filters = ExportFilterRequest(deduplicate_latest_only=True)
        result = service.fetch_statistics(
            filters=filters,
            group_by=["graph_type"],
            include_ci=False,
            include_std=False,
        )

        assert len(result.statistics) == 1
        stats = result.statistics[0]
        assert stats.n == 1
        assert stats.bert_f1_mean == pytest.approx(0.9)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
