"""
BlockForge AI – Real-ESRGAN Enhancement Engine
Optional post-inpainting super-resolution / quality enhancement.
"""

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch

from config import settings
from services.gpu_manager import gpu_manager

logger = logging.getLogger("blockforge.enhancer")


class Enhancer:
    """GPU-accelerated image enhancement using Real-ESRGAN."""

    def __init__(self, device: Optional[str] = None):
        self.device = device or gpu_manager.current_device
        self.model = None

    def load_model(self):
        """Lazily load Real-ESRGAN model."""
        if self.model is not None:
            return

        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer

            rrdb_model = RRDBNet(
                num_in_ch=3, num_out_ch=3,
                num_feat=64, num_block=23, num_grow_ch=32, scale=settings.REALESRGAN_SCALE,
            )

            self.model = RealESRGANer(
                scale=settings.REALESRGAN_SCALE,
                model_path=settings.REALESRGAN_MODEL,
                model=rrdb_model,
                tile=512,            # Process in tiles to save GPU memory
                tile_pad=10,
                pre_pad=0,
                half=settings.USE_FP16,
                device=self.device,
            )
            logger.info("⛏  Real-ESRGAN loaded successfully")

        except ImportError:
            logger.warning("Real-ESRGAN not installed. Enhancement unavailable.")
            self.model = "unavailable"

    def enhance_frame(self, image: np.ndarray, outscale: int = 1) -> np.ndarray:
        """
        Enhance a single frame.
        
        If outscale == 1, upscale then downscale to original size
        (quality enhancement without resolution change).
        """
        self.load_model()

        if self.model == "unavailable":
            logger.warning("Enhancement skipped (model unavailable)")
            return image

        try:
            output, _ = self.model.enhance(image, outscale=outscale or settings.REALESRGAN_SCALE)

            # If we don't want resolution change, resize back to original
            if outscale == 1:
                h, w = image.shape[:2]
                output = cv2.resize(output, (w, h), interpolation=cv2.INTER_LANCZOS4)

            return output

        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return image  # Return original if enhancement fails

    def enhance_batch(
        self,
        frames: list[Path],
        output_dir: Path,
        outscale: int = 1,
        progress_callback=None,
    ) -> list[Path]:
        """
        Enhance a batch of frames.
        
        Returns list of enhanced frame paths.
        """
        self.load_model()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths = []
        total = len(frames)

        for i, frame_path in enumerate(frames):
            image = cv2.imread(str(frame_path))
            if image is None:
                continue

            enhanced = self.enhance_frame(image, outscale)

            out_path = output_dir / f"enhanced_{i:06d}.png"
            cv2.imwrite(str(out_path), enhanced)
            output_paths.append(out_path)

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            if progress_callback and i % 5 == 0:
                progress_callback(i + 1, total)

        logger.info(f"⛏  Enhancement complete: {len(output_paths)} frames")
        return output_paths

    def cleanup(self):
        """Release GPU memory."""
        if self.model is not None and self.model != "unavailable":
            del self.model
            self.model = None
            torch.cuda.empty_cache()
            logger.info("⛏  Real-ESRGAN unloaded, GPU memory freed")
