# app/api/routes/comparison_routes.py
"""
Comparison-bezogene Endpoints

Endpoints zum Vergleichen von Antworten verschiedener Graph-Typen
für die gleiche Frage.
"""

import logging
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.schemas.comparison_schemas import (
    GraphComparisonResponse,
    ComparisonMetricsSummary,
    EvaluatedQuestionListItem,
    EvaluationWithGraphType,
    AcceptedAnswerInfo,
    RetrievedDocumentSchema,
    IterationMetricsSchema,
    PaginatedEvaluatedQuestionsResponse,
    RerunRequest,
    RerunResponse
)
from app.api.schemas.schemas import GraphType
from app.api.middleware import safe_error_handler
from app.database import get_db, SOQuestion
from app.services.comparison_service import get_comparison_service
from app.dependencies import get_batch_query_service
from app.services.batch_query_service import BatchQueryService
from app.services.job_manager import get_batch_query_manager

router = APIRouter(prefix="/comparisons", tags=["Comparisons"])
logger = logging.getLogger(__name__)


@router.get("/questions/{question_id}", response_model=GraphComparisonResponse)
async def get_comparison_for_question(
        question_id: int,
        db: Session = Depends(get_db)
):
    """
    Alle Evaluierungen für eine SO-Frage abrufen, gruppiert nach graph_type

    Args:
        question_id: StackOverflow Question ID (so_questions.stack_overflow_id)

    Returns:
        GraphComparisonResponse mit allen Evaluations gruppiert nach graph_type
    """
    try:
        comparison_service = get_comparison_service(db)
        result = comparison_service.get_comparisons_by_question_id(question_id)

        # Convert to response model
        question = result["question"]
        evaluations_by_graph_type = result["evaluations_by_graph_type"]

        # Convert evaluations to response format with additional details
        formatted_evals = {}
        for graph_type, evaluations in evaluations_by_graph_type.items():
            formatted_evals[graph_type] = []
            for eval in evaluations:
                details = comparison_service.get_evaluation_details(eval.id)

                retrieved_docs = None
                if details.get("retrieved_documents"):
                    retrieved_docs = [
                        RetrievedDocumentSchema(**doc)
                        for doc in details["retrieved_documents"]
                    ]

                iteration_metrics = None
                if details.get("iteration_metrics"):
                    iteration_metrics = IterationMetricsSchema(**details["iteration_metrics"])

                formatted_evals[graph_type].append(
                    EvaluationWithGraphType(
                        id=eval.id,
                        graph_type=eval.graph_type or "adaptive_rag",
                        generated_answer=eval.generated_answer,
                        bert_precision=eval.bert_precision,
                        bert_recall=eval.bert_recall,
                        bert_f1=eval.bert_f1,
                        processing_time_ms=eval.processing_time_ms,
                        manual_rating=eval.manual_rating,
                        created_at=eval.created_at,
                        graph_trace=details.get("graph_trace"),
                        node_timings=details.get("node_timings"),
                        rewritten_question=details.get("rewritten_question"),
                        retrieved_documents=retrieved_docs,
                        iteration_metrics=iteration_metrics
                    )
                )

        accepted_answer_info = None
        if result.get("accepted_answer"):
            answer = result["accepted_answer"]
            accepted_answer_info = AcceptedAnswerInfo(
                stack_overflow_id=answer.stack_overflow_id,
                body=answer.body,
                score=answer.score,
                owner_display_name=answer.owner_display_name,
                creation_date=answer.creation_date
            )

        return GraphComparisonResponse(
            question_id=question.stack_overflow_id,
            question_title=question.title,
            question_body=question.body or "",
            accepted_answer=accepted_answer_info,
            evaluations_by_graph_type=formatted_evals
        )

    except ValueError as e:
        logger.error(f"Question not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get comparison: {str(e)}")


@router.get("/questions/{question_id}/metrics", response_model=List[ComparisonMetricsSummary])
async def get_comparison_metrics(
        question_id: int,
        db: Session = Depends(get_db)
):
    """
    Aggregierte Metriken für eine SO-Frage über alle Graph-Typen

    Args:
        question_id: StackOverflow Question ID

    Returns:
        List of ComparisonMetricsSummary - Metriken pro Graph-Type
    """
    try:
        comparison_service = get_comparison_service(db)
        metrics = comparison_service.get_comparison_metrics(question_id)

        return [
            ComparisonMetricsSummary(**m)
            for m in metrics
        ]

    except Exception as e:
        logger.error(f"Error getting comparison metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/questions", response_model=PaginatedEvaluatedQuestionsResponse)
