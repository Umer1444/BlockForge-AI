"""
BlockForge AI – Quality Preservation Engine
Handles lossless/near-lossless export and bitrate preservation.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Optional
from enum import Enum

from config import settings

logger = logging.getLogger("blockforge.quality")


class ExportQuality(Enum):
    """Export quality presets."""
    ORIGINAL = "original"  # Lossless (CRF 0)
    HIGHEST = "highest"    # Near-lossless (CRF 1-2)
    HIGH = "high"           # High quality (CRF 10)
    STANDARD = "standard"   # Default (CRF 18)
    BALANCED = "balanced"   # Balanced (CRF 23)
    WEB = "web"             # Web-optimized (CRF 28)


class QualityPreservationEngine:
    """
    Preserve original video quality through processing:
    - Detect original resolution, bitrate, codec
    - Apply lossless/near-lossless encoding
    - Validate output quality
    """

    # CRF to bitrate multiplier mapping (for H.264)
    CRF_BITRATE_MAP = {
        0: 1.0,     # Lossless
        1: 0.95,
        2: 0.90,
        10: 0.70,
        18: 0.50,   # Default
        23: 0.35,
        28: 0.20,
    }

    def __init__(self, metadata: dict):
        """
        Args:
            metadata: Video metadata (from upload endpoint)
        """
        self.metadata = metadata
        self.original_width = metadata.get("width", 1920)
        self.original_height = metadata.get("height", 1080)
        self.original_fps = metadata.get("fps", 30)
        self.original_bitrate = metadata.get("bitrate", 0)
        self.original_codec = metadata.get("codec", "h264")
        self.original_pix_fmt = metadata.get("pixel_format", "yuv420p")

    def get_crf_for_quality(self, quality: ExportQuality) -> int:
        """Get CRF value for quality preset."""
        crf_map = {
            ExportQuality.ORIGINAL: 0,
            ExportQuality.HIGHEST: 1,
            ExportQuality.HIGH: 10,
            ExportQuality.STANDARD: 18,
            ExportQuality.BALANCED: 23,
            ExportQuality.WEB: 28,
        }
        return crf_map.get(quality, 18)

    def estimate_bitrate(self, crf: int) -> int:
        """
        Estimate output bitrate based on CRF value.
        Returns bitrate in bits/second.
        """
        if self.original_bitrate == 0:
            # Estimate from resolution and FPS
            pixel_count = self.original_width * self.original_height * self.original_fps
            base_bitrate = max(1000000, pixel_count / 1000)  # 1 Mbps minimum
        else:
            base_bitrate = self.original_bitrate

        multiplier = self.CRF_BITRATE_MAP.get(crf, 0.5)
        return int(base_bitrate * multiplier)

    def get_ffmpeg_quality_args(
        self,
        quality: ExportQuality,
        preserve_original: bool = False,
    ) -> list:
        """
        Get FFmpeg arguments for quality preservation.

        Args:
            quality: Quality preset
            preserve_original: If True, use CRF 0 and other lossless settings

        Returns:
            List of FFmpeg command arguments
        """
        if preserve_original:
            crf = 0
        else:
            crf = self.get_crf_for_quality(quality)

        args = [
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", "slow",  # Slower preset for better compression
            "-pix_fmt", self.original_pix_fmt,
        ]

        # Add bitrate constraints
        target_bitrate = self.estimate_bitrate(crf)

        # For lossless/near-lossless, remove bitrate restrictions
        if crf > 2:
            args.extend([
                "-maxrate", f"{int(target_bitrate * 1.2)}",
                "-bufsize", f"{int(target_bitrate * 2)}",
            ])

        # Add codec-specific optimizations
        args.extend([
            "-x264opts", "aq-mode=3:aq-strength=1.0",  # Adaptive quantization
        ])

        return args

    def validate_output_quality(
        self,
        output_path: Path,
        original_path: Path,
        tolerance_percent: float = 5.0,
    ) -> dict:
        """
        Validate output video quality against original.

        Args:
            output_path: Path to processed video
            original_path: Path to original video
            tolerance_percent: Acceptable quality loss percentage

        Returns:
            Validation report
        """
        report = {
            "valid": True,
            "issues": [],
        }

        # Extract metadata from output
        output_metadata = self._extract_metadata(output_path)

        # Check resolution
        if (output_metadata["width"] != self.original_width or
                output_metadata["height"] != self.original_height):
            report["valid"] = False
            report["issues"].append(
                f"Resolution mismatch: {output_metadata['width']}x{output_metadata['height']} "
                f"vs {self.original_width}x{self.original_height}"
            )

        # Check FPS
        if abs(output_metadata["fps"] - self.original_fps) > 0.1:
            report["valid"] = False
            report["issues"].append(
                f"FPS mismatch: {output_metadata['fps']} vs {self.original_fps}"
            )

        # Check bitrate (within tolerance)
        if self.original_bitrate > 0:
            bitrate_diff = abs(output_metadata["bitrate"] - self.original_bitrate) / self.original_bitrate * 100
            if bitrate_diff > tolerance_percent:
                report["issues"].append(
                    f"Bitrate loss: {bitrate_diff:.1f}% (tolerating {tolerance_percent}%)"
                )

        # Check file sizes
        output_size = output_path.stat().st_size
        original_size = original_path.stat().st_size
        size_ratio = (output_size / original_size * 100) if original_size > 0 else 0

        report["output_size_mb"] = round(output_size / (1024**2), 2)
        report["original_size_mb"] = round(original_size / (1024**2), 2)
        report["size_ratio_percent"] = round(size_ratio, 1)

        if size_ratio > 105:
            report["issues"].append(f"Output larger than original: {size_ratio:.1f}%")

        return report

    def _extract_metadata(self, video_path: Path) -> dict:
        """Extract video metadata using ffprobe."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"ffprobe failed: {result.stderr}")
            return {}

        probe = json.loads(result.stdout)
        video_stream = next(
            (s for s in probe.get("streams", []) if s["codec_type"] == "video"),
            {},
        )
        fmt = probe.get("format", {})

        fps_str = video_stream.get("r_frame_rate", "30/1")
        num, den = map(int, fps_str.split("/"))
        fps = num / den if den else 30.0

        return {
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": fps,
            "bitrate": int(fmt.get("bit_rate", 0)),
            "codec": video_stream.get("codec_name", "unknown"),
            "duration": float(fmt.get("duration", 0)),
        }

    def get_quality_report(
        self,
        output_path: Path,
        original_path: Path,
    ) -> dict:
        """Generate comprehensive quality comparison report."""
        output_meta = self._extract_metadata(output_path)
        original_meta = self._extract_metadata(original_path)

        return {
            "original": original_meta,
            "output": output_meta,
            "resolution_preserved": (
                output_meta["width"] == original_meta["width"] and
                output_meta["height"] == original_meta["height"]
            ),
            "fps_preserved": abs(output_meta["fps"] - original_meta["fps"]) < 0.1,
            "bitrate_ratio": (
                output_meta["bitrate"] / original_meta["bitrate"]
                if original_meta["bitrate"] > 0 else 1.0
            ),
            "file_size_ratio": (
                output_path.stat().st_size / original_path.stat().st_size
                if original_path.stat().st_size > 0 else 1.0
            ),
        }
