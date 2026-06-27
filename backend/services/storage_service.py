"""
BlockForge AI – Storage Service
File and directory management helpers.
"""

import shutil
import logging
from pathlib import Path
from typing import Optional

from config import settings

logger = logging.getLogger("blockforge.storage")


class StorageService:
    """Manage file storage for jobs."""

    @staticmethod
    def get_job_dirs(job_id: str) -> dict[str, Path]:
        """Return all directories for a given job."""
        return {
            "upload": settings.UPLOAD_DIR / job_id,
            "frames": settings.FRAMES_DIR / job_id,
            "masks": settings.MASKS_DIR / job_id,
            "output": settings.OUTPUT_DIR / job_id,
            "inpainted": settings.FRAMES_DIR / job_id / "inpainted",
            "smoothed": settings.FRAMES_DIR / job_id / "smoothed",
            "enhanced": settings.FRAMES_DIR / job_id / "enhanced",
        }

    @staticmethod
    def ensure_job_dirs(job_id: str) -> dict[str, Path]:
        """Create all directories for a job."""
        dirs = StorageService.get_job_dirs(job_id)
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)
        return dirs

    @staticmethod
    def cleanup_job(job_id: str, keep_output: bool = True):
        """
        Clean up temporary files for a job.
        Optionally keep the final output.
        """
        dirs = StorageService.get_job_dirs(job_id)

        for name, path in dirs.items():
            if name == "output" and keep_output:
                continue
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                logger.info(f"⛏  Cleaned up {name} for job {job_id}")

    @staticmethod
    def delete_job(job_id: str):
        """Completely remove all directories and files for a job."""
        dirs = StorageService.get_job_dirs(job_id)
        for name, path in dirs.items():
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                logger.info(f"⛏  Deleted {name} for job {job_id}")

    @staticmethod
    def cleanup_old_jobs(max_age_hours: int = 24):
        """Remove jobs older than max_age_hours."""
        import time

        now = time.time()
        cutoff = now - (max_age_hours * 3600)

        for base_dir in [settings.UPLOAD_DIR, settings.FRAMES_DIR, settings.MASKS_DIR, settings.OUTPUT_DIR]:
            if not base_dir.exists():
                continue
            for job_dir in base_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                if job_dir.stat().st_mtime < cutoff:
                    shutil.rmtree(job_dir, ignore_errors=True)
                    logger.info(f"⛏  Removed old job dir: {job_dir}")

    @staticmethod
    def get_disk_usage() -> dict:
        """Return disk usage for all storage directories."""
        usage = {}
        for name, base_dir in {
            "uploads": settings.UPLOAD_DIR,
            "frames": settings.FRAMES_DIR,
            "masks": settings.MASKS_DIR,
            "output": settings.OUTPUT_DIR,
        }.items():
            if base_dir.exists():
                total = sum(f.stat().st_size for f in base_dir.rglob("*") if f.is_file())
                usage[name] = {
                    "path": str(base_dir),
                    "size_mb": round(total / (1024 * 1024), 2),
                    "jobs": len([d for d in base_dir.iterdir() if d.is_dir()]) if base_dir.exists() else 0,
                }
            else:
                usage[name] = {"path": str(base_dir), "size_mb": 0, "jobs": 0}
        return usage


storage_service = StorageService()
