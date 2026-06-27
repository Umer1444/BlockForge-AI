"""
BlockForge AI – Video Rebuilder
Reassemble processed frames into video using FFmpeg with original settings.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional

from config import settings

logger = logging.getLogger("blockforge.video_rebuilder")


class VideoRebuilder:
    """Rebuild video from processed frames preserving original quality settings."""

    def __init__(self, job_id: str, metadata: dict):
        self.job_id = job_id
        self.metadata = metadata
        self.output_dir = settings.OUTPUT_DIR / job_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def rebuild(
        self,
        frames_dir: Path,
        frame_pattern: str = "smoothed_%06d.png",
        audio_path: Optional[Path] = None,
        crf: Optional[int] = None,
        codec: Optional[str] = None,
        preset: Optional[str] = None,
        extra_ffmpeg_args: Optional[list] = None,
    ) -> Path:
        """
        Rebuild video from frames using FFmpeg.
        
        Preserves:
        - Original FPS
        - Original resolution
        - Original bitrate (via CRF matching)
        - Original pixel format
        - Audio stream
        
        Args:
            extra_ffmpeg_args: Additional FFmpeg arguments for quality preservation
        
        Returns:
            Path to the rebuilt output video.
        """
        output_path = self.output_dir / "output.mp4"
        fps = self.metadata.get("fps_raw", str(self.metadata.get("fps", 30)))
        width = self.metadata.get("width", 1920)
        height = self.metadata.get("height", 1080)
        pix_fmt = self.metadata.get("pixel_format", "yuv420p")
        original_bitrate = self.metadata.get("bitrate", 0)

        _codec = codec or settings.DEFAULT_CODEC
        _crf = crf or settings.DEFAULT_CRF
        _preset = preset or settings.DEFAULT_PRESET

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / frame_pattern),
        ]

        # Add audio if available
        if audio_path and audio_path.exists():
            cmd.extend(["-i", str(audio_path)])

        cmd.extend([
            "-c:v", _codec,
            "-crf", str(_crf),
            "-preset", _preset,
            "-pix_fmt", pix_fmt,
        ])

        # Add extra quality preservation args if provided
        if extra_ffmpeg_args:
            cmd.extend(extra_ffmpeg_args)

        # Target bitrate to match original
        if original_bitrate > 0:
            cmd.extend([
                "-maxrate", f"{int(original_bitrate * 1.2)}",
                "-bufsize", f"{int(original_bitrate * 2)}",
            ])

        # Resolution (ensure even dimensions)
        w = width if width % 2 == 0 else width + 1
        h = height if height % 2 == 0 else height + 1
        cmd.extend(["-vf", f"scale={w}:{h}"])

        # Audio mapping
        if audio_path and audio_path.exists():
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
            ])

        cmd.extend([
            "-movflags", "+faststart",  # Web-friendly MP4
            str(output_path),
        ])

        logger.info(f"⛏  Rebuilding video: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg rebuild failed: {result.stderr}")
            raise RuntimeError(f"Video rebuild failed: {result.stderr[:500]}")

        # Verify output
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Output video is empty or was not created")

        output_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"⛏  Video rebuilt: {output_path} ({output_size_mb:.1f} MB)")

        return output_path

    def get_output_metadata(self) -> dict:
        """Verify output video metadata."""
        output_path = self.output_dir / "output.mp4"
        if not output_path.exists():
            return {}

        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout) if result.returncode == 0 else {}
