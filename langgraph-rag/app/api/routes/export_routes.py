"""
API routes for scientific data export of RAG experiment results.

Provides endpoints for exporting evaluation data in CSV, JSON, and LaTeX formats.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.schemas.export_schemas import (
    ExportFormat,
    ExportType,
    FullExportRequest,
    StatisticsExportRequest,
    ComparisonExportRequest,
    ExportJobStartResponse,
    ExportJobStatus,
    ExportProgress,
)
from app.config import settings
from app.database import get_db
from app.services.export_service import get_export_service
from app.services.job_manager import get_export_manager, JobStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["Export"])


def _get_export_dir() -> Path:
    """Get or create export directory."""
    export_dir = Path(settings.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def _get_content_type(format: ExportFormat) -> str:
    """Get content type for export format."""
    if format == ExportFormat.CSV:
        return "text/csv"
    elif format == ExportFormat.JSON:
        return "application/json"
    elif format == ExportFormat.LATEX:
        return "text/x-tex"
    return "text/plain"


def _get_file_extension(format: ExportFormat) -> str:
    """Get file extension for export format."""
    if format == ExportFormat.CSV:
        return ".csv"
    elif format == ExportFormat.JSON:
        return ".json"
    elif format == ExportFormat.LATEX:
        return ".tex"
    return ".txt"


@router.post("/full", response_model=ExportJobStartResponse)
async def export_full(
    request: FullExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start a full export of all evaluation data (like comparison view).

    This includes:
    - Question metadata (ID, title, body, tags, score)
    - All evaluations per graph type
    - BERT scores (F1, precision, recall)
    - Processing time, manual ratings
    - Graph execution trace and node timings
    - Retrieved documents

    Returns a job_id for status polling.
    """
    manager = get_export_manager()

    job_id = manager.create_job(
        parameters={
            "export_type": ExportType.FULL.value,
            "format": request.format.value,
            "filters": request.filters.model_dump() if request.filters else None,
            "include_retrieved_documents": request.include_retrieved_documents,
            "include_full_answers": request.include_full_answers,
            "include_node_timings": request.include_node_timings
        },
        progress_fields={
            "phase": "pending",
            "processed": 0,
            "total": 0,
            "percent": 0.0
        }
    )

    def update_progress(progress_update: dict):
        total = progress_update.get("total", 0)
        processed = progress_update.get("processed", 0)
        percent = (processed / total * 100) if total > 0 else 0
        progress_update["percent"] = percent
        manager.update_progress(job_id, progress_update)

    async def export_task():
        try:
            logger.info(f"Starting full export job {job_id}")

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                def run_export():
                    from app.database import SessionLocal
                    with SessionLocal() as task_db:
                        service = get_export_service(task_db)

                        data = service.fetch_full_export_data(
                            filters=request.filters,
                            include_retrieved_documents=request.include_retrieved_documents,
                            include_full_answers=request.include_full_answers,
                            include_node_timings=request.include_node_timings,
                            progress_callback=update_progress
                        )

                        update_progress({"phase": "formatting", "processed": 0, "total": 100})

                        if request.format == ExportFormat.CSV:
                            content = service.to_csv(data)
                        elif request.format == ExportFormat.JSON:
                            content = service.to_json(data)
                        elif request.format == ExportFormat.LATEX:
                            stats_data = service.fetch_statistics(
                                filters=request.filters,
                                group_by=["graph_type"],
                                include_ci=True,
                                include_std=True
                            )
                            content = service.to_latex_statistics(stats_data)
                        else:
                            content = service.to_json(data)

                        return content, data.export_metadata.total_evaluations

                content, total_evals = await loop.run_in_executor(executor, run_export)

            export_dir = _get_export_dir()
            ext = _get_file_extension(request.format)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"export_full_{timestamp}{ext}"
            file_path = export_dir / filename

            file_path.write_text(content, encoding="utf-8")

            manager.update_progress(job_id, {
                "phase": "completed",
                "file_path": str(file_path),
                "file_size_bytes": file_path.stat().st_size,
                "filename": filename
            })
            manager.complete_job(job_id)

            logger.info(f"Full export job {job_id} completed: {filename}")

        except Exception as e:
            logger.error(f"Full export job {job_id} failed: {e}")
            manager.fail_job(job_id, str(e))

    background_tasks.add_task(export_task)

    return ExportJobStartResponse(
        job_id=job_id,
        message="Full export started",
        export_type=ExportType.FULL,
        format=request.format
    )


