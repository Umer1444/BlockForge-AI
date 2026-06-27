"""
BlockForge AI – Processing Trigger API
Extended with Auto-Detection, Hybrid, and Quality Preservation modes.
"""

import json
import base64
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from workers.tasks import celery_app
from services.batch_manager import BatchJobManager, JobPriority

router = APIRouter()
logger = logging.getLogger("blockforge.process")

batch_manager = BatchJobManager(settings.REDIS_URL)


class MaskPoint(BaseModel):
    x: int
    y: int


class ProcessRequest(BaseModel):
    job_id: str
    # Masking mode: manual | sam_points | auto | hybrid
    mode: str = "manual"
    
    # Manual mask as base64-encoded PNG (for manual mode)
    mask_base64: Optional[str] = None
    
    # SAM prompt points (for sam_points mode)
    sam_points: Optional[list[MaskPoint]] = None
    sam_labels: Optional[list[int]] = None  # 1 = foreground, 0 = background
    
    # Auto-detection config
    text_confidence: float = 0.5      # OCR confidence threshold
    logo_confidence: float = 0.4      # Object detection confidence threshold
    
    # Hybrid mode refinements
    refinements: Optional[dict] = None  # {frame_index: {mode: add|remove|replace, mask_path: ...}}
    
    # Quality preservation
    quality_preset: str = "standard"  # original | highest | high | standard | balanced | web
    preserve_bitrate: bool = True
    
    # Processing options
    use_enhancement: bool = False
    codec: str = "libx264"
    preset: str = "slow"
    batch_size: int = 4
    priority: str = "normal"  # normal | high | urgent


@router.post("/process")
async def start_processing(req: ProcessRequest):
    """Accept mask data and dispatch a processing task with quality preservation."""

    # Validate job exists
    job_dir = settings.UPLOAD_DIR / req.job_id
    meta_path = job_dir / "metadata.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Job not found. Upload a video first.")

    with open(meta_path) as f:
        metadata = json.load(f)

    # Save mask data based on mode
    mask_dir = settings.MASKS_DIR / req.job_id
    mask_dir.mkdir(parents=True, exist_ok=True)

    mask_info = {"type": "none"}

    if req.mode == "manual":
        if not req.mask_base64:
            raise HTTPException(status_code=400, detail="Manual mode requires mask_base64")
        
        # Decode and save manual mask
        mask_bytes = base64.b64decode(req.mask_base64)
        mask_path = mask_dir / "manual_mask.png"
        with open(mask_path, "wb") as f:
            f.write(mask_bytes)
        mask_info = {"type": "manual", "path": str(mask_path)}
        logger.info(f"⛏  Manual mask saved for job {req.job_id}")

    elif req.mode == "sam_points":
        if not req.sam_points:
            raise HTTPException(status_code=400, detail="SAM mode requires sam_points")
        
        # Save SAM prompt points for AI mask generation
        sam_data = {
            "points": [{"x": p.x, "y": p.y} for p in req.sam_points],
            "labels": req.sam_labels or [1] * len(req.sam_points),
        }
        sam_path = mask_dir / "sam_prompts.json"
        with open(sam_path, "w") as f:
            json.dump(sam_data, f)
        mask_info = {"type": "sam", "path": str(sam_path)}
        logger.info(f"⛏  SAM prompts saved for job {req.job_id}")

    elif req.mode == "auto":
        # Auto-detection mode: AI detects watermarks
        mask_info = {
            "type": "auto",
            "text_confidence": req.text_confidence,
            "logo_confidence": req.logo_confidence,
        }
        logger.info(f"⛏  Auto-detection mode configured for job {req.job_id}")

    elif req.mode == "hybrid":
        # Hybrid mode: AI detects + user refines
        mask_info = {
            "type": "hybrid",
            "text_confidence": req.text_confidence,
            "logo_confidence": req.logo_confidence,
            "refinements": req.refinements or {},
        }
        logger.info(f"⛏  Hybrid mode configured for job {req.job_id}")

    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {req.mode}")

    # Determine CRF from quality preset
    quality_crf_map = {
        "original": 0,
        "highest": 1,
        "high": 10,
        "standard": 18,
        "balanced": 23,
        "web": 28,
    }
    crf = quality_crf_map.get(req.quality_preset, 18)

    # Build task payload with quality preservation options
    task_payload = {
        "job_id": req.job_id,
        "video_path": metadata["file_path"],
        "metadata": metadata,
        "mask_info": mask_info,
        "options": {
            "use_enhancement": req.use_enhancement,
            "crf": crf,
            "codec": req.codec,
            "preset": req.preset,
            "batch_size": req.batch_size,
            "quality_preset": req.quality_preset,
            "preserve_bitrate": req.preserve_bitrate,
        },
    }


    # Dispatch Celery task
    from workers.tasks import process_video_task
    import time

    task = process_video_task.delay(task_payload)

    # Initialize status file with task_id
    status_path = job_dir / "status.json"
    status_data = {
        "job_id": req.job_id,
        "task_id": task.id,
        "state": "queued",
        "progress": 0,
        "current_step": "Job queued",
        "timestamp": time.time(),
    }
    with open(status_path, "w") as f:
        json.dump(status_data, f)

    logger.info(f"⛏  Processing dispatched: job={req.job_id}, celery_task={task.id}")

    return {
        "job_id": req.job_id,
        "task_id": task.id,
        "status": "queued",
        "message": "Processing started. Connect to WebSocket for live updates.",
        "ws_url": f"/ws/{req.job_id}",
    }


