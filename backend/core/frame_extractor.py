"""
BlockForge AI – Frame Extractor
Extracts frames from video using FFmpeg (lossless PNG).
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional

from config import settings

logger = logging.getLogger("blockforge.frame_extractor")


class FrameExtractor:
    """Extract individual frames from a video using FFmpeg."""

    def __init__(self, video_path: str, job_id: str):
        self.video_path = Path(video_path)
        self.job_id = job_id
        self.frames_dir = settings.FRAMES_DIR / job_id / "original"
        self.frames_dir.mkdir(parents=True, exist_ok=True)

    def extract_all_frames(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> list[Path]:
        """
        Extract all frames as lossless PNG files.
        Returns sorted list of frame file paths.
        """
        cmd = ["ffmpeg", "-y"]

        if start_time is not None:
            cmd.extend(["-ss", str(start_time)])
        
        cmd.extend(["-i", str(self.video_path)])

        if end_time is not None:
            duration = end_time - (start_time or 0)
            cmd.extend(["-t", str(duration)])

        cmd.extend([
            "-fps_mode", "passthrough",
            "-q:v", "1",            # Highest quality
            "-start_number", "0",
            str(self.frames_dir / "frame_%06d.png"),
        ])

        logger.info(f"⛏  Extracting frames: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"Frame extraction failed: {result.stderr[:500]}")

        frames = sorted(self.frames_dir.glob("frame_*.png"))
        logger.info(f"⛏  Extracted {len(frames)} frames for job {self.job_id}")
        return frames

    def extract_single_frame(self, timestamp: float) -> Path:
        """Extract a single frame at a specific timestamp."""
        output_path = self.frames_dir / f"frame_at_{timestamp:.3f}.png"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", str(self.video_path),
            "-frames:v", "1",
            "-q:v", "1",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def extract_audio(self) -> Optional[Path]:
        """Extract audio stream to preserve during rebuild."""
        audio_path = settings.FRAMES_DIR / self.job_id / "audio.aac"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(self.video_path),
            "-vn",                 # No video
            "-acodec", "copy",     # Copy audio without re-encoding
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0 and audio_path.exists():
            logger.info(f"⛏  Audio extracted for job {self.job_id}")
            return audio_path
        else:
            logger.warning(f"No audio stream found in job {self.job_id}")
            return None

    def get_frame_count(self) -> int:
        """Count total extracted frames."""
        return len(list(self.frames_dir.glob("frame_*.png")))
