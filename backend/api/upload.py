"""
BlockForge AI – Video Upload API
"""

import uuid
import shutil
import subprocess
import json
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from config import settings

router = APIRouter()
logger = logging.getLogger("blockforge.upload")


def _extract_video_metadata(filepath: Path) -> dict:
    """Use ffprobe to extract resolution, fps, bitrate, duration, codec."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(filepath),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"ffprobe failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid or corrupt video file")

    video_stream = next(
        (s for s in probe.get("streams", []) if s["codec_type"] == "video"), None
    )
    if not video_stream:
        raise HTTPException(status_code=400, detail="No video stream found")

    fmt = probe.get("format", {})

    # Parse frame rate (e.g. "30000/1001")
    fps_str = video_stream.get("r_frame_rate", "30/1")
    num, den = map(int, fps_str.split("/"))
    fps = round(num / den, 3) if den else 30.0

    # Determine orientation
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    if width > height:
        orientation = "landscape"
    elif height > width:
        orientation = "portrait"
    else:
        orientation = "square"

    return {
        "width": width,
        "height": height,
        "resolution": f"{width}x{height}",
        "orientation": orientation,
        "fps": fps,
        "fps_raw": fps_str,
        "bitrate": int(fmt.get("bit_rate", 0)),
        "duration": float(fmt.get("duration", 0)),
        "codec": video_stream.get("codec_name", "unknown"),
        "pixel_format": video_stream.get("pix_fmt", "yuv420p"),
        "total_frames": int(video_stream.get("nb_frames", 0)) or int(fps * float(fmt.get("duration", 0))),
        "file_size": int(fmt.get("size", 0)),
    }


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file and return a job_id + extracted metadata."""

    # Validate extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: .{ext}. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Validate size
    file.file.seek(0, 2)
    size_mb = file.file.tell() / (1024 * 1024)
    file.file.seek(0)
    if size_mb > settings.MAX_VIDEO_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Max: {settings.MAX_VIDEO_SIZE_MB} MB",
        )

    # Save with unique ID
    job_id = str(uuid.uuid4())
    job_dir = settings.UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    filepath = job_dir / f"original.{ext}"

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract metadata
    metadata = _extract_video_metadata(filepath)

    # Save metadata alongside video
    meta_path = job_dir / "metadata.json"
    meta_data = {
        "job_id": job_id,
        "original_filename": file.filename,
        "extension": ext,
        "file_path": str(filepath),
        "size_mb": round(size_mb, 2),
        **metadata,
    }
    with open(meta_path, "w") as f:
        json.dump(meta_data, f, indent=2)

    # Generate thumbnail
    thumbnail_path = job_dir / "thumbnail.png"
    thumb_cmd = [
        "ffmpeg", "-y",
        "-i", str(filepath),
        "-frames:v", "1",
        "-update", "1",
        "-q:v", "2",
        str(thumbnail_path),
    ]
    try:
        subprocess.run(thumb_cmd, capture_output=True, check=True)
        logger.info(f"Generated thumbnail for job {job_id}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Thumbnail generation failed: {e.stderr.decode()}")

    logger.info(f"⛏  Uploaded {file.filename} → job {job_id} ({metadata['width']}x{metadata['height']} @ {metadata['fps']}fps)")

    return {
        "job_id": job_id,
        "metadata": {**meta_data, "thumbnail_url": f"/uploads/{job_id}/thumbnail.png"},
        "message": "Video uploaded successfully. Ready for processing.",
    }


@router.get("/upload/{job_id}/frame")
async def get_preview_frame(job_id: str, time: float = 0.0):
    """Extract a single frame at a given timestamp for mask drawing preview."""
    job_dir = settings.UPLOAD_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    # Find video file
    video_files = list(job_dir.glob("original.*"))
    if not video_files:
        raise HTTPException(status_code=404, detail="Video not found")

    frame_path = job_dir / "preview_frame.png"
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(time),
        "-i", str(video_files[0]),
        "-frames:v", "1",
        "-q:v", "1",
        str(frame_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    from fastapi.responses import FileResponse
    return FileResponse(str(frame_path), media_type="image/png")
