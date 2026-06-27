import sys
import os
import types
import typing
from pathlib import Path
import numpy as np

# ── Compatibility Polyfills ──────────────────────────────
# 1. Fix typing.io removal in Python 3.12+
try:
    import typing.io
except ImportError:
    tio = types.ModuleType("typing.io")
    tio.TextIO = typing.TextIO
    sys.modules["typing.io"] = tio

# 2. Fix np.sctypes removal in NumPy 2.0+ (for imgaug/LaMa)
if not hasattr(np, "sctypes"):
    np.sctypes = {
        'int': [np.int8, np.int16, np.int32, np.int64],
        'uint': [np.uint8, np.uint16, np.uint32, np.uint64],
        'float': [np.float16, np.float32, np.float64],
        'complex': [np.complex64, np.complex128],
        'others': [bool, object, bytes, str, memoryview]
    }

# ── Path Resolution ───────────────────────────────────────
# Ensure the root 'backend' directory is in sys.path
# This is critical for finding 'saicinpainting' and 'core' modules.
backend_root = str(Path(__file__).resolve().parents[1])
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)


import json
import logging
import time
import redis
from celery import Celery
from typing import Any

# Import core modules at top-level for worker clarity
from config import settings
from core.frame_extractor import FrameExtractor
from core.mask_engine import MaskEngine
from core.inpaint_engine import InpaintEngine
from core.optical_flow import OpticalFlowSmoother
from core.enhancer import Enhancer
from core.video_rebuilder import VideoRebuilder
from core.quality_engine import QualityPreservationEngine, ExportQuality
from services.storage_service import StorageService

logger = logging.getLogger("blockforge.tasks")

# ── Celery App ───────────────────────────────────────────
celery_app = Celery(
    "blockforge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # One task at a time (GPU-bound)
)


def _publish_progress(job_id: str, state: str, progress: int, step: str, details: dict = None):
    """Publish progress update to Redis pub/sub and save status file."""
    data = {
        "state": state,
        "progress": progress,
        "current_step": step,
        "details": details or {},
        "timestamp": time.time(),
    }

    # Save to status file
    status_path = settings.UPLOAD_DIR / job_id / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with open(status_path, "w") as f:
        json.dump(data, f)

    # Publish to Redis pub/sub for WebSocket streaming
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.publish(f"blockforge:progress:{job_id}", json.dumps(data))
        r.close()
    except Exception as e:
        logger.warning(f"Redis publish failed: {e}")