async def get_all_evaluated_questions(
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
        has_multiple_graph_types: bool = Query(False, description="Only questions with >1 graph type"),
        sort_by: str = Query("creation_date", description="Sort by: creation_date, score, evaluation_count, question_id"),
        sort_order: str = Query("desc", description="Sort order: asc, desc"),
        tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
        min_score: Optional[int] = Query(None, description="Minimum score filter"),
        title_search: Optional[str] = Query(None, description="Partial title search (case-insensitive)"),
        db: Session = Depends(get_db)
):
    """
    Liste aller SO-Fragen die evaluiert wurden (paginiert)

    Returns:
        Paginated list of evaluated questions with metadata
    """
    try:
        valid_sort_fields = ["creation_date", "score", "evaluation_count", "question_id"]
        if sort_by not in valid_sort_fields:
            sort_by = "creation_date"

        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"

        comparison_service = get_comparison_service(db)
        result = comparison_service.get_all_evaluated_questions(
            page=page,
            page_size=page_size,
            has_multiple_graph_types=has_multiple_graph_types,
            sort_by=sort_by,
            sort_order=sort_order,
            tags=tags,
            min_score=min_score,
            title_search=title_search
        )

        return PaginatedEvaluatedQuestionsResponse(
            items=[EvaluatedQuestionListItem(**q) for q in result["items"]],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"],
            has_next=result["has_next"],
            has_prev=result["has_prev"]
        )

    except Exception as e:
        logger.error(f"Error getting evaluated questions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get questions: {str(e)}")


@router.post("/questions/{question_id}/rerun", response_model=RerunResponse)
async def rerun_question_evaluation(
        question_id: int,
        request: RerunRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        service: BatchQueryService = Depends(get_batch_query_service)
):
    """
    Rerun evaluation for a specific question with selected graph types and collections.

    - Uses the same processing logic as batch queries
    - Returns a job_id for status polling via /batch-queries/{job_id}
    - Allows selecting different graph types and collections

    Args:
        question_id: StackOverflow Question ID (stack_overflow_id)
        request: RerunRequest with graph_types, collection_ids, session_id
    """
    valid_graph_types = {"adaptive_rag", "simple_rag", "pure_llm"}
    for gt in request.graph_types:
        if gt not in valid_graph_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid graph type: {gt}. Valid types: {valid_graph_types}"
            )

    question = db.query(SOQuestion).filter(
        SOQuestion.stack_overflow_id == question_id
    ).first()

    if not question:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")

    graph_type_enums = [GraphType(gt) for gt in request.graph_types]

    manager = get_batch_query_manager()

    total_runs = len(request.graph_types)
    job_id = manager.create_job(
        parameters={
            "question_ids": [question.stack_overflow_id],
            "session_id": request.session_id,
            "collection_ids": request.collection_ids,
            "graph_types": request.graph_types,
            "rerun_for_question_id": question_id,
            "question_title": question.title
        },
        progress_fields={
            "total_questions": total_runs,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "current_question_id": None,
            "current_question_title": None
        }
    )

    def update_progress(progress_update: Dict):
        manager.update_progress(job_id, progress_update)

    async def rerun_task():
        try:
            logger.info(f"Starting rerun job {job_id} for question {question_id} with {total_runs} graph types")

            from concurrent.futures import ThreadPoolExecutor
            import asyncio

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                def run_rerun():
                    return service.process_batch_sync(
                        job_id=job_id,
                        question_ids=[question.stack_overflow_id],
                        session_id=request.session_id,
                        collection_ids=request.collection_ids,
                        graph_types=graph_type_enums,
                        llm_config=None,
                        progress_callback=update_progress
                    )

                result = await loop.run_in_executor(executor, run_rerun)

            manager.complete_job(job_id)
            logger.info(f"Rerun job {job_id} completed: {result['summary']}")

        except Exception as e:
            logger.error(f"Rerun job {job_id} failed: {e}")
            manager.fail_job(job_id, str(e))

    background_tasks.add_task(rerun_task)

    return RerunResponse(
        job_id=job_id,
        message=f"Rerun started for question '{question.title[:50]}...' with {total_runs} graph type(s)",
        total_runs=total_runs,
        question_id=question_id,
        question_title=question.title
    )
