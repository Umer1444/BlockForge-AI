"""
BlockForge AI – LaMa Inpainting Engine (GPU)
"""

import logging
import sys
import os
import types
import typing
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch

# ── Compatibility Polyfills ──────────────────────────────
# 1. Fix typing.io removal in Python 3.12+
try:
    import typing.io
except ImportError:
    tio = types.ModuleType("typing.io")
    tio.TextIO = typing.TextIO
    sys.modules["typing.io"] = tio

# 2. Fix np.sctypes removal in NumPy 2.0+
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
backend_root = str(Path(__file__).resolve().parents[1])
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

# Verify saicinpainting is reachable
if not (Path(backend_root) / "saicinpainting").exists():
    print(f"ERROR: Saicinpainting package not found in {backend_root}")

from config import settings
from services.gpu_manager import gpu_manager

logger = logging.getLogger("blockforge.inpaint")


class InpaintEngine:
    """GPU-accelerated inpainting using LaMa (Large Mask Inpainting)."""

    def __init__(self, device: Optional[str] = None):
        self.device = device or gpu_manager.current_device
        self.model = None

    def load_model(self):
        """Lazily load the LaMa inpainting model."""
        if self.model is not None:
            return

        try:
            logger.info(f"⛏  Loading LaMa model on {self.device}")


            model_path = Path(settings.LAMA_CHECKPOINT)
            
            # Check for TorchScript version first (faster load)
            jit_path = model_path / "lama.pt"
            if jit_path.exists():
                self.model = torch.jit.load(str(jit_path), map_location=self.device)
            else:
                # Load from Lightning checkpoint using official saicinpainting logic
                try:
                    from saicinpainting.training.trainers import load_checkpoint
                except ImportError as ie:
                    logger.error(f"CRITICAL: Failed to import saicinpainting! {ie}")
                    logger.debug(f"Full sys.path: {sys.path}")
                    raise ie

                from omegaconf import OmegaConf
                import yaml

                config_path = model_path / "config.yaml"
                ckpt_path = model_path / "models" / "best.ckpt"

                if not config_path.exists() or not ckpt_path.exists():
                    # Fallback to general search in the directory
                    pt_files = list(model_path.glob("*.pt"))
                    if pt_files:
                        self.model = torch.jit.load(str(pt_files[0]), map_location=self.device)
                    else:
                        raise FileNotFoundError(f"No checkpoint or config in {model_path}")
                else:
                    # Proper Lightning load
                    with open(config_path, "r") as f:
                        train_config = OmegaConf.create(yaml.safe_load(f))
                    
                    train_config.training_model.predict_only = True
                    train_config.visualizer.kind = "noop"

                    # Convert map_location to string for load_checkpoint
                    map_loc = "cpu" if "cpu" in self.device else "cuda" if "cuda" in self.device else "mps"
                    
                    self.model = load_checkpoint(
                        train_config, 
                        str(ckpt_path), 
                        map_location=self.device,  # Pass raw device
                        strict=False
                    )

            self.model.eval()
            self.model.to(self.device)
            if settings.USE_FP16:
                self.model.half()

            logger.info("⛏  LaMa model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load LaMa: {e}")
            logger.info("⛏  Falling back to OpenCV inpainting (Telea)")
            self.model = "opencv_fallback"

    def _preprocess(self, image: np.ndarray, mask: np.ndarray) -> tuple[torch.Tensor, torch.Tensor]:
        """Convert image+mask to tensors for LaMa."""
        # Normalize image to [0, 1]
        img = image.astype(np.float32) / 255.0
        img = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0)  # (1, 3, H, W)

        # Binary mask: 1 = inpaint region
        msk = mask.astype(np.float32) / 255.0
        msk = torch.from_numpy(msk).unsqueeze(0).unsqueeze(0)  # (1, 1, H, W)

        img = img.to(self.device)
        msk = msk.to(self.device)

        if settings.USE_FP16:
            img = img.half()
            msk = msk.half()

        return img, msk

    def _postprocess(self, output: torch.Tensor) -> np.ndarray:
        """Convert LaMa output tensor back to BGR image."""
        result = output.squeeze(0).permute(1, 2, 0)  # (H, W, 3)
        result = result.clamp(0, 1).float().cpu().numpy()
        
        # ── NaN Safety ──────────────────────────────────────
        if np.isnan(result).any():
            logger.warning("⛏  NaN detected in model output! Replacing with 0.")
            result = np.nan_to_num(result)
            
        result = (result * 255).astype(np.uint8)
        return result

    def inpaint_frame(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Inpaint a single frame.
        
        Args:
            image: BGR image (H, W, 3)
            mask: Binary mask (H, W), 255 = region to inpaint
            
        Returns:
            Inpainted BGR image (H, W, 3)
        """
        self.load_model()

        if self.model == "opencv_fallback":
            return self._opencv_inpaint(image, mask)

        img_t, mask_t = self._preprocess(image, mask)

        batch = {"image": img_t, "mask": mask_t}
        with torch.no_grad():
            if settings.USE_FP16:
                device_type = "cuda" if "cuda" in self.device else "mps" if "mps" in self.device else "cpu"
                if device_type != "cpu":
                    with torch.autocast(device_type=device_type):
                        output_batch = self.model(batch)
                else:
                    output_batch = self.model(batch)
            else:
                output_batch = self.model(batch)

        # LaMa DefaultInpaintingTrainingModule returns the full batch including 'inpainted'
        result = self._postprocess(output_batch["inpainted"])

        # Blend: only replace masked region
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0
        blended = (result * mask_3ch + image * (1 - mask_3ch)).astype(np.uint8)

        return blended

    def _opencv_inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Fallback inpainting using OpenCV Telea algorithm."""
        return cv2.inpaint(image, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

    def inpaint_batch(
        self,
        frames: list[Path],
        masks: list[Path],
        output_dir: Path,
        batch_size: Optional[int] = None,
        progress_callback=None,
    ) -> list[Path]:
        """
        Inpaint a batch of frames with corresponding masks.
        Uses GPU batching for efficiency.
        
        Args:
            frames: List of frame image paths
            masks: List of corresponding mask paths
            output_dir: Directory to save inpainted frames
            batch_size: Number of frames per GPU batch
            progress_callback: fn(current, total) for progress updates
            
        Returns:
            List of inpainted frame paths
        """
        self.load_model()
        output_dir.mkdir(parents=True, exist_ok=True)
        bs = batch_size or settings.GPU_BATCH_SIZE
        output_paths = []

        total = len(frames)
        for i in range(0, total, bs):
            batch_frames = frames[i : i + bs]
            batch_masks = masks[i : i + bs]

            for j, (frame_path, mask_path) in enumerate(zip(batch_frames, batch_masks)):
                image = cv2.imread(str(frame_path))
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

                if image is None or mask is None:
                    logger.warning(f"Skipping frame {i + j}: read error")
                    continue

                result = self.inpaint_frame(image, mask)

                out_path = output_dir / f"inpainted_{i + j:06d}.png"
                cv2.imwrite(str(out_path), result)
                output_paths.append(out_path)

            # Clear GPU cache after each batch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            if progress_callback:
                progress_callback(min(i + bs, total), total)

            logger.debug(f"⛏  Inpainted batch {i // bs + 1}/{(total + bs - 1) // bs}")

        logger.info(f"⛏  Inpainting complete: {len(output_paths)} frames")
        return output_paths

    def cleanup(self):
        """Release GPU memory."""
        if self.model is not None and self.model != "opencv_fallback":
            del self.model
            self.model = None
            torch.cuda.empty_cache()
            logger.info("⛏  LaMa model unloaded, GPU memory freed")
