# app/api/routes/scraper.py
"""
StackOverflow Scraper Endpoints
- Scrape new questions and answers from Stack Overflow API
- Store data in database
- Manage scraping jobs
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.api.schemas.schemas import (
    ScrapeRequest,
    ScrapeJobStatus,
    ScrapeJobResult,
    ScrapeStats
)
from app.api.middleware import safe_error_handler
from app.database import get_db
from app.services.stackoverflow_scrapper import get_stackoverflow_scraper
from app.services.job_manager import get_scraper_manager, JobStatus

router = APIRouter(prefix="/scraper", tags=["StackOverflow Scraper"])
logger = logging.getLogger(__name__)


@router.post("/scrape", response_model=ScrapeJobStatus)
async def start_scraping_job(
        request: ScrapeRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """
    Start a new Stack Overflow scraping job

    Scrapes SQL-related questions and answers from Stack Overflow API
    and stores them in the database.

    Parameters:
    - count: Number of questions to fetch (max 1000)
    - days_back: Look back this many days (max 10 years / 3650 days)
    - tags: List of tags to filter by (e.g., ["sql", "mysql"])
    - min_score: Minimum score for questions (default 1)
    - only_accepted_answers: Only fetch questions with accepted answers
    """

    if request.count > 1000:
        raise HTTPException(
            status_code=400,
            detail="Maximum count is 1000 per job"
        )

    if request.days_back > 3650:
        raise HTTPException(
            status_code=400,
            detail="Maximum days_back is 3650 days (10 years)"
        )

    manager = get_scraper_manager()

    job_id = manager.create_job(
        parameters=request.dict(),
        progress_fields={
            "questions_fetched": 0,
            "questions_stored": 0,
            "answers_fetched": 0,
            "answers_stored": 0,
            "errors": 0
        }
    )

    def scrape_task():
        try:
            scraper = get_stackoverflow_scraper()

            result = scraper.scrape_and_store(
                count=request.count,
                days_back=request.days_back,
                tags=request.tags,
                min_score=request.min_score,
                only_accepted_answers=request.only_accepted_answers,
                start_page=request.start_page,
                job_id=job_id,
                progress_callback=lambda progress: manager.update_progress(job_id, progress)
            )

            manager.update_progress(job_id, {"result": result})
            manager.complete_job(job_id)

            logger.info(f"Scraping job {job_id} completed: {result}")

        except Exception as e:
            logger.error(f"Scraping job {job_id} failed: {e}")
            manager.fail_job(job_id, str(e))

    background_tasks.add_task(scrape_task)

    job_data = manager.get_job(job_id)
    return _build_job_status(job_data)


def _build_job_status(job_data: dict) -> ScrapeJobStatus:
    """Convert JobManager job data to ScrapeJobStatus response"""
    status = job_data["status"]
    status_str = status.value if isinstance(status, JobStatus) else status

    return ScrapeJobStatus(
        job_id=job_data["job_id"],
        status=status_str,
        started_at=job_data["started_at"],
        completed_at=job_data.get("completed_at"),
        progress=job_data["progress"],
        parameters=job_data["parameters"],
        result=job_data["progress"].get("result"),
        error=job_data.get("error")
    )


@router.get("/jobs/{job_id}", response_model=ScrapeJobStatus)
async def get_scrape_job_status(job_id: str):
    """
    Get status of a scraping job

    Returns current status and progress of the scraping job.
    """
    manager = get_scraper_manager()
    job_data = manager.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return _build_job_status(job_data)


@router.get("/jobs", response_model=List[ScrapeJobStatus])
async def list_scrape_jobs(
        status: Optional[str] = Query(None, description="Filter by status: running, completed, failed"),
        limit: int = Query(50, le=100)
):
    """
    List all scraping jobs

    Returns a list of all scraping jobs, optionally filtered by status.
    """
    manager = get_scraper_manager()

    job_status = None
    if status:
        try:
            job_status = JobStatus(status)
        except ValueError:
            pass
    jobs = manager.list_jobs(status=job_status, limit=limit)

    return [_build_job_status(job) for job in jobs]


@router.delete("/jobs/{job_id}")
async def delete_scrape_job(job_id: str):
    """
    Delete a scraping job record

    Only completed or failed jobs can be deleted.
    """
    manager = get_scraper_manager()
    job_data = manager.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if not manager.delete_job(job_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete running job"
        )

    return {"message": f"Job {job_id} deleted", "job_id": job_id}


@router.get("/stats", response_model=ScrapeStats)
async def get_scraper_stats():
    """
    Get scraper statistics

    Shows statistics about all completed scraping jobs.
    """
    try:
        scraper = get_stackoverflow_scraper()
        stats = scraper.get_scraping_stats()

        return ScrapeStats(**stats)

    except Exception as e:
        logger.error(f"Error getting scraper stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-api")
async def test_stackoverflow_api():
    """
    Test Stack Overflow API connection

    Performs a simple test query to verify API connectivity and quota.
    """
    try:
        scraper = get_stackoverflow_scraper()
        test_result = scraper.test_api_connection()

        return {
            "status": "success" if test_result["success"] else "error",
            "api_available": test_result["success"],
            "quota_remaining": test_result.get("quota_remaining"),
            "test_query_result": test_result.get("result"),
            "error": test_result.get("error")
        }

    except Exception as e:
        logger.error(f"API test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backfill-accepted-answers")
async def backfill_missing_accepted_answers(
    limit: Optional[int] = Query(None, description="Limit number of answers to fetch"),
    db: Session = Depends(get_db)
):
    """
    Debug/Maintenance endpoint: Fetch missing accepted answers

    Finds questions with accepted_answer_id that don't have the answer stored,
    then fetches those answers from StackOverflow API.

    Parameters:
    - limit: Optional limit on number of missing answers to fetch
    """
    from app.database import SOQuestion, SOAnswer

    logger.info("Starting backfill of missing accepted answers")

    scraper = get_stackoverflow_scraper()

    questions_with_accepted = db.query(SOQuestion).filter(
        SOQuestion.accepted_answer_id.isnot(None)
    ).all()

    logger.info(f"Found {len(questions_with_accepted)} questions with accepted_answer_id")

    missing_answer_ids = []
    for question in questions_with_accepted:
        answer_exists = db.query(SOAnswer).filter(
            SOAnswer.stack_overflow_id == question.accepted_answer_id
        ).first()

        if not answer_exists:
            missing_answer_ids.append(question.accepted_answer_id)

    logger.info(f"Found {len(missing_answer_ids)} missing accepted answers")

    if not missing_answer_ids:
        return {
            "status": "completed",
            "questions_checked": len(questions_with_accepted),
            "missing_answers_found": 0,
            "answers_stored": 0
        }

    if limit:
        missing_answer_ids = missing_answer_ids[:limit]

    try:
        answers_data = scraper._fetch_accepted_answers(missing_answer_ids)
        logger.info(f"Fetched {len(answers_data)} answers from API")
    except Exception as e:
        logger.error(f"Failed to fetch from API: {e}")
        raise HTTPException(status_code=500, detail=f"API fetch failed: {str(e)}")

    stats = {"answers_stored": 0, "answers_skipped": 0, "errors": 0}

    for answer_raw in answers_data:
        try:
            answer_data = scraper._parse_answer_data(answer_raw)
            scraper._store_answer_orm(db, answer_raw, answer_data, stats)
        except Exception as e:
            logger.error(f"Error processing answer: {e}")
            stats["errors"] += 1

    return {
        "status": "completed",
        "questions_checked": len(questions_with_accepted),
        "missing_answers_found": len(missing_answer_ids),
        "answers_fetched": len(answers_data),
        "answers_stored": stats["answers_stored"],
        "errors": stats["errors"]
    }
