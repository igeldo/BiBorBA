# services/comparison_service.py
"""
Service for comparing different graph types on the same questions

This service provides methods to:
- Get all evaluations for a question grouped by graph_type
- Calculate aggregated metrics for comparison
- List questions that have been evaluated with multiple graph types
"""

import logging
import math
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from app.database import SOQuestion, GraphExecution, RetrievedDocument
from app.evaluation.models import AnswerEvaluation

logger = logging.getLogger(__name__)


class ComparisonService:
    """Service für Query-Vergleiche über Graph-Typen"""

    def __init__(self, db: Session):
        self.db = db

    def get_comparisons_by_question_id(
        self,
        stackoverflow_question_id: int
    ) -> Dict[str, Any]:
        """
        Alle Evaluierungen für eine SO-Frage abrufen, gruppiert nach graph_type

        Args:
            stackoverflow_question_id: ID of the StackOverflow question

        Returns:
            Dict with question details and evaluations grouped by graph_type:
            {
                "question": SOQuestion object,
                "evaluations_by_graph_type": {
                    "adaptive_rag": [AnswerEvaluation, ...],
                    "simple_rag": [...],
                    "pure_llm": [...]
                },
                "metrics_summary": {...}
            }
        """
        logger.info(f"Getting comparisons for question {stackoverflow_question_id}")

        # Get the question
        question = self.db.query(SOQuestion).filter(
            SOQuestion.stack_overflow_id == stackoverflow_question_id
        ).first()

        if not question:
            raise ValueError(f"Question with id {stackoverflow_question_id} not found")

        # Get all evaluations for this question
        evaluations = self.db.query(AnswerEvaluation).filter(
            AnswerEvaluation.stackoverflow_question_id == stackoverflow_question_id
        ).order_by(AnswerEvaluation.created_at.desc()).all()

        # Group by graph_type
        evaluations_by_graph_type = defaultdict(list)
        for evaluation in evaluations:
            graph_type = evaluation.graph_type or "adaptive_rag"  # Default for old data
            evaluations_by_graph_type[graph_type].append(evaluation)

        # Calculate metrics summary
        metrics_summary = self._calculate_metrics_summary(evaluations_by_graph_type)

        # Find accepted answer
        accepted_answer = None
        if question.answers:
            for answer in question.answers:
                if answer.is_accepted:
                    accepted_answer = answer
                    break

        return {
            "question": question,
            "evaluations_by_graph_type": dict(evaluations_by_graph_type),
            "metrics_summary": metrics_summary,
            "accepted_answer": accepted_answer
        }

    def get_comparison_metrics(
        self,
        stackoverflow_question_id: int
    ) -> List[Dict[str, Any]]:
        """
        Aggregierte Metriken für eine SO-Frage über alle Graph-Typen

        Args:
            stackoverflow_question_id: ID of the StackOverflow question

        Returns:
            List of metric summaries per graph_type:
            [
                {
                    "graph_type": "adaptive_rag",
                    "avg_bert_f1": 0.85,
                    "avg_processing_time_ms": 2341,
                    "evaluation_count": 3,
                    "latest_evaluation_date": datetime
                },
                ...
            ]
        """
        logger.info(f"Getting comparison metrics for question {stackoverflow_question_id}")

        # Query evaluations grouped by graph_type
        results = self.db.query(
            AnswerEvaluation.graph_type,
            func.avg(AnswerEvaluation.bert_f1).label('avg_bert_f1'),
            func.avg(AnswerEvaluation.bert_precision).label('avg_bert_precision'),
            func.avg(AnswerEvaluation.bert_recall).label('avg_bert_recall'),
            func.avg(AnswerEvaluation.processing_time_ms).label('avg_processing_time_ms'),
            func.avg(AnswerEvaluation.confidence_score).label('avg_confidence_score'),
            func.count(AnswerEvaluation.id).label('evaluation_count'),
            func.max(AnswerEvaluation.created_at).label('latest_evaluation_date')
        ).filter(
            AnswerEvaluation.stackoverflow_question_id == stackoverflow_question_id
        ).group_by(
            AnswerEvaluation.graph_type
        ).all()

        metrics = []
        for row in results:
            metrics.append({
                "graph_type": row.graph_type or "adaptive_rag",
                "avg_bert_f1": float(row.avg_bert_f1) if row.avg_bert_f1 else None,
                "avg_bert_precision": float(row.avg_bert_precision) if row.avg_bert_precision else None,
                "avg_bert_recall": float(row.avg_bert_recall) if row.avg_bert_recall else None,
                "avg_processing_time_ms": float(row.avg_processing_time_ms) if row.avg_processing_time_ms else None,
                "avg_confidence_score": float(row.avg_confidence_score) if row.avg_confidence_score else None,
                "evaluation_count": row.evaluation_count,
                "latest_evaluation_date": row.latest_evaluation_date
            })

        return metrics

    def get_all_evaluated_questions(
        self,
        page: int = 1,
        page_size: int = 20,
        has_multiple_graph_types: bool = False,
        sort_by: str = "creation_date",
        sort_order: str = "desc",
        tags: Optional[str] = None,
        min_score: Optional[int] = None,
        title_search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Liste aller SO-Fragen die mit mindestens einem Graph-Typ evaluiert wurden

        Args:
            page: Page number (1-indexed)
            page_size: Number of records per page
            has_multiple_graph_types: If True, only return questions evaluated with >1 graph type
            sort_by: Field to sort by (creation_date, score, evaluation_count, question_id)
            sort_order: Sort direction (asc, desc)
            tags: Comma-separated list of tags to filter by
            min_score: Minimum score filter
            title_search: Partial title search (case-insensitive)

        Returns:
            Paginated response with items and metadata
        """
        logger.info(f"Getting evaluated questions (page={page}, page_size={page_size}, sort={sort_by} {sort_order})")

        # Subquery to get distinct graph types per question
        subquery = self.db.query(
            AnswerEvaluation.stackoverflow_question_id,
            func.count(func.distinct(AnswerEvaluation.graph_type)).label('graph_type_count'),
            func.count(AnswerEvaluation.id).label('total_evaluations'),
            func.array_agg(func.distinct(AnswerEvaluation.graph_type)).label('graph_types')
        ).group_by(
            AnswerEvaluation.stackoverflow_question_id
        ).subquery()

        # Main query joining with questions
        query = self.db.query(
            SOQuestion,
            subquery.c.graph_types,
            subquery.c.total_evaluations,
            subquery.c.graph_type_count
        ).join(
            subquery,
            SOQuestion.stack_overflow_id == subquery.c.stackoverflow_question_id
        )

        # Filter for multiple graph types if requested
        if has_multiple_graph_types:
            query = query.filter(subquery.c.graph_type_count > 1)

        # Tag filter
        if tags:
            tag_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
            for tag in tag_list:
                query = query.filter(func.lower(SOQuestion.tags).contains(tag))

        # Min score filter
        if min_score is not None:
            query = query.filter(SOQuestion.score >= min_score)

        # Title search filter (case-insensitive partial match)
        if title_search:
            query = query.filter(SOQuestion.title.ilike(f"%{title_search}%"))

        # Get total count before pagination
        total = query.count()

        # Sorting
        sort_func = desc if sort_order == "desc" else asc
        if sort_by == "score":
            query = query.order_by(sort_func(SOQuestion.score))
        elif sort_by == "evaluation_count":
            query = query.order_by(sort_func(subquery.c.total_evaluations))
        elif sort_by == "question_id":
            query = query.order_by(sort_func(SOQuestion.stack_overflow_id))
        else:  # default: creation_date
            query = query.order_by(sort_func(SOQuestion.creation_date))

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        results = query.all()

        questions = []
        for question, graph_types, total_evals, graph_count in results:
            # Parse tags (stored as comma-separated string)
            tag_list = question.tags.split(',') if question.tags else []

            questions.append({
                "question_id": question.stack_overflow_id,
                "question_title": question.title,
                "available_graph_types": [gt for gt in graph_types if gt],  # Filter None
                "total_evaluations": total_evals,
                "has_multiple_graph_types": graph_count > 1,
                "tags": tag_list,
                "score": question.score
            })

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        logger.info(f"Found {len(questions)} evaluated questions (page {page}/{total_pages}, total={total})")

        return {
            "items": questions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }

    def get_evaluation_details(self, evaluation_id: int) -> Dict[str, Any]:
        """
        Get detailed information for a single evaluation including:
        - Graph execution data (trace, node_timings)
        - Retrieved documents

        Args:
            evaluation_id: ID of the evaluation

        Returns:
            Dict with graph_trace, node_timings, retrieved_documents
        """
        details = {
            "graph_trace": None,
            "node_timings": None,
            "rewritten_question": None,
            "retrieved_documents": [],
            "iteration_metrics": None
        }

        # Get evaluation to find graph_execution_id
        evaluation = self.db.query(AnswerEvaluation).filter(
            AnswerEvaluation.id == evaluation_id
        ).first()

        if not evaluation:
            return details

        # Get graph execution data if available
        graph_execution = None

        if evaluation.graph_execution_id:
            # Direct lookup via foreign key
            graph_execution = self.db.query(GraphExecution).filter(
                GraphExecution.id == evaluation.graph_execution_id
            ).first()

        # Fallback: Lookup via session_id for legacy data without graph_execution_id
        if not graph_execution and evaluation.session_id:
            graph_execution = self.db.query(GraphExecution).filter(
                GraphExecution.session_id == evaluation.session_id
            ).order_by(GraphExecution.started_at.desc()).first()

            if graph_execution:
                logger.debug(f"Found graph execution via session_id fallback for evaluation {evaluation_id}")

        if graph_execution:
            details["graph_trace"] = graph_execution.execution_path
            details["node_timings"] = graph_execution.node_timings

        # Get retrieved documents
        retrieved_docs = self.db.query(RetrievedDocument).filter(
            RetrievedDocument.evaluation_id == evaluation_id
        ).all()

        if retrieved_docs:
            details["retrieved_documents"] = [
                {
                    "id": doc.id,
                    "source": doc.source,
                    "title": doc.title,
                    "content_preview": doc.content_preview or "",
                    "full_content": doc.full_content,
                    "relevance_score": doc.relevance_score,
                    "collection_name": doc.collection_name,
                    "metadata": doc.document_metadata
                }
                for doc in retrieved_docs
            ]

        return details

    def _calculate_metrics_summary(
        self,
        evaluations_by_graph_type: Dict[str, List[AnswerEvaluation]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate aggregated metrics for each graph type

        Args:
            evaluations_by_graph_type: Evaluations grouped by graph type

        Returns:
            Dict mapping graph_type to metrics summary
        """
        summary = {}

        for graph_type, evaluations in evaluations_by_graph_type.items():
            if not evaluations:
                continue

            # Calculate averages
            bert_f1_scores = [e.bert_f1 for e in evaluations if e.bert_f1 is not None]
            bert_precision_scores = [e.bert_precision for e in evaluations if e.bert_precision is not None]
            bert_recall_scores = [e.bert_recall for e in evaluations if e.bert_recall is not None]
            processing_times = [e.processing_time_ms for e in evaluations if e.processing_time_ms is not None]
            confidence_scores = [e.confidence_score for e in evaluations if e.confidence_score is not None]

            summary[graph_type] = {
                "evaluation_count": len(evaluations),
                "avg_bert_f1": sum(bert_f1_scores) / len(bert_f1_scores) if bert_f1_scores else None,
                "avg_bert_precision": sum(bert_precision_scores) / len(bert_precision_scores) if bert_precision_scores else None,
                "avg_bert_recall": sum(bert_recall_scores) / len(bert_recall_scores) if bert_recall_scores else None,
                "avg_processing_time_ms": sum(processing_times) / len(processing_times) if processing_times else None,
                "avg_confidence_score": sum(confidence_scores) / len(confidence_scores) if confidence_scores else None,
                "latest_evaluation": max(evaluations, key=lambda e: e.created_at),
                "latest_evaluation_date": max(e.created_at for e in evaluations)
            }

        return summary


# Dependency for FastAPI
def get_comparison_service(db: Session) -> ComparisonService:
    """Get ComparisonService instance with database session"""
    return ComparisonService(db)
