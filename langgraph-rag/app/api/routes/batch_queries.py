import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from sqlalchemy.orm import Session

from app.api.schemas.schemas import (
    BatchQueryRequest,
    BatchQueryJobStatus,
    BatchQueryStartResponse,
    BatchQueryResult,
    BatchQueryProgress,
    GraphType,
    PaginatedMissingQuestionsResponse
)
from app.database import get_db
from app.dependencies import get_batch_query_service
from app.services.batch_query_service import BatchQueryService
from app.services.coverage_service import get_coverage_service
from app.services.job_manager import get_batch_query_manager, JobStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/batch-queries", tags=["Batch Queries"])


@router.post("", response_model=BatchQueryStartResponse)
async def start_batch_query(
    request: BatchQueryRequest,
    background_tasks: BackgroundTasks,
    service: BatchQueryService = Depends(get_batch_query_service)
):
    """
    Start batch processing of StackOverflow questions.

    - Processes up to 50 questions sequentially
    - Generates answers using graph execution
    - Calculates BERT-Score against SO answers
    - Returns job_id for status polling
    """

    if len(request.question_ids) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 questions per batch allowed"
        )

    manager = get_batch_query_manager()

    job_id = manager.create_job(
        parameters=request.model_dump(),
        progress_fields={
            "total_questions": len(request.question_ids) * len(request.graph_types or [GraphType.ADAPTIVE_RAG]),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "current_question_id": None,
            "current_question_title": None
        }
    )

    def update_progress(progress_update: Dict):
        """Update progress and optionally add completed result"""
        manager.update_progress(job_id, progress_update)

    async def batch_task():
        try:
            logger.info(f"Starting batch query {job_id} with {len(request.question_ids)} questions")

            from concurrent.futures import ThreadPoolExecutor
            import asyncio

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                def run_batch():
                    return service.process_batch_sync(
                        job_id=job_id,
                        question_ids=request.question_ids,
                        session_id=request.session_id,
                        collection_ids=request.collection_ids,
                        graph_types=request.graph_types,
                        llm_config=request.llm_config,
                        progress_callback=update_progress
                    )

                result = await loop.run_in_executor(executor, run_batch)

            manager.complete_job(job_id)
            logger.info(f"Batch query {job_id} completed: {result['summary']}")

        except Exception as e:
            logger.error(f"Batch query {job_id} failed: {e}")
            manager.fail_job(job_id, str(e))

    background_tasks.add_task(batch_task)

    return BatchQueryStartResponse(
        job_id=job_id,
        message=f"Batch query started with {len(request.question_ids)} questions",
        total_questions=len(request.question_ids),
    )


@router.get("/missing-questions", response_model=PaginatedMissingQuestionsResponse)
async def get_missing_questions(
    graph_types: Optional[str] = Query(
        default="adaptive_rag,simple_rag,pure_llm",
        description="Comma-separated list of graph types to check (adaptive_rag, simple_rag, pure_llm)"
    ),
    exclude_collection_ids: Optional[str] = Query(
        default=None,
        description="Comma-separated list of collection IDs - questions in these collections will be excluded"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    sort_by: str = Query("score", description="Sort by: score, title, stack_overflow_id"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Find questions that are missing evaluations for the current model configuration.

    Returns missing question IDs per graph type based on:
    - For adaptive_rag, simple_rag: llm_model + llm_correctness_model + embedding_model
    - For pure_llm: llm_model + llm_correctness_model (no embedding)

    Response includes:
    - current_config: Current model configuration from settings
    - total_questions: Total number of questions in the database
    - missing_by_graph_type: Missing question counts and IDs per graph type
    - questions: Details of missing questions (paginated), each with collections info
    - Pagination metadata: page, page_size, total_missing, total_pages, has_next, has_prev
    """
    graph_type_list = [gt.strip() for gt in graph_types.split(",") if gt.strip()]

    valid_types = {"adaptive_rag", "simple_rag", "pure_llm"}
    invalid_types = set(graph_type_list) - valid_types
    if invalid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid graph types: {invalid_types}. Valid types are: {valid_types}"
        )

    valid_sort_fields = {"score", "title", "stack_overflow_id"}
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by: {sort_by}. Valid fields are: {valid_sort_fields}"
        )

    if sort_order.lower() not in {"asc", "desc"}:
        raise HTTPException(
            status_code=400,
            detail="sort_order must be 'asc' or 'desc'"
        )

    exclude_ids: List[int] = []
    if exclude_collection_ids:
        try:
            exclude_ids = [int(x.strip()) for x in exclude_collection_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="exclude_collection_ids must be comma-separated integers"
            )

    coverage_service = get_coverage_service(db)
    return coverage_service.get_missing_questions_summary(
        graph_types=graph_type_list,
        exclude_collection_ids=exclude_ids if exclude_ids else None,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("", response_model=List[BatchQueryJobStatus])
async def list_batch_query_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List all batch query jobs, optionally filtered by status.
    """
    manager = get_batch_query_manager()

    job_status = None
    if status:
        try:
            job_status = JobStatus(status)
        except ValueError:
            pass  # Invalid status, will return all jobs

    jobs = manager.list_jobs(status=job_status, limit=limit)

    return [
        BatchQueryJobStatus(
            job_id=j["job_id"],
            status=j["status"].value if isinstance(j["status"], JobStatus) else j["status"],
            started_at=j["started_at"],
            completed_at=j.get("completed_at"),
            progress=BatchQueryProgress(**j["progress"]),
            parameters=j["parameters"],
            results=[BatchQueryResult(**r) for r in j.get("results", [])],
            error=j.get("error")
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=BatchQueryJobStatus)
async def get_batch_query_status(job_id: str):
    """
    Get status and results of a batch query job.

    Poll this endpoint to track progress.
    """
    manager = get_batch_query_manager()
    job_data = manager.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return BatchQueryJobStatus(
        job_id=job_data["job_id"],
        status=job_data["status"].value if isinstance(job_data["status"], JobStatus) else job_data["status"],
        started_at=job_data["started_at"],
        completed_at=job_data.get("completed_at"),
        progress=BatchQueryProgress(**job_data["progress"]),
        parameters=job_data["parameters"],
        results=[BatchQueryResult(**r) for r in job_data.get("results", [])],
        error=job_data.get("error")
    )


@router.delete("/{job_id}")
async def delete_batch_query_job(job_id: str):
    """
    Delete a batch query job from memory.
    Only allows deletion of completed or failed jobs.
    """
    manager = get_batch_query_manager()
    job_data = manager.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not manager.delete_job(job_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete running job. Wait for completion or cancel first."
        )

    return {"message": f"Job {job_id} deleted successfully"}


@router.post("/{job_id}/cancel")
async def cancel_batch_query_job(job_id: str):
    """
    Cancel a running batch query job.
    Note: Cancellation may not be immediate for currently processing question.
    """
    manager = get_batch_query_manager()
    job_data = manager.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not manager.cancel_job(job_id):
        current_status = job_data["status"]
        status_str = current_status.value if isinstance(current_status, JobStatus) else current_status
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{status_str}'"
        )

    return {"message": f"Job {job_id} cancellation requested"}
