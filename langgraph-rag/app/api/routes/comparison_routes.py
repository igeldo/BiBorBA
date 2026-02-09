"""
Comparison-related endpoints.

Endpoints for comparing answers from different graph types
for the same question.
"""

import logging
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.schemas.comparison_schemas import (
    GraphComparisonResponse,
    ComparisonMetricsSummary,
    EvaluationWithGraphType,
    AcceptedAnswerInfo,
    RetrievedDocumentSchema,
    IterationMetricsSchema,
    RerunRequest,
    RerunResponse,
    AggregatedStatisticsResponse,
    ConfigurationStatistics,
    EvaluatedQuestionListItemExtended,
    PaginatedEvaluatedQuestionsExtendedResponse,
    ArchitectureMetrics,
    MetricsByArchitecture
)
from app.api.schemas.schemas import GraphType
from app.database import get_db, SOQuestion
from app.dependencies import get_batch_query_service
from app.services.batch_query_service import BatchQueryService
from app.services.comparison_service import get_comparison_service
from app.services.job_manager import get_batch_query_manager

router = APIRouter(prefix="/comparisons", tags=["Comparisons"])
logger = logging.getLogger(__name__)


@router.get("/aggregated-statistics", response_model=AggregatedStatisticsResponse)
async def get_aggregated_statistics(
        group_by: Optional[str] = Query(
            "graph_type",
            description="Comma-separated list of fields to group by: graph_type, llm_model, embedding_model"
        ),
        db: Session = Depends(get_db)
):
    """
    Get aggregated statistics across all evaluations.

    Groups statistics by the specified fields and returns mean/std for key metrics.

    Args:
        group_by: Comma-separated grouping fields (default: graph_type)

    Returns:
        AggregatedStatisticsResponse with statistics per configuration
    """
    try:
        group_by_list = [g.strip() for g in group_by.split(',') if g.strip()]
        valid_fields = {'graph_type', 'llm_model', 'embedding_model'}
        group_by_list = [g for g in group_by_list if g in valid_fields]

        if not group_by_list:
            group_by_list = ['graph_type']

        comparison_service = get_comparison_service(db)
        result = comparison_service.get_aggregated_statistics(group_by=group_by_list)

        return AggregatedStatisticsResponse(
            statistics=[ConfigurationStatistics(**stat) for stat in result["statistics"]],
            total_evaluations=result["total_evaluations"],
            group_by=result["group_by"]
        )

    except Exception as e:
        logger.error(f"Error getting aggregated statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/questions/{question_id}", response_model=GraphComparisonResponse)
async def get_comparison_for_question(
        question_id: int,
        db: Session = Depends(get_db)
):
    """
    Fetch all evaluations for a SO question, grouped by graph_type

    Args:
        question_id: StackOverflow Question ID (so_questions.stack_overflow_id)

    Returns:
        GraphComparisonResponse with all evaluations grouped by graph_type
    """
    try:
        comparison_service = get_comparison_service(db)
        result = comparison_service.get_comparisons_by_question_id(question_id)

        question = result["question"]
        evaluations_by_graph_type = result["evaluations_by_graph_type"]

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
                        iteration_metrics=iteration_metrics,
                        llm_model=eval.llm_model,
                        embedding_model=details.get("embedding_model"),
                        llm_correctness_score=eval.llm_correctness_score,
                        llm_correctness_model=eval.llm_correctness_model
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
    Aggregated metrics for a SO question across all graph types

    Args:
        question_id: StackOverflow Question ID

    Returns:
        List of ComparisonMetricsSummary - metrics per graph type
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


@router.get("/questions", response_model=PaginatedEvaluatedQuestionsExtendedResponse)
async def get_all_evaluated_questions(
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=200, description="Items per page (max 200)"),
        sort_by: str = Query("creation_date", description="Sort by: creation_date, score, evaluation_count, question_id, adaptive_rag_f1, simple_rag_f1, pure_llm_f1"),
        sort_order: str = Query("desc", description="Sort order: asc, desc"),
        tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
        title_search: Optional[str] = Query(None, description="Partial title search (case-insensitive)"),
        db: Session = Depends(get_db)
):
    """
    Liste aller SO-Fragen die evaluiert wurden (paginiert)

    Returns:
        Paginated list of evaluated questions with metadata and best metrics per architecture
    """
    try:
        valid_sort_fields = ["creation_date", "score", "evaluation_count", "question_id", "adaptive_rag_f1", "simple_rag_f1", "pure_llm_f1"]
        if sort_by not in valid_sort_fields:
            sort_by = "creation_date"

        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"

        comparison_service = get_comparison_service(db)
        result = comparison_service.get_all_evaluated_questions(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            tags=tags,
            title_search=title_search
        )

        items = []
        for q in result["items"]:
            metrics_by_arch = None
            if q.get("metrics_by_architecture"):
                metrics_by_arch = MetricsByArchitecture(
                    adaptive_rag=ArchitectureMetrics(**q["metrics_by_architecture"]["adaptive_rag"]) if q["metrics_by_architecture"].get("adaptive_rag") else None,
                    simple_rag=ArchitectureMetrics(**q["metrics_by_architecture"]["simple_rag"]) if q["metrics_by_architecture"].get("simple_rag") else None,
                    pure_llm=ArchitectureMetrics(**q["metrics_by_architecture"]["pure_llm"]) if q["metrics_by_architecture"].get("pure_llm") else None
                )

            items.append(EvaluatedQuestionListItemExtended(
                question_id=q["question_id"],
                question_title=q["question_title"],
                available_graph_types=q["available_graph_types"],
                total_evaluations=q["total_evaluations"],
                has_multiple_graph_types=q["has_multiple_graph_types"],
                tags=q["tags"],
                score=q["score"],
                metrics_by_architecture=metrics_by_arch
            ))

        return PaginatedEvaluatedQuestionsExtendedResponse(
            items=items,
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
