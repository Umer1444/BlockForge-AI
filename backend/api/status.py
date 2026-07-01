import shutil
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import settings
from services.storage_service import storage_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = logging.getLogger("blockforge.status")


@router.delete("/")
async def clear_all_history():
    """Clear all job history by deleting upload and output directories."""
    upload_dir, output_dir = settings.UPLOAD_DIR, settings.OUTPUT_DIR
    deleted_count = 0

    try:
        for d in upload_dir.glob("*"):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
                deleted_count += 1

        for d in output_dir.glob("*"):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)

        return {"status": "success", "message": f"Cleared {deleted_count} jobs from registry."}
    except Exception as e:
        logger.exception("Failed to clear job history")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Delete a specific job and all its files."""
    try:
        await cancel_job(job_id)  # attempt cancellation first
    except Exception:
        logger.debug(f"Job {job_id} not active or already cleaned up")

    storage_service.delete_job(job_id)
    return {"status": "success", "message": f"Job {job_id} deleted."}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job by revoking its Celery task."""
    from workers.tasks import celery_app

    status_path = settings.UPLOAD_DIR / job_id / "status.json"
    if not status_path.exists():
        return {"status": "ignored", "message": "Job status not found or already idle."}

    try:
        with open(status_path) as f:
            status = json.load(f)

        task_id = status.get("task_id")
        if not task_id:
            return {"status": "ignored", "message": "No active task ID found for this job."}

        logger.info(f"⛏ Revoking task {task_id} for job {job_id}")
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")

        # Update status to cancelled
        status.update({"state": "failed", "current_step": "Cancelled by user"})
        with open(status_path, "w") as f:
            json.dump(status, f)

        storage_service.cleanup_job(job_id, keep_output=True)
        return {"status": "success", "message": f"Processing for job {job_id} cancelled."}
    except Exception as e:
        logger.exception(f"Failed to cancel job {job_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Return the current processing status for a job."""
    job_dir = settings.UPLOAD_DIR / job_id
    meta_path, status_path = job_dir / "metadata.json", job_dir / "status.json"

    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    status_data = {
        "state": "uploaded",
        "progress": 0,
        "current_step": "Waiting for processing",
        "details": {},
    }
    if status_path.exists():
        try:
            with open(status_path) as f:
                status_data = json.load(f)
        except Exception:
            logger.warning(f"Corrupt status.json for job {job_id}")

    output_dir = settings.OUTPUT_DIR / job_id
    output_files = list(output_dir.glob("output.*")) if output_dir.exists() else []

    return {
        "job_id": job_id,
        **status_data,
        "output_ready": bool(output_files),
        "output_url": f"/output/{job_id}/{output_files[0].name}" if output_files else None,
    }


@router.get("/status/{job_id}/download")
async def download_output(job_id: str):
    """Download the processed video."""
    output_dir = settings.OUTPUT_DIR / job_id
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Output not found")

    output_files = list(output_dir.glob("output.*"))
    if not output_files:
        raise HTTPException(status_code=404, detail="Processing not complete yet")

    filename = f"blockforge_{job_id}.mp4"
    meta_path = settings.UPLOAD_DIR / job_id / "metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            orig_filename = meta.get("original_filename", filename)
            if not orig_filename.lower().endswith(tuple(f".{ext}" for ext in settings.ALLOWED_EXTENSIONS)):
                filename = f"{orig_filename}.mp4"
            else:
                filename = orig_filename
        except Exception:
            logger.warning(f"Failed to read metadata for job {job_id}")

    return FileResponse(str(output_files[0]), media_type="video/mp4", filename=filename)


@router.get("/")
async def list_jobs():
    """List all jobs with their current status and previews."""
    jobs = []
    upload_dir = settings.UPLOAD_DIR
    if not upload_dir.exists():
        return {"jobs": []}

    try:
        dirs = sorted(
            [d for d in upload_dir.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        dirs = []

    for job_dir in dirs[:50]:  # limit to 50 most recent
        job_id = job_dir.name
        meta_path, status_path = job_dir / "metadata.json", job_dir / "status.json"

        job_info = {
            "job_id": job_id,
            "id": job_id,
            "created_at": job_dir.stat().st_mtime,
            "preview_url": f"/uploads/{job_id}/thumbnail.png",
        }

        if meta_path.exists():
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
                job_info.update({
                    "filename": meta.get("original_filename"),
                    "width": meta.get("width"),
                    "height": meta.get("height"),
                    "resolution": meta.get("resolution") or f"{meta.get('width')}x{meta.get('height')}",
                    "orientation": meta.get("orientation"),
                    "fps": meta.get("fps"),
                    "duration": meta.get("duration"),
                    "file_size": meta.get("file_size"),
                    "thumbnail_url": meta.get("thumbnail_url") or f"/uploads/{job_id}/thumbnail.png",
                })
            except Exception:
                logger.warning(f"Failed to read metadata for job {job_id}")

        output_dir = settings.OUTPUT_DIR / job_id
        if output_dir.exists():
            output_files = list(output_dir.glob("output.*"))
            if output_files:
                job_info.update({
                    "output_ready": True,
                    "output_url": f"/output/{job_id}/{output_files[0].name}",
                })
                after_preview = output_dir / "preview_after.png"
                if after_preview.exists():
                    job_info["preview_url"] = f"/output/{job_id}/preview_after.png"

        if status_path.exists():
            try:
                with open(status_path) as f:
                    status = json.load(f)
                job_info.update({
                    "state": status.get("state", "unknown"),
                    "progress": status.get("progress", 0),
                    "current_step": status.get("current_step", ""),
                })
            except Exception:
                job_info["state"] = "unknown"
        else:
            job_info["state"] = "completed" if job_info.get("output_ready") else "uploaded"

        jobs.append(job_info)

    return {"jobs": jobs}
