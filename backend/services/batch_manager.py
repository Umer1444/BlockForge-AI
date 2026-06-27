"""
BlockForge AI – Batch Job Manager
Manages multiple processing jobs with priority queue and GPU batching.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import redis

from config import settings

logger = logging.getLogger("blockforge.batch")


class JobPriority(Enum):
    """Job priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


class JobStatus(Enum):
    """Job status states."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Represents a single video processing job."""
    job_id: str
    status: str = JobStatus.QUEUED.value
    priority: int = JobPriority.NORMAL.value
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: int = 0
    current_step: str = ""
    error_message: Optional[str] = None
    result_path: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = asdict(self)
        d["elapsed_time"] = (self.completed_at or time.time()) - self.created_at
        if self.started_at:
            d["processing_time"] = (self.completed_at or time.time()) - self.started_at
        return d


class BatchJobManager:
    """
    Manages a queue of video processing jobs with:
    - Priority-based scheduling
    - GPU batch optimization
    - Retry logic
    - State persistence
    """

    def __init__(self, redis_url: str = settings.REDIS_URL, max_concurrent: int = 1):
        self.redis_url = redis_url
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.max_concurrent = max_concurrent
        self.queue_key = "blockforge:job_queue"
        self.job_prefix = "blockforge:job:"
        self.metrics_key = "blockforge:metrics"

    def submit_job(
        self,
        job_id: str,
        priority: JobPriority = JobPriority.NORMAL,
        metadata: dict = None,
    ) -> BatchJob:
        """
        Submit a new job to the queue.

        Args:
            job_id: Unique job identifier
            priority: Job priority level
            metadata: Additional job metadata

        Returns:
            BatchJob object
        """
        job = BatchJob(
            job_id=job_id,
            priority=priority.value,
            metadata=metadata or {},
        )

        # Store job state
        self.redis.hset(
            self.job_prefix + job_id,
            mapping=asdict(job),
        )

        # Add to priority queue (sorted by priority, then by creation time)
        score = priority.value * 1e10 + job.created_at
        self.redis.zadd(self.queue_key, {job_id: score})

        logger.info(f"⛏  Job {job_id} submitted with priority {priority.name}")
        return job

    def get_next_jobs(self, count: int = 1) -> List[BatchJob]:
        """
        Get the next N jobs from the queue.

        Returns:
            List of BatchJob objects ready for processing
        """
        job_ids = self.redis.zrange(self.queue_key, 0, count - 1)
        jobs = []

        for job_id in job_ids:
            job_data = self.redis.hgetall(self.job_prefix + job_id)
            if job_data:
                job_data["priority"] = int(job_data["priority"])
                job_data["progress"] = int(job_data["progress"])
                job_data["retries"] = int(job_data["retries"])
                job_data["created_at"] = float(job_data["created_at"])
                job_data["started_at"] = float(job_data["started_at"]) if job_data.get("started_at") else None
                job_data["completed_at"] = float(job_data["completed_at"]) if job_data.get("completed_at") else None
                jobs.append(BatchJob(**job_data))

        return jobs

    def update_job(self, job_id: str, **updates):
        """Update job state."""
        self.redis.hset(self.job_prefix + job_id, mapping=updates)

    def mark_processing(self, job_id: str):
        """Mark job as currently processing."""
        self.redis.hset(
            self.job_prefix + job_id,
            mapping={
                "status": JobStatus.PROCESSING.value,
                "started_at": time.time(),
            },
        )
        # Remove from queue
        self.redis.zrem(self.queue_key, job_id)

    def mark_completed(self, job_id: str, result_path: str):
        """Mark job as completed."""
        self.redis.hset(
            self.job_prefix + job_id,
            mapping={
                "status": JobStatus.COMPLETED.value,
                "completed_at": time.time(),
                "result_path": result_path,
                "progress": 100,
            },
        )

    def mark_failed(self, job_id: str, error_message: str) -> bool:
        """
        Mark job as failed. Returns True if should retry, False if max retries exceeded.
        """
        job_data = self.redis.hgetall(self.job_prefix + job_id)
        retries = int(job_data.get("retries", 0))
        max_retries = int(job_data.get("max_retries", 3))

        if retries < max_retries:
            # Retry: put back in queue with higher priority
            self.redis.hset(
                self.job_prefix + job_id,
                mapping={
                    "status": JobStatus.QUEUED.value,
                    "retries": retries + 1,
                    "error_message": error_message,
                },
            )
            # Re-add to queue with higher priority (pushed to front)
            score = (JobPriority.HIGH.value - retries * 0.1) * 1e10
            self.redis.zadd(self.queue_key, {job_id: score})
            logger.warning(f"⛏  Job {job_id} retrying ({retries + 1}/{max_retries}): {error_message}")
            return True
        else:
            # Permanent failure
            self.redis.hset(
                self.job_prefix + job_id,
                mapping={
                    "status": JobStatus.FAILED.value,
                    "completed_at": time.time(),
                    "error_message": error_message,
                },
            )
            logger.error(f"⛏  Job {job_id} failed permanently: {error_message}")
            return False

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job details."""
        job_data = self.redis.hgetall(self.job_prefix + job_id)
        if not job_data:
            return None

        job_data["priority"] = int(job_data["priority"])
        job_data["progress"] = int(job_data["progress"])
        job_data["retries"] = int(job_data["retries"])
        job_data["created_at"] = float(job_data["created_at"])
        job_data["started_at"] = float(job_data["started_at"]) if job_data.get("started_at") else None
        job_data["completed_at"] = float(job_data["completed_at"]) if job_data.get("completed_at") else None
        return BatchJob(**job_data)

    def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        queued_count = self.redis.zcard(self.queue_key)
        processing = self.redis.keys(self.job_prefix + "*")
        processing_count = len([p for p in processing if self.get_job(p.split(":")[-1]).status == JobStatus.PROCESSING.value])

        return {
            "queued_jobs": queued_count,
            "processing_jobs": processing_count,
            "queue_size": queued_count + processing_count,
            "max_concurrent": self.max_concurrent,
        }

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job."""
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status == JobStatus.QUEUED.value:
            self.redis.hset(
                self.job_prefix + job_id,
                mapping={"status": JobStatus.CANCELLED.value},
            )
            self.redis.zrem(self.queue_key, job_id)
            logger.info(f"⛏  Job {job_id} cancelled")
            return True

        return False

    def clear_old_jobs(self, days: int = 7):
        """Clean up completed/failed jobs older than N days."""
        cutoff_time = time.time() - (days * 86400)
        keys = self.redis.keys(self.job_prefix + "*")

        for key in keys:
            job_id = key.split(":")[-1]
            job = self.get_job(job_id)
            if job and job.completed_at and job.completed_at < cutoff_time:
                self.redis.delete(key)
                logger.debug(f"⛏  Cleaned up old job {job_id}")
