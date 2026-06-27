"""
BlockForge AI – Optical Flow Temporal Smoothing
Ensures temporal consistency between inpainted frames.
"""

import logging
from pathlib import Path

import cv2
import numpy as np

from config import settings

logger = logging.getLogger("blockforge.optical_flow")


class OpticalFlowSmoother:
    """
    Smooth inpainted frames using optical flow to eliminate
    temporal flickering and ensure consistency across frames.
    """

    def __init__(self, blend_strength: float = 0.6, window_size: int = 3):
        """
        Args:
            blend_strength: How much to blend with warped neighbor (0-1).
            window_size: Temporal window for smoothing (odd number).
        """
        self.blend_strength = blend_strength
        self.window_size = window_size

    def compute_flow(self, prev_frame: np.ndarray, next_frame: np.ndarray) -> np.ndarray:
        """
        Compute dense optical flow between two frames using Farneback.
        
        Returns:
            Flow field (H, W, 2) – displacement vectors for each pixel.
        """
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        next_gray = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)

        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, next_gray,
            flow=None,
            pyr_scale=0.5,
            levels=5,
            winsize=15,
            iterations=3,
            poly_n=7,
            poly_sigma=1.5,
            flags=cv2.OPTFLOW_FARNEBACK_GAUSSIAN,
        )
        return flow

    def warp_frame(self, frame: np.ndarray, flow: np.ndarray) -> np.ndarray:
        """Warp a frame using an optical flow field."""
        h, w = flow.shape[:2]
        map_x = np.float32(np.arange(w))
        map_y = np.float32(np.arange(h))
        map_x, map_y = np.meshgrid(map_x, map_y)

        remap_x = map_x + flow[..., 0]
        remap_y = map_y + flow[..., 1]

        warped = cv2.remap(
            frame, remap_x, remap_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )
        return warped

    def smooth_pair(
        self,
        current: np.ndarray,
        neighbor: np.ndarray,
        mask: np.ndarray,
    ) -> np.ndarray:
        """
        Smooth current frame using flow-warped neighbor.
        Only blend in the masked (inpainted) region.
        """
        flow = self.compute_flow(neighbor, current)
        warped = self.warp_frame(neighbor, flow)

        # Only blend in the mask region
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0
        alpha = self.blend_strength * mask_3ch

        blended = (
            current.astype(np.float32) * (1 - alpha) +
            warped.astype(np.float32) * alpha
        ).astype(np.uint8)

        return blended

    def smooth_sequence(
        self,
        inpainted_frames: list[Path],
        masks: list[Path],
        output_dir: Path,
        progress_callback=None,
    ) -> list[Path]:
        """
        Apply temporal smoothing across the entire frame sequence.
        
        Uses a sliding window approach:
        - For each frame, blend with flow-warped adjacent frames
        - Only modifies the masked (inpainted) region
        
        Returns:
            List of smoothed frame paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        total = len(inpainted_frames)
        half_window = self.window_size // 2
        output_paths = []

        for i in range(total):
            current = cv2.imread(str(inpainted_frames[i]))
            mask = cv2.imread(str(masks[i]), cv2.IMREAD_GRAYSCALE)

            if current is None or mask is None:
                continue

            # Skip smoothing if mask is empty (no inpainted region)
            if np.sum(mask) == 0:
                out_path = output_dir / f"smoothed_{i:06d}.png"
                cv2.imwrite(str(out_path), current)
                output_paths.append(out_path)
                continue

            result = current.astype(np.float32)
            weight_sum = 1.0

            # Blend with neighboring frames
            for offset in range(-half_window, half_window + 1):
                if offset == 0:
                    continue
                neighbor_idx = i + offset
                if neighbor_idx < 0 or neighbor_idx >= total:
                    continue

                neighbor = cv2.imread(str(inpainted_frames[neighbor_idx]))
                if neighbor is None:
                    continue

                flow = self.compute_flow(neighbor, current)
                warped = self.warp_frame(neighbor, flow)

                # Distance-based weight (closer frames have more influence)
                weight = 1.0 / (abs(offset) + 1)
                mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0

                result += warped.astype(np.float32) * weight * mask_3ch * self.blend_strength
                weight_sum += weight * self.blend_strength

            # Normalize
            mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0
            # Only normalize in masked region
            result_normalized = result / weight_sum
            final = current.astype(np.float32) * (1 - mask_3ch) + result_normalized * mask_3ch
            final = np.clip(final, 0, 255).astype(np.uint8)

            out_path = output_dir / f"smoothed_{i:06d}.png"
            cv2.imwrite(str(out_path), final)
            output_paths.append(out_path)

            if progress_callback and i % 10 == 0:
                progress_callback(i + 1, total)

        logger.info(f"⛏  Temporal smoothing complete: {len(output_paths)} frames")
        return output_paths
