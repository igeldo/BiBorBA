"""Generic background job management for batch operations."""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobManager:
    """Generic manager for background jobs with progress tracking."""

    def __init__(self, job_type: str):
        self.job_type = job_type
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(
        self,
        parameters: Dict[str, Any],
        progress_fields: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid.uuid4())

        self._jobs[job_id] = {
            "job_id": job_id,
            "job_type": self.job_type,
            "status": JobStatus.RUNNING,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "progress": progress_fields or {},
            "parameters": parameters,
            "results": [],
            "error": None
        }

        logger.info(f"Created {self.job_type} job: {job_id}")
        return job_id

    def update_progress(self, job_id: str, progress: Dict[str, Any]) -> None:
        """Update job progress."""
        if job_id in self._jobs:
            self._jobs[job_id]["progress"].update(progress)

            # If result is provided, append it
            if "result" in progress:
                self._jobs[job_id]["results"].append(progress["result"])

    def complete_job(self, job_id: str, results: Optional[List] = None) -> None:
        """Mark job as completed."""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = JobStatus.COMPLETED
            self._jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            if results:
                self._jobs[job_id]["results"] = results

    def fail_job(self, job_id: str, error: str) -> None:
        """Mark job as failed."""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = JobStatus.FAILED
            self._jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            self._jobs[job_id]["error"] = error

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job. Returns True if successful."""
        if job_id not in self._jobs:
            return False

        job = self._jobs[job_id]
        if job["status"] != JobStatus.RUNNING:
            return False

        job["status"] = JobStatus.CANCELLED
        job["completed_at"] = datetime.utcnow().isoformat()
        return True

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List jobs, optionally filtered by status."""
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j["status"] == status]

        # Sort by started_at descending
        jobs.sort(key=lambda x: x["started_at"], reverse=True)

        return jobs[:limit]

    def delete_job(self, job_id: str) -> bool:
        """Delete a completed/failed job. Returns True if successful."""
        if job_id not in self._jobs:
            return False

        job = self._jobs[job_id]
        if job["status"] == JobStatus.RUNNING:
            return False

        del self._jobs[job_id]
        return True


# Singleton instances for each job type
_batch_query_manager: Optional[JobManager] = None
_scraper_manager: Optional[JobManager] = None
_rebuild_manager: Optional[JobManager] = None


def get_batch_query_manager() -> JobManager:
    """Get global batch query job manager instance."""
    global _batch_query_manager
    if _batch_query_manager is None:
        _batch_query_manager = JobManager("batch_query")
    return _batch_query_manager


def get_scraper_manager() -> JobManager:
    """Get global scraper job manager instance."""
    global _scraper_manager
    if _scraper_manager is None:
        _scraper_manager = JobManager("scraper")
    return _scraper_manager


def get_rebuild_manager() -> JobManager:
    """Get global rebuild job manager instance."""
    global _rebuild_manager
    if _rebuild_manager is None:
        _rebuild_manager = JobManager("rebuild")
    return _rebuild_manager
