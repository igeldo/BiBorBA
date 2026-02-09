"""
Service for comparing different graph types on the same questions

This service provides methods to:
- Get all evaluations for a question grouped by graph_type
- Calculate aggregated metrics for comparison
- List questions that have been evaluated with multiple graph types
"""

import logging
import math
from collections import defaultdict
from typing import Dict, Any, List, Optional

from sqlalchemy import func, desc, asc, null, cast, String
from sqlalchemy.orm import Session

from app.database import SOQuestion, GraphExecution, RetrievedDocument, CollectionConfiguration
from app.evaluation.models import AnswerEvaluation

logger = logging.getLogger(__name__)


class ComparisonService:
    """Service for query comparisons across graph types"""

    def __init__(self, db: Session):
        self.db = db

    def get_comparisons_by_question_id(
        self,
        stackoverflow_question_id: int
    ) -> Dict[str, Any]:
        """
        Fetch all evaluations for a SO question, grouped by graph_type

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

        question = self.db.query(SOQuestion).filter(
            SOQuestion.stack_overflow_id == stackoverflow_question_id
        ).first()

        if not question:
            raise ValueError(f"Question with id {stackoverflow_question_id} not found")

        evaluations = self.db.query(AnswerEvaluation).filter(
            AnswerEvaluation.stackoverflow_question_id == stackoverflow_question_id
        ).order_by(AnswerEvaluation.created_at.desc()).all()

        evaluations_by_graph_type = defaultdict(list)
        for evaluation in evaluations:
            graph_type = evaluation.graph_type or "adaptive_rag"
            evaluations_by_graph_type[graph_type].append(evaluation)

        metrics_summary = self._calculate_metrics_summary(evaluations_by_graph_type)

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
        Aggregated metrics for a SO question across all graph types

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

        results = self.db.query(
            AnswerEvaluation.graph_type,
            func.avg(AnswerEvaluation.bert_f1).label('avg_bert_f1'),
            func.avg(AnswerEvaluation.bert_precision).label('avg_bert_precision'),
            func.avg(AnswerEvaluation.bert_recall).label('avg_bert_recall'),
            func.avg(AnswerEvaluation.processing_time_ms).label('avg_processing_time_ms'),
            func.avg(AnswerEvaluation.confidence_score).label('avg_confidence_score'),
            func.avg(AnswerEvaluation.llm_correctness_score).label('avg_llm_correctness'),
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
                "avg_llm_correctness": float(row.avg_llm_correctness) if row.avg_llm_correctness else None,
                "avg_confidence_score": float(row.avg_confidence_score) if row.avg_confidence_score else None,
                "evaluation_count": row.evaluation_count,
                "latest_evaluation_date": row.latest_evaluation_date
            })

        return metrics

    def get_all_evaluated_questions(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "creation_date",
        sort_order: str = "desc",
        tags: Optional[str] = None,
        title_search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Liste aller SO-Fragen die mit mindestens einem Graph-Typ evaluiert wurden

        Args:
            page: Page number (1-indexed)
            page_size: Number of records per page
            sort_by: Field to sort by (creation_date, score, evaluation_count, question_id, adaptive_rag_f1, simple_rag_f1, pure_llm_f1)
            sort_order: Sort direction (asc, desc)
            tags: Comma-separated list of tags to filter by
            title_search: Partial title search (case-insensitive)

        Returns:
            Paginated response with items and metadata
        """
        logger.info(f"Getting evaluated questions (page={page}, page_size={page_size}, sort={sort_by} {sort_order})")

        subquery = self.db.query(
            AnswerEvaluation.stackoverflow_question_id,
            func.count(func.distinct(AnswerEvaluation.graph_type)).label('graph_type_count'),
            func.count(AnswerEvaluation.id).label('total_evaluations'),
            func.array_agg(func.distinct(AnswerEvaluation.graph_type)).label('graph_types')
        ).group_by(
            AnswerEvaluation.stackoverflow_question_id
        ).subquery()

        def make_arch_subquery(graph_type_value: str):
            return self.db.query(
                AnswerEvaluation.stackoverflow_question_id,
                func.avg(AnswerEvaluation.bert_f1).label('avg_f1')
            ).filter(
                AnswerEvaluation.graph_type == graph_type_value
            ).group_by(
                AnswerEvaluation.stackoverflow_question_id
            ).subquery()

        adaptive_rag_subq = make_arch_subquery("adaptive_rag")
        simple_rag_subq = make_arch_subquery("simple_rag")
        pure_llm_subq = make_arch_subquery("pure_llm")

        query = self.db.query(
            SOQuestion,
            subquery.c.graph_types,
            subquery.c.total_evaluations,
            subquery.c.graph_type_count,
            adaptive_rag_subq.c.avg_f1.label('adaptive_rag_f1'),
            simple_rag_subq.c.avg_f1.label('simple_rag_f1'),
            pure_llm_subq.c.avg_f1.label('pure_llm_f1')
        ).join(
            subquery,
            SOQuestion.stack_overflow_id == subquery.c.stackoverflow_question_id
        ).outerjoin(
            adaptive_rag_subq,
            SOQuestion.stack_overflow_id == adaptive_rag_subq.c.stackoverflow_question_id
        ).outerjoin(
            simple_rag_subq,
            SOQuestion.stack_overflow_id == simple_rag_subq.c.stackoverflow_question_id
        ).outerjoin(
            pure_llm_subq,
            SOQuestion.stack_overflow_id == pure_llm_subq.c.stackoverflow_question_id
        )

        if tags:
            tag_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
            for tag in tag_list:
                query = query.filter(func.lower(SOQuestion.tags).contains(tag))

        if title_search:
            query = query.filter(SOQuestion.title.ilike(f"%{title_search}%"))

        total = query.count()

        sort_func = desc if sort_order == "desc" else asc
        if sort_by == "score":
            query = query.order_by(sort_func(SOQuestion.score))
        elif sort_by == "evaluation_count":
            query = query.order_by(sort_func(subquery.c.total_evaluations))
        elif sort_by == "question_id":
            query = query.order_by(sort_func(SOQuestion.stack_overflow_id))
        elif sort_by == "adaptive_rag_f1":
            query = query.order_by(sort_func(adaptive_rag_subq.c.avg_f1).nulls_last())
        elif sort_by == "simple_rag_f1":
            query = query.order_by(sort_func(simple_rag_subq.c.avg_f1).nulls_last())
        elif sort_by == "pure_llm_f1":
            query = query.order_by(sort_func(pure_llm_subq.c.avg_f1).nulls_last())
        else:
            query = query.order_by(sort_func(SOQuestion.creation_date))

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        results = query.all()

        question_ids = [q[0].stack_overflow_id for q in results]

        avg_metrics = self.get_avg_metrics_by_architecture(question_ids) if question_ids else {}

        questions = []
        for question, graph_types, total_evals, graph_count, _, _, _ in results:
            tag_list = question.tags.split(',') if question.tags else []

            question_avg_metrics = avg_metrics.get(question.stack_overflow_id, {})
            metrics_by_architecture = None
            if question_avg_metrics:
                metrics_by_architecture = {
                    "adaptive_rag": question_avg_metrics.get("adaptive_rag"),
                    "simple_rag": question_avg_metrics.get("simple_rag"),
                    "pure_llm": question_avg_metrics.get("pure_llm")
                }

            questions.append({
                "question_id": question.stack_overflow_id,
                "question_title": question.title,
                "available_graph_types": [gt for gt in graph_types if gt],
                "total_evaluations": total_evals,
                "has_multiple_graph_types": graph_count > 1,
                "tags": tag_list,
                "score": question.score,
                "metrics_by_architecture": metrics_by_architecture
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

        evaluation = self.db.query(AnswerEvaluation).filter(
            AnswerEvaluation.id == evaluation_id
        ).first()

        if not evaluation:
            return details

        graph_execution = None

        if evaluation.graph_execution_id:
            graph_execution = self.db.query(GraphExecution).filter(
                GraphExecution.id == evaluation.graph_execution_id
            ).first()

        if not graph_execution and evaluation.session_id:
            graph_execution = self.db.query(GraphExecution).filter(
                GraphExecution.session_id == evaluation.session_id
            ).order_by(GraphExecution.started_at.desc()).first()

            if graph_execution:
                logger.debug(f"Found graph execution via session_id fallback for evaluation {evaluation_id}")

        if graph_execution:
            details["graph_trace"] = graph_execution.execution_path
            details["node_timings"] = graph_execution.node_timings

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

        embedding_model = evaluation.embedding_model
        if not embedding_model and retrieved_docs:
            first_collection_name = retrieved_docs[0].collection_name
            if first_collection_name:
                collection = self.db.query(CollectionConfiguration).filter(
                    CollectionConfiguration.name == first_collection_name
                ).first()
                if collection:
                    embedding_model = collection.embedding_model

        details["embedding_model"] = embedding_model

        return details

    def get_aggregated_statistics(
        self,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics across all evaluations, grouped by specified fields.

        Args:
            group_by: List of fields to group by. Options: 'graph_type', 'llm_model', 'embedding_model'
                     Default: ['graph_type']

        Returns:
            Dict with statistics list and metadata
        """
        if not group_by:
            group_by = ['graph_type']

        logger.info(f"Getting aggregated statistics grouped by: {group_by}")

        group_columns = []
        if 'graph_type' in group_by:
            group_columns.append(AnswerEvaluation.graph_type)
        if 'llm_model' in group_by:
            group_columns.append(AnswerEvaluation.llm_model)

        include_embedding = 'embedding_model' in group_by

        if include_embedding:
            query = self.db.query(
                AnswerEvaluation.graph_type,
                AnswerEvaluation.llm_model if 'llm_model' in group_by else cast(null(), String).label('llm_model'),
                func.coalesce(AnswerEvaluation.embedding_model, CollectionConfiguration.embedding_model).label('embedding_model'),
                func.count(func.distinct(AnswerEvaluation.id)).label('n'),
                func.avg(AnswerEvaluation.bert_f1).label('bert_f1_mean'),
                func.stddev(AnswerEvaluation.bert_f1).label('bert_f1_std'),
                func.avg(AnswerEvaluation.llm_correctness_score).label('llm_correctness_mean'),
                func.stddev(AnswerEvaluation.llm_correctness_score).label('llm_correctness_std'),
                func.avg(AnswerEvaluation.processing_time_ms).label('processing_time_ms_mean')
            ).outerjoin(
                RetrievedDocument, RetrievedDocument.evaluation_id == AnswerEvaluation.id
            ).outerjoin(
                CollectionConfiguration, RetrievedDocument.collection_name == CollectionConfiguration.name
            )

            group_cols = [AnswerEvaluation.graph_type]
            if 'llm_model' in group_by:
                group_cols.append(AnswerEvaluation.llm_model)
            group_cols.append(func.coalesce(AnswerEvaluation.embedding_model, CollectionConfiguration.embedding_model))

            query = query.group_by(*group_cols)
        else:
            select_cols = [
                AnswerEvaluation.graph_type,
                func.count(AnswerEvaluation.id).label('n'),
                func.avg(AnswerEvaluation.bert_f1).label('bert_f1_mean'),
                func.stddev(AnswerEvaluation.bert_f1).label('bert_f1_std'),
                func.avg(AnswerEvaluation.llm_correctness_score).label('llm_correctness_mean'),
                func.stddev(AnswerEvaluation.llm_correctness_score).label('llm_correctness_std'),
                func.avg(AnswerEvaluation.processing_time_ms).label('processing_time_ms_mean')
            ]

            if 'llm_model' in group_by:
                select_cols.insert(1, AnswerEvaluation.llm_model)
            else:
                select_cols.insert(1, cast(null(), String).label('llm_model'))

            query = self.db.query(*select_cols)

            group_cols = [AnswerEvaluation.graph_type]
            if 'llm_model' in group_by:
                group_cols.append(AnswerEvaluation.llm_model)

            query = query.group_by(*group_cols)

        results = query.all()

        total_evaluations = self.db.query(func.count(AnswerEvaluation.id)).scalar() or 0

        statistics = []
        for row in results:
            if include_embedding:
                stat = {
                    "graph_type": row.graph_type or "adaptive_rag",
                    "llm_model": row.llm_model if 'llm_model' in group_by else None,
                    "embedding_model": row.embedding_model,
                    "n": row.n,
                    "bert_f1_mean": float(row.bert_f1_mean) if row.bert_f1_mean else None,
                    "bert_f1_std": float(row.bert_f1_std) if row.bert_f1_std else None,
                    "llm_correctness_mean": float(row.llm_correctness_mean) if row.llm_correctness_mean else None,
                    "llm_correctness_std": float(row.llm_correctness_std) if row.llm_correctness_std else None,
                    "processing_time_ms_mean": float(row.processing_time_ms_mean) if row.processing_time_ms_mean else None
                }
            else:
                stat = {
                    "graph_type": row.graph_type or "adaptive_rag",
                    "llm_model": row.llm_model if 'llm_model' in group_by else None,
                    "embedding_model": None,
                    "n": row.n,
                    "bert_f1_mean": float(row.bert_f1_mean) if row.bert_f1_mean else None,
                    "bert_f1_std": float(row.bert_f1_std) if row.bert_f1_std else None,
                    "llm_correctness_mean": float(row.llm_correctness_mean) if row.llm_correctness_mean else None,
                    "llm_correctness_std": float(row.llm_correctness_std) if row.llm_correctness_std else None,
                    "processing_time_ms_mean": float(row.processing_time_ms_mean) if row.processing_time_ms_mean else None
                }
            statistics.append(stat)

        statistics.sort(key=lambda x: x['n'], reverse=True)

        logger.info(f"Found {len(statistics)} configuration groups with {total_evaluations} total evaluations")

        return {
            "statistics": statistics,
            "total_evaluations": total_evaluations,
            "group_by": group_by
        }

    def get_avg_metrics_by_architecture(
        self,
        question_ids: List[int]
    ) -> Dict[int, Dict[str, Dict[str, Optional[float]]]]:
        """
        Get the average metrics for each architecture for a list of questions.

        Args:
            question_ids: List of StackOverflow question IDs

        Returns:
            Dict mapping question_id -> architecture -> metrics
        """
        if not question_ids:
            return {}

        results = self.db.query(
            AnswerEvaluation.stackoverflow_question_id,
            AnswerEvaluation.graph_type,
            func.avg(AnswerEvaluation.bert_f1).label('avg_bert_f1'),
            func.avg(AnswerEvaluation.llm_correctness_score).label('avg_llm_correctness')
        ).filter(
            AnswerEvaluation.stackoverflow_question_id.in_(question_ids)
        ).group_by(
            AnswerEvaluation.stackoverflow_question_id,
            AnswerEvaluation.graph_type
        ).all()

        avg_metrics: Dict[int, Dict[str, Dict[str, Optional[float]]]] = {}
        for row in results:
            question_id = row.stackoverflow_question_id
            graph_type = row.graph_type or "adaptive_rag"

            if question_id not in avg_metrics:
                avg_metrics[question_id] = {}

            avg_metrics[question_id][graph_type] = {
                "avg_bert_f1": float(row.avg_bert_f1) if row.avg_bert_f1 else None,
                "avg_llm_correctness": float(row.avg_llm_correctness) if row.avg_llm_correctness else None
            }

        return avg_metrics

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


def get_comparison_service(db: Session) -> ComparisonService:
    """Get ComparisonService instance with database session"""
    return ComparisonService(db)
