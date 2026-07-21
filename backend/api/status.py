import re
import shutil
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import settings
from services.storage_service import storage_service

router = APIRouter()
logger = logging.getLogger("blockforge.status")

# job_id is always a uuid4 generated server-side (see api/upload.py). Several
# routes below interpolate the caller-supplied job_id into filesystem paths and
# then delete/read files within those directories. Without validation, values
# like ".." (e.g., via percent-encoded dot segments) can escape the job
# directories and lead to arbitrary file reads/deletes.
_JOB_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _validate_job_id(job_id: str) -> None:
    if not _JOB_ID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id")


@router.delete("/jobs")
async def clear_all_history():
    """Clear all job history by deleting upload and output directories."""
    upload_dir = settings.UPLOAD_DIR
    output_dir = settings.OUTPUT_DIR
    
    deleted_count = 0
    
    try:
        # Delete upload subdirectories
        if upload_dir.exists():
            for d in upload_dir.iterdir():
                if d.is_dir():
                    shutil.rmtree(d)
                    deleted_count += 1
                    
        # Delete output subdirectories
        if output_dir.exists():
            for d in output_dir.iterdir():
                if d.is_dir():
                    shutil.rmtree(d)
                    
        return {"status": "success", "message": f"Cleared {deleted_count} jobs from registry."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a specific job and all its files."""
    _validate_job_id(job_id)
    try:
        # Also try to cancel if it was processing
        await cancel_job(job_id)
    except:
        pass

    storage_service.delete_job(job_id)
    return {"status": "success", "message": f"Job {job_id} deleted."}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job by revoking its Celery task."""
    _validate_job_id(job_id)
    from workers.tasks import celery_app

    status_path = settings.UPLOAD_DIR / job_id / "status.json"
    if not status_path.exists():
        # Maybe it's not processing or already cleaned up
        return {"status": "ignored", "message": "Job status not found or already idle."}

    try:
        with open(status_path) as f:
            status = json.load(f)
        
        task_id = status.get("task_id")
        if task_id:
            logger.info(f"⛏  Revoking task {task_id} for job {job_id}")
            celery_app.control.revoke(task_id, terminate=True, signal='SIGTERM')
            
            # Update status to cancelled
            status["state"] = "failed"
            status["current_step"] = "Cancelled by user"
            with open(status_path, "w") as f:
                json.dump(status, f)
            
            # Trigger cleanup
            storage_service.cleanup_job(job_id, keep_output=True)
            
            return {"status": "success", "message": f"Processing for job {job_id} cancelled."}
        else:
            return {"status": "ignored", "message": "No active task ID found for this job."}
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Return the current processing status for a job."""
    _validate_job_id(job_id)

    job_dir = settings.UPLOAD_DIR / job_id
    meta_path = job_dir / "metadata.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    # Check for status file (updated by Celery worker)
    status_path = job_dir / "status.json"
    if status_path.exists():
        with open(status_path) as f:
            status_data = json.load(f)
    else:
        status_data = {
            "state": "uploaded",
            "progress": 0,
            "current_step": "Waiting for processing",
            "details": {},
        }

    # Check for output file
    output_dir = settings.OUTPUT_DIR / job_id
    output_files = list(output_dir.glob("output.*")) if output_dir.exists() else []

    return {
        "job_id": job_id,
        **status_data,
        "output_ready": len(output_files) > 0,
        "output_url": f"/output/{job_id}/{output_files[0].name}" if output_files else None,
    }


@router.get("/status/{job_id}/download")
async def download_output(job_id: str):
    """Download the processed video."""
    _validate_job_id(job_id)
    output_dir = settings.OUTPUT_DIR / job_id
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Output not found")

    output_files = list(output_dir.glob("output.*"))
    if not output_files:
        raise HTTPException(status_code=404, detail="Processing not complete yet")

    # Get original filename from metadata if available
    job_dir = settings.UPLOAD_DIR / job_id
    meta_path = job_dir / "metadata.json"
    filename = f"blockforge_{job_id}.mp4"
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                meta = json.load(f)
                orig_filename = meta.get("original_filename", f"blockforge_{job_id}.mp4")
                # Ensure it ends with .mp4 or appropriate extension
                if not orig_filename.lower().endswith(tuple(f".{ext}" for ext in settings.ALLOWED_EXTENSIONS)):
                    filename = f"{orig_filename}.mp4"
                else:
                    filename = orig_filename
        except Exception:
            pass

    return FileResponse(
        str(output_files[0]),
        media_type="video/mp4",
        filename=filename,
    )


@router.get("/jobs")
async def list_jobs():
    """List all jobs with their current status and previews."""
    jobs = []
    upload_dir = settings.UPLOAD_DIR
    if not upload_dir.exists():
        return {"jobs": []}

    # Iterate through job directories, sorted by newest first
    # Using modification time of the directory for sorting
    try:
        dirs = [d for d in upload_dir.iterdir() if d.is_dir()]
        dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    except Exception:
        dirs = []

    for job_dir in dirs:
        job_id = job_dir.name
        meta_path = job_dir / "metadata.json"
        status_path = job_dir / "status.json"

        # Basic info
        job_info = {
            "job_id": job_id,
            "id": job_id, # Added for consistency with required structure
            "created_at": job_dir.stat().st_mtime,
            "preview_url": f"/uploads/{job_id}/thumbnail.png", # Use thumbnail as default
        }

        # Add metadata if exists
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
                pass

        # Check for output and completed preview
        output_dir = settings.OUTPUT_DIR / job_id
        output_exists = False
        if output_dir.exists():
            output_files = list(output_dir.glob("output.*"))
            if output_files:
                output_exists = True
                job_info["output_ready"] = True
                job_info["output_url"] = f"/output/{job_id}/{output_files[0].name}"
                # If finished, use the 'after' preview if it exists
                after_preview = output_dir / "preview_after.png"
                if after_preview.exists():
                    job_info["preview_url"] = f"/output/{job_id}/preview_after.png"

        # Add status if exists
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
            job_info["state"] = "completed" if output_exists else "uploaded"

        jobs.append(job_info)

    return {"jobs": jobs[:50]}  # Limit to 50 most recent