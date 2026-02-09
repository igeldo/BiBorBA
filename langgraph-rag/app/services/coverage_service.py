"""
Coverage service for finding missing evaluations.

Identifies questions that haven't been evaluated yet for a specific
configuration (LLM model, embedding model, graph type).
"""

import logging
from typing import Dict, List, Optional, Any

from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.database import SOQuestion, RetrievedDocument, CollectionConfiguration, CollectionQuestion
from app.evaluation.models import AnswerEvaluation
from app.config import (
    get_current_llm_model,
    get_current_embedding_model,
    get_current_evaluation_model
)

logger = logging.getLogger(__name__)


class CoverageService:
    """Service for analyzing evaluation coverage and finding missing questions."""

    def __init__(self, db: Session):
        self.db = db

    def get_current_config(self) -> Dict[str, str]:
        """Get current model configuration from settings."""
        return {
            "llm_model": get_current_llm_model(),
            "llm_correctness_model": get_current_evaluation_model(),
            "embedding_model": get_current_embedding_model()
        }

    def get_all_question_ids(self) -> List[int]:
        """Get all StackOverflow question IDs."""
        result = (
            self.db.query(SOQuestion.stack_overflow_id)
            .all()
        )
        return [r[0] for r in result]

    def get_evaluated_question_ids_for_pure_llm(
        self,
        llm_model: str,
        llm_correctness_model: str
    ) -> List[int]:
        """
        Get question IDs that have been evaluated for pure_llm graph type.

        For pure_llm, we only filter by llm_model and llm_correctness_model
        since no embedding/retrieval is involved.
        """
        result = (
            self.db.query(distinct(AnswerEvaluation.stackoverflow_question_id))
            .filter(AnswerEvaluation.stackoverflow_question_id.isnot(None))
            .filter(AnswerEvaluation.llm_model == llm_model)
            .filter(AnswerEvaluation.llm_correctness_model == llm_correctness_model)
            .filter(AnswerEvaluation.graph_type == "pure_llm")
            .all()
        )
        return [r[0] for r in result]

    def get_evaluated_question_ids_for_rag(
        self,
        llm_model: str,
        llm_correctness_model: str,
        embedding_model: str,
        graph_type: str
    ) -> List[int]:
        """
        Get question IDs that have been evaluated for RAG graph types.

        For adaptive_rag and simple_rag, we filter by llm_model, llm_correctness_model,
        and embedding_model. Uses a dual strategy:
        1. Primary: Direct match on AnswerEvaluation.embedding_model
        2. Fallback: If embedding_model is NULL, resolve via RetrievedDocument -> CollectionConfiguration
        """
        collection_subquery = (
            self.db.query(RetrievedDocument.evaluation_id)
            .join(CollectionConfiguration,
                  CollectionConfiguration.name == RetrievedDocument.collection_name)
            .filter(CollectionConfiguration.embedding_model == embedding_model)
            .distinct()
            .subquery()
        )

        result = (
            self.db.query(distinct(AnswerEvaluation.stackoverflow_question_id))
            .filter(AnswerEvaluation.stackoverflow_question_id.isnot(None))
            .filter(AnswerEvaluation.llm_model == llm_model)
            .filter(AnswerEvaluation.llm_correctness_model == llm_correctness_model)
            .filter(AnswerEvaluation.graph_type == graph_type)
            .filter(
                (AnswerEvaluation.embedding_model == embedding_model) |
                (AnswerEvaluation.embedding_model.is_(None) & AnswerEvaluation.id.in_(collection_subquery))
            )
            .all()
        )
        return [r[0] for r in result]

    def get_missing_questions_for_graph_type(
        self,
        llm_model: str,
        llm_correctness_model: str,
        embedding_model: str,
        graph_type: str
    ) -> List[int]:
        """
        Find questions that are missing evaluations for a specific configuration.

        For pure_llm:
            Filter by llm_model + llm_correctness_model only

        For adaptive_rag, simple_rag:
            Filter by llm_model + llm_correctness_model + embedding_model (via Collection)
        """
        all_question_ids = set(self.get_all_question_ids())

        if graph_type == "pure_llm":
            evaluated_ids = set(self.get_evaluated_question_ids_for_pure_llm(
                llm_model=llm_model,
                llm_correctness_model=llm_correctness_model
            ))
        else:
            evaluated_ids = set(self.get_evaluated_question_ids_for_rag(
                llm_model=llm_model,
                llm_correctness_model=llm_correctness_model,
                embedding_model=embedding_model,
                graph_type=graph_type
            ))

        missing_ids = all_question_ids - evaluated_ids
        return sorted(list(missing_ids))

    def get_missing_questions_summary(
        self,
        graph_types: Optional[List[str]] = None,
        exclude_collection_ids: Optional[List[int]] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "score",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Get a complete summary of missing questions across graph types.

        Args:
            graph_types: List of graph types to check (default: all)
            exclude_collection_ids: List of collection IDs - questions in these collections will be excluded
            page: Page number (1-indexed)
            page_size: Number of questions per page
            sort_by: Sort field (score, title, stack_overflow_id)
            sort_order: Sort order (asc, desc)

        Returns:
            {
                "current_config": {
                    "llm_model": "gemma3:12b",
                    "llm_correctness_model": "gemma3:12b",
                    "embedding_model": "embeddinggemma:latest"
                },
                "total_questions": 110,
                "missing_by_graph_type": {
                    "adaptive_rag": {
                        "count": 77,
                        "question_ids": [35111002, 35142129, ...]
                    },
                    ...
                },
                "questions": [...],
                "page": 1,
                "page_size": 50,
                "total_missing": 77,
                "total_pages": 2,
                "has_next": true,
                "has_prev": false
            }
        """
        if graph_types is None:
            graph_types = ["adaptive_rag", "simple_rag", "pure_llm"]

        config = self.get_current_config()
        all_question_ids = self.get_all_question_ids()
        total_questions = len(all_question_ids)

        excluded_question_ids: set = set()
        if exclude_collection_ids:
            excluded_questions = (
                self.db.query(CollectionQuestion.question_stack_overflow_id)
                .filter(CollectionQuestion.collection_id.in_(exclude_collection_ids))
                .distinct()
                .all()
            )
            excluded_question_ids = {q[0] for q in excluded_questions}

        missing_by_graph_type: Dict[str, Dict[str, Any]] = {}
        union_missing_ids: set = set()

        for graph_type in graph_types:
            missing_ids = self.get_missing_questions_for_graph_type(
                llm_model=config["llm_model"],
                llm_correctness_model=config["llm_correctness_model"],
                embedding_model=config["embedding_model"],
                graph_type=graph_type
            )
            if excluded_question_ids:
                missing_ids = [qid for qid in missing_ids if qid not in excluded_question_ids]
            missing_by_graph_type[graph_type] = {
                "count": len(missing_ids),
                "question_ids": missing_ids
            }
            union_missing_ids.update(missing_ids)

        total_missing = len(union_missing_ids)
        total_pages = (total_missing + page_size - 1) // page_size if total_missing > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1

        sort_column_map = {
            "score": SOQuestion.score,
            "title": SOQuestion.title,
            "stack_overflow_id": SOQuestion.stack_overflow_id
        }
        sort_column = sort_column_map.get(sort_by, SOQuestion.score)

        if sort_order.lower() == "asc":
            sort_column = sort_column.asc()
        else:
            sort_column = sort_column.desc()

        questions_details = []
        if union_missing_ids:
            offset = (page - 1) * page_size
            questions = (
                self.db.query(SOQuestion)
                .filter(SOQuestion.stack_overflow_id.in_(union_missing_ids))
                .order_by(sort_column)
                .offset(offset)
                .limit(page_size)
                .all()
            )
            for q in questions:
                tags = q.tags.split(',') if q.tags else []
                tags = [t.strip() for t in tags if t.strip()]

                collection_memberships = (
                    self.db.query(
                        CollectionConfiguration.id,
                        CollectionConfiguration.name,
                        CollectionConfiguration.collection_type,
                        CollectionQuestion.added_at
                    )
                    .join(CollectionQuestion, CollectionQuestion.collection_id == CollectionConfiguration.id)
                    .filter(CollectionQuestion.question_stack_overflow_id == q.stack_overflow_id)
                    .all()
                )

                questions_details.append({
                    "stack_overflow_id": q.stack_overflow_id,
                    "title": q.title,
                    "tags": tags,
                    "score": q.score or 0,
                    "collections": [
                        {
                            "collection_id": c[0],
                            "collection_name": c[1],
                            "collection_type": c[2],
                            "added_at": c[3].isoformat() if c[3] else None
                        }
                        for c in collection_memberships
                    ]
                })

        return {
            "current_config": config,
            "total_questions": total_questions,
            "missing_by_graph_type": missing_by_graph_type,
            "questions": questions_details,
            "page": page,
            "page_size": page_size,
            "total_missing": total_missing,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }


def get_coverage_service(db: Session) -> CoverageService:
    """Get CoverageService instance with database session."""
    return CoverageService(db)