@celery_app.task(bind=True, name="blockforge.process_video")
def process_video_task(self, payload: dict) -> dict:
    """
    Full video processing pipeline:
    
    1. Extract frames
    2. Extract audio
    3. Generate / load masks
    4. GPU inpainting (LaMa)
    5. Temporal smoothing (optical flow)
    6. Optional enhancement (Real-ESRGAN)
    7. Rebuild video
    """
    job_id = payload["job_id"]
    video_path = payload["video_path"]
    metadata = payload["metadata"]
    mask_info = payload["mask_info"]
    options = payload.get("options", {})

    logger.info(f"⛏  Starting pipeline for job {job_id}")

    try:
        # ── Step 1: Extract frames ──────────────────────
        _publish_progress(job_id, "processing", 5, "Extracting frames...")

        extractor = FrameExtractor(video_path, job_id)
        frames = extractor.extract_all_frames()
        audio_path = extractor.extract_audio()

        total_frames = len(frames)
        _publish_progress(
            job_id, "processing", 15,
            f"Extracted {total_frames} frames",
            {"total_frames": total_frames},
        )

        # ── Step 2: Generate masks ──────────────────────
        _publish_progress(job_id, "processing", 20, "Generating masks...")

        mask_engine = MaskEngine()
        mask_paths = mask_engine.generate_masks_for_job(job_id, mask_info, frames)
        mask_engine.cleanup()

        _publish_progress(job_id, "processing", 30, f"Masks ready for {len(mask_paths)} frames")

        # ── Step 3: GPU Inpainting ──────────────────────
        _publish_progress(job_id, "processing", 35, "GPU inpainting in progress...")

        dirs = StorageService.ensure_job_dirs(job_id)
        inpaint_engine = InpaintEngine()

        def inpaint_progress(current, total):
            pct = 35 + int((current / total) * 30)  # 35% to 65%
            _publish_progress(
                job_id, "processing", pct,
                f"Inpainting frame {current}/{total}",
                {"current_frame": current, "total_frames": total},
            )

        inpainted_frames = inpaint_engine.inpaint_batch(
            frames, mask_paths,
            dirs["inpainted"],
            batch_size=options.get("batch_size", settings.GPU_BATCH_SIZE),
            progress_callback=inpaint_progress,
        )
        inpaint_engine.cleanup()

        # ── Step 4: Temporal smoothing ──────────────────
        _publish_progress(job_id, "processing", 68, "Temporal smoothing...")

        smoother = OpticalFlowSmoother()

        def smooth_progress(current, total):
            pct = 68 + int((current / total) * 12)  # 68% to 80%
            _publish_progress(
                job_id, "processing", pct,
                f"Smoothing frame {current}/{total}",
            )

        smoothed_frames = smoother.smooth_sequence(
            inpainted_frames, mask_paths,
            dirs["smoothed"],
            progress_callback=smooth_progress,
        )

        # ── Step 5: Optional enhancement ────────────────
        final_frames_dir = dirs["smoothed"]
        final_pattern = "smoothed_%06d.png"

        if options.get("use_enhancement", False):
            _publish_progress(job_id, "processing", 82, "Enhancing frames with Real-ESRGAN...")

            enhancer = Enhancer()

            def enhance_progress(current, total):
                pct = 82 + int((current / total) * 8)  # 82% to 90%
                _publish_progress(
                    job_id, "processing", pct,
                    f"Enhancing frame {current}/{total}",
                )

            enhanced_frames = enhancer.enhance_batch(
                smoothed_frames,
                dirs["enhanced"],
                progress_callback=enhance_progress,
            )
            enhancer.cleanup()

            if enhanced_frames:
                final_frames_dir = dirs["enhanced"]
                final_pattern = "enhanced_%06d.png"

        # ── Step 6: Rebuild video with quality preservation ─────────────
        _publish_progress(job_id, "processing", 92, "Rebuilding video with quality preservation...")

        # Initialize quality engine
        quality_engine = QualityPreservationEngine(metadata)
        quality_preset = options.get("quality_preset", "standard")
        
        try:
            quality_enum = ExportQuality(quality_preset)
        except ValueError:
            quality_enum = ExportQuality.STANDARD
        
        rebuilder = VideoRebuilder(job_id, metadata)
        
        # Get quality-preserving FFmpeg args
        if options.get("preserve_bitrate", True):
            extra_args = quality_engine.get_ffmpeg_quality_args(
                quality=quality_enum,
                preserve_original=(quality_enum == ExportQuality.ORIGINAL),
            )
        else:
            extra_args = []
        
        output_path = rebuilder.rebuild(
            final_frames_dir,
            frame_pattern=final_pattern,
            audio_path=audio_path,
            crf=options.get("crf", settings.DEFAULT_CRF),
            codec=options.get("codec", settings.DEFAULT_CODEC),
            preset=options.get("preset", settings.DEFAULT_PRESET),
            extra_ffmpeg_args=extra_args,
        )
        
        # ── Quality validation ──────────────────────────
        _publish_progress(job_id, "processing", 94, "Validating output quality...")
        
        original_video_path = Path(metadata["file_path"])
        quality_report = quality_engine.get_quality_report(output_path, original_video_path)
        
        # Save quality report
        quality_report_path = output_path.parent / "quality_report.json"
        with open(quality_report_path, "w") as f:
            json.dump(quality_report, f, indent=2)
        
        logger.info(f"⛏  Quality report: {quality_report}")
 
        # ── Step 7: Generate result preview ─────────────
        _publish_progress(job_id, "processing", 96, "Generating result preview...")
        preview_after_path = output_path.parent / "preview_after.png"
        preview_cmd = [
            "ffmpeg", "-y",
            "-i", str(output_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(preview_after_path),
        ]
        import subprocess
        subprocess.run(preview_cmd, capture_output=True)

        # ── Cleanup temp frames ─────────────────────────
        _publish_progress(job_id, "processing", 98, "Cleaning up temporary files...")
        StorageService.cleanup_job(job_id, keep_output=True)

        # ── Done ────────────────────────────────────────
        _publish_progress(
            job_id, "completed", 100,
            "Processing complete!",
            {
                "output_path": str(output_path),
                "output_url": f"/output/{job_id}/output.mp4",
                "preview_after_url": f"/output/{job_id}/preview_after.png",
                "quality_preserved": quality_report.get("resolution_preserved", True),
                "quality_report": quality_report,
            },
        )

        logger.info(f"⛏  Pipeline complete for job {job_id}")
        return {
            "job_id": job_id,
            "status": "completed",
            "output_url": f"/output/{job_id}/output.mp4",
            "quality_report": quality_report,
        }

    except Exception as e:
        logger.error(f"Pipeline failed for job {job_id}: {e}", exc_info=True)
        _publish_progress(
            job_id, "failed", 0,
            f"Processing failed: {str(e)}",
            {"error": str(e)},
        )
        # ── Cleanup even on failure to save disk space ──
        try:
            StorageService.cleanup_job(job_id, keep_output=True)
        except:
            pass
        raise
