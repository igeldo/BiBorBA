# api/routes/batch_queries.py
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends

from app.api.schemas.schemas import (
    BatchQueryRequest,
    BatchQueryJobStatus,
    BatchQueryStartResponse,
    BatchQueryResult,
    BatchQueryProgress,
    GraphType
)
from app.api.middleware import safe_error_handler
from app.dependencies import get_batch_query_service
from app.services.batch_query_service import BatchQueryService
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

    # Validate batch size
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