@router.post("/batch-process")
async def batch_process(jobs: list[ProcessRequest]):
    """Submit multiple jobs for batch processing."""
    priority_map = {
        "urgent": JobPriority.URGENT,
        "high": JobPriority.HIGH,
        "normal": JobPriority.NORMAL,
        "low": JobPriority.LOW,
    }

    submitted_jobs = []
    for job_req in jobs:
        try:
            priority = priority_map.get(job_req.priority, JobPriority.NORMAL)
            batch_job = batch_manager.submit_job(
                job_req.job_id,
                priority=priority,
                metadata={
                    "mode": job_req.mode,
                    "quality_preset": job_req.quality_preset,
                },
            )
            submitted_jobs.append(batch_job.to_dict())
        except Exception as e:
            logger.error(f"Failed to submit job {job_req.job_id}: {e}")

    return {
        "submitted": len(submitted_jobs),
        "jobs": submitted_jobs,
        "queue_size": batch_manager.get_queue_stats(),
    }


@router.get("/queue-status")
async def get_queue_status():
    """Get current queue statistics."""
    return batch_manager.get_queue_stats()


@router.post("/preview-auto-detect/{job_id}")
async def preview_auto_detect(job_id: str, request_body: dict = None):
    """
    Generate preview of auto-detected watermarks before processing.
    
    This allows users to validate AI detection before committing to processing.
    """
    from core.frame_extractor import FrameExtractor
    from core.watermark_detector import WatermarkDetector
    from core.preview_renderer import PreviewRenderer

    job_dir = settings.UPLOAD_DIR / job_id
    meta_path = job_dir / "metadata.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with open(meta_path) as f:
        metadata = json.load(f)

    video_path = metadata["file_path"]

    # Extract first frame for preview
    extractor = FrameExtractor(video_path, job_id)
    first_frame_path = extractor.extract_single_frame(0.0)

    # Detect watermarks
    detector = WatermarkDetector()
    text_confidence = request_body.get("text_confidence", 0.5) if request_body else 0.5
    logo_confidence = request_body.get("logo_confidence", 0.4) if request_body else 0.4

    frame = cv2.imread(str(first_frame_path))
    detections = detector.detect_all_watermarks(
        frame,
        text_confidence=text_confidence,
        logo_confidence=logo_confidence,
    )

    # Generate preview with highlights
    renderer = PreviewRenderer(width=1280, height=720)
    preview = renderer.render_watermark_highlight(frame, detections, opacity=0.4)

    preview_path = job_dir / "detection_preview.png"
    renderer.save_preview(preview, preview_path)

    detector.cleanup()

    return {
        "detections": len(detections),
        "preview_url": f"/uploads/{job_id}/detection_preview.png",
        "detections_data": [
            {
                "type": d.type,
                "confidence": d.confidence,
                "bbox": d.bbox,
                "text": d.text,
            }
            for d in detections
        ],
    }