@router.post("/statistics", response_model=ExportJobStartResponse)
async def export_statistics(
    request: StatisticsExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Export aggregated statistics for paper tables.

    Includes:
    - Per graph type: n, mean, std, 95% CI
    - BERT-F1, precision, recall
    - Processing time statistics

    Ideal for LaTeX tables in scientific papers.
    """
    manager = get_export_manager()

    job_id = manager.create_job(
        parameters={
            "export_type": ExportType.STATISTICS.value,
            "format": request.format.value,
            "filters": request.filters.model_dump() if request.filters else None,
            "group_by": request.group_by,
            "include_confidence_intervals": request.include_confidence_intervals,
            "include_std": request.include_std
        },
        progress_fields={
            "phase": "pending",
            "processed": 0,
            "total": 100,
            "percent": 0.0
        }
    )

    def update_progress(progress_update: dict):
        total = progress_update.get("total", 100)
        processed = progress_update.get("processed", 0)
        percent = (processed / total * 100) if total > 0 else 0
        progress_update["percent"] = percent
        manager.update_progress(job_id, progress_update)

    async def export_task():
        try:
            logger.info(f"Starting statistics export job {job_id}")

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                def run_export():
                    from app.database import SessionLocal
                    with SessionLocal() as task_db:
                        service = get_export_service(task_db)

                        data = service.fetch_statistics(
                            filters=request.filters,
                            group_by=request.group_by,
                            include_ci=request.include_confidence_intervals,
                            include_std=request.include_std,
                            progress_callback=update_progress
                        )

                        update_progress({"phase": "formatting", "processed": 80, "total": 100})

                        if request.format == ExportFormat.CSV:
                            content = service.statistics_to_csv(data)
                        elif request.format == ExportFormat.JSON:
                            content = service.statistics_to_json(data)
                        elif request.format == ExportFormat.LATEX:
                            content = service.to_latex_statistics(data)
                        else:
                            content = service.statistics_to_json(data)

                        return content

                content = await loop.run_in_executor(executor, run_export)

            export_dir = _get_export_dir()
            ext = _get_file_extension(request.format)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"export_statistics_{timestamp}{ext}"
            file_path = export_dir / filename

            file_path.write_text(content, encoding="utf-8")

            manager.update_progress(job_id, {
                "phase": "completed",
                "file_path": str(file_path),
                "file_size_bytes": file_path.stat().st_size,
                "filename": filename
            })
            manager.complete_job(job_id)

            logger.info(f"Statistics export job {job_id} completed: {filename}")

        except Exception as e:
            logger.error(f"Statistics export job {job_id} failed: {e}")
            manager.fail_job(job_id, str(e))

    background_tasks.add_task(export_task)

    return ExportJobStartResponse(
        job_id=job_id,
        message="Statistics export started",
        export_type=ExportType.STATISTICS,
        format=request.format
    )


@router.post("/comparison", response_model=ExportJobStartResponse)
async def export_comparison(
    request: ComparisonExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Export side-by-side comparison table.

    Shows per-question performance across graph types with:
    - Metric values per graph type
    - Best performing graph type
    - Improvement percentage vs baseline
    """
    manager = get_export_manager()

    job_id = manager.create_job(
        parameters={
            "export_type": ExportType.COMPARISON.value,
            "format": request.format.value,
            "filters": request.filters.model_dump() if request.filters else None,
            "baseline_graph_type": request.baseline_graph_type,
            "metric": request.metric
        },
        progress_fields={
            "phase": "pending",
            "processed": 0,
            "total": 100,
            "percent": 0.0
        }
    )

    def update_progress(progress_update: dict):
        total = progress_update.get("total", 100)
        processed = progress_update.get("processed", 0)
        percent = (processed / total * 100) if total > 0 else 0
        progress_update["percent"] = percent
        manager.update_progress(job_id, progress_update)

    async def export_task():
        try:
            logger.info(f"Starting comparison export job {job_id}")

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                def run_export():
                    from app.database import SessionLocal
                    with SessionLocal() as task_db:
                        service = get_export_service(task_db)

                        data = service.fetch_comparison_table(
                            filters=request.filters,
                            baseline_graph_type=request.baseline_graph_type,
                            metric=request.metric,
                            progress_callback=update_progress
                        )

                        update_progress({"phase": "formatting", "processed": 80, "total": 100})

                        if request.format == ExportFormat.CSV:
                            content = service.comparison_to_csv(data)
                        elif request.format == ExportFormat.JSON:
                            content = service.comparison_to_json(data)
                        elif request.format == ExportFormat.LATEX:
                            content = service.to_latex_comparison(data)
                        else:
                            content = service.comparison_to_json(data)

                        return content

                content = await loop.run_in_executor(executor, run_export)

            export_dir = _get_export_dir()
            ext = _get_file_extension(request.format)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"export_comparison_{timestamp}{ext}"
            file_path = export_dir / filename

            file_path.write_text(content, encoding="utf-8")

            manager.update_progress(job_id, {
                "phase": "completed",
                "file_path": str(file_path),
                "file_size_bytes": file_path.stat().st_size,
                "filename": filename
            })
            manager.complete_job(job_id)

            logger.info(f"Comparison export job {job_id} completed: {filename}")

        except Exception as e:
            logger.error(f"Comparison export job {job_id} failed: {e}")
            manager.fail_job(job_id, str(e))

    background_tasks.add_task(export_task)

    return ExportJobStartResponse(
        job_id=job_id,
        message="Comparison export started",
        export_type=ExportType.COMPARISON,
        format=request.format
    )


@router.get("/jobs", response_model=List[ExportJobStatus])
async def list_export_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List all export jobs, optionally filtered by status.
    """
    manager = get_export_manager()

    job_status = None
    if status:
        try:
            job_status = JobStatus(status)
        except ValueError:
            pass

    jobs = manager.list_jobs(status=job_status, limit=limit)

    return [
        ExportJobStatus(
            job_id=j["job_id"],
            status=j["status"].value if isinstance(j["status"], JobStatus) else j["status"],
            export_type=ExportType(j["parameters"].get("export_type", "full")),
            format=ExportFormat(j["parameters"].get("format", "json")),
            progress=ExportProgress(
                phase=j["progress"].get("phase", "unknown"),
                processed=j["progress"].get("processed", 0),
                total=j["progress"].get("total", 0),
                percent=j["progress"].get("percent", 0.0)
            ),
            started_at=j["started_at"],
            completed_at=j.get("completed_at"),
            file_size_bytes=j["progress"].get("file_size_bytes"),
            download_url=f"/api/v1/export/jobs/{j['job_id']}/download" if j["progress"].get("file_path") else None,
            error=j.get("error"),
            parameters=j["parameters"]
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=ExportJobStatus)
async def get_export_job_status(job_id: str):
    """
    Get status of an export job.

    Poll this endpoint to track progress.
    """
    manager = get_export_manager()
    job_data = manager.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail="Export job not found")

    return ExportJobStatus(
        job_id=job_data["job_id"],
        status=job_data["status"].value if isinstance(job_data["status"], JobStatus) else job_data["status"],
        export_type=ExportType(job_data["parameters"].get("export_type", "full")),
        format=ExportFormat(job_data["parameters"].get("format", "json")),
        progress=ExportProgress(
            phase=job_data["progress"].get("phase", "unknown"),
            processed=job_data["progress"].get("processed", 0),
            total=job_data["progress"].get("total", 0),
            percent=job_data["progress"].get("percent", 0.0)
        ),
        started_at=job_data["started_at"],
        completed_at=job_data.get("completed_at"),
        file_size_bytes=job_data["progress"].get("file_size_bytes"),
        download_url=f"/api/v1/export/jobs/{job_id}/download" if job_data["progress"].get("file_path") else None,
        error=job_data.get("error"),
        parameters=job_data["parameters"]
    )


@router.get("/jobs/{job_id}/download")
async def download_export(job_id: str):
    """
    Download the exported file.

    Only available for completed jobs.
    """
    manager = get_export_manager()
    job_data = manager.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail="Export job not found")

    status = job_data["status"]
    if isinstance(status, JobStatus):
        status = status.value

    if status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Export not ready. Current status: {status}"
        )

    file_path = job_data["progress"].get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Export file not found")

    file_path = Path(file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file has been deleted")

    filename = job_data["progress"].get("filename", file_path.name)
    format_str = job_data["parameters"].get("format", "json")

    try:
        format_enum = ExportFormat(format_str)
    except ValueError:
        format_enum = ExportFormat.JSON

    content_type = _get_content_type(format_enum)

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=content_type
    )


@router.delete("/jobs/{job_id}")
async def delete_export_job(job_id: str):
    """
    Delete an export job and its file.

    Only allows deletion of completed or failed jobs.
    """
    manager = get_export_manager()
    job_data = manager.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail="Export job not found")

    file_path = job_data["progress"].get("file_path")
    if file_path:
        file_path = Path(file_path)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Deleted export file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete export file: {e}")

    if not manager.delete_job(job_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete running job. Wait for completion or cancel first."
        )

    return {"message": f"Export job {job_id} deleted successfully"}


@router.post("/jobs/{job_id}/cancel")
async def cancel_export_job(job_id: str):
    """
    Cancel a running export job.
    """
    manager = get_export_manager()
    job_data = manager.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail="Export job not found")

    if not manager.cancel_job(job_id):
        current_status = job_data["status"]
        status_str = current_status.value if isinstance(current_status, JobStatus) else current_status
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{status_str}'"
        )

    return {"message": f"Export job {job_id} cancellation requested"}
