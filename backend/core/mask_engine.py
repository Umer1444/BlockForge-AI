"""
BlockForge AI – Mask Engine
SAM-based, manual, and auto-detection mask generation for video inpainting.
Supports: Manual, Auto, and Hybrid modes.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List
from enum import Enum

import cv2
import numpy as np
import torch

from config import settings
from services.gpu_manager import gpu_manager
from core.watermark_detector import WatermarkDetector, Detection
from core.watermark_tracker import WatermarkTracker, FrameInterpolator

logger = logging.getLogger("blockforge.mask_engine")


class MaskMode(Enum):
    """Mask generation modes."""
    MANUAL = "manual"              # User-drawn mask
    AUTO = "auto"                  # AI auto-detection
    HYBRID = "hybrid"              # AI + user refinement
    SAM_POINTS = "sam_points"      # SAM with point prompts


class MaskEngine:
    """Generate masks using SAM, manual input, or AI auto-detection."""

    def __init__(self, device: Optional[str] = None):
        self.device = device or gpu_manager.current_device
        self.sam_model = None
        self.sam_predictor = None
        self.detector = None
        self.tracker = None

    def load_sam(self):
        """Lazily load SAM model onto GPU."""
        if self.sam_model is not None:
            return

        try:
            from segment_anything import sam_model_registry, SamPredictor

            logger.info(f"⛏  Loading SAM ({settings.SAM_MODEL_TYPE}) on {self.device}")
            self.sam_model = sam_model_registry[settings.SAM_MODEL_TYPE](
                checkpoint=settings.SAM_CHECKPOINT
            )
            self.sam_model.to(self.device)
            if settings.USE_FP16:
                self.sam_model.half()
            self.sam_predictor = SamPredictor(self.sam_model)
            logger.info("⛏  SAM loaded successfully")
        except ImportError:
            logger.warning("segment_anything not installed. SAM unavailable.")
            raise RuntimeError("SAM model not available. Install segment-anything.")

    def generate_sam_mask(
        self,
        image: np.ndarray,
        points: list[dict],
        labels: list[int],
    ) -> np.ndarray:
        """
        Generate mask using SAM from point prompts.
        
        Args:
            image: BGR image (H, W, 3)
            points: List of {"x": int, "y": int}
            labels: 1 = foreground, 0 = background
            
        Returns:
            Binary mask (H, W) with 255 for masked regions.
        """
        self.load_sam()

        # SAM expects RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.sam_predictor.set_image(image_rgb)

        point_coords = np.array([[p["x"], p["y"]] for p in points])
        point_labels = np.array(labels)

        masks, scores, _ = self.sam_predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True,
        )

        # Use the mask with highest confidence
        best_idx = np.argmax(scores)
        mask = masks[best_idx].astype(np.uint8) * 255

        logger.info(f"⛏  SAM mask generated (score: {scores[best_idx]:.3f})")
        return mask

    def load_manual_mask(self, mask_path: str) -> np.ndarray:
        """Load a manually drawn mask from a PNG file."""
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise FileNotFoundError(f"Mask not found: {mask_path}")

        # Threshold to binary
        _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        return binary_mask

    def propagate_mask_to_frames(
        self,
        mask: np.ndarray,
        frames: list[Path],
        job_id: str,
    ) -> list[Path]:
        """
        Propagate a single mask to all video frames.
        For static watermarks, the same mask applies to every frame.
        For moving objects, use optical flow tracking (handled separately).
        
        Returns list of mask file paths.
        """
        mask_dir = settings.MASKS_DIR / job_id / "frame_masks"
        mask_dir.mkdir(parents=True, exist_ok=True)

        mask_paths = []
        for i, frame_path in enumerate(frames):
            # For watermarks: static mask across all frames
            # Read frame to ensure mask dimensions match
            frame = cv2.imread(str(frame_path))
            if frame is None:
                continue

            h, w = frame.shape[:2]
            resized_mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)

            # Optional: dilate mask slightly for better inpainting coverage
            kernel = np.ones((5, 5), np.uint8)
            dilated = cv2.dilate(resized_mask, kernel, iterations=2)

            mask_path = mask_dir / f"mask_{i:06d}.png"
            cv2.imwrite(str(mask_path), dilated)
            mask_paths.append(mask_path)

        logger.info(f"⛏  Propagated mask to {len(mask_paths)} frames")
        return mask_paths

    def generate_masks_for_job(self, job_id: str, mask_info: dict, frames: list[Path]) -> list[Path]:
        """
        High-level API: generate individual frame masks based on mask_info type.
        """
        if mask_info["type"] == "manual":
            base_mask = self.load_manual_mask(mask_info["path"])
            return self.propagate_mask_to_frames(base_mask, frames, job_id)
        
        elif mask_info["type"] == "sam":
            with open(mask_info["path"]) as f:
                sam_data = json.load(f)
            # Use first frame for SAM mask generation
            first_frame = cv2.imread(str(frames[0]))
            base_mask = self.generate_sam_mask(
                first_frame,
                sam_data["points"],
                sam_data["labels"],
            )
            return self.propagate_mask_to_frames(base_mask, frames, job_id)
        
        elif mask_info["type"] == "auto":
            return self.generate_masks_auto_detect(job_id, frames, mask_info)
        
        elif mask_info["type"] == "hybrid":
            return self.generate_masks_hybrid(job_id, frames, mask_info)
        
        else:
            raise ValueError(f"Unknown mask type: {mask_info['type']}")

    def generate_masks_auto_detect(
        self,
        job_id: str,
        frames: list[Path],
        mask_info: dict,
    ) -> list[Path]:
        """
        Auto-detect watermarks using OCR and object detection.
        
        Args:
            job_id: Job ID
            frames: List of frame paths
            mask_info: Contains confidence thresholds
        
        Returns:
            List of mask file paths
        """
        logger.info("⛏  Starting auto-detection mode")
        
        # Initialize detector and tracker
        self.detector = WatermarkDetector(device=self.device)
        self.tracker = WatermarkTracker()
        
        text_confidence = mask_info.get("text_confidence", 0.5)
        logo_confidence = mask_info.get("logo_confidence", 0.4)
        
        mask_dir = settings.MASKS_DIR / job_id / "frame_masks"
        mask_dir.mkdir(parents=True, exist_ok=True)
        
        mask_paths = []
        prev_frame = None
        
        try:
            for frame_idx, frame_path in enumerate(frames):
                frame = cv2.imread(str(frame_path))
                if frame is None:
                    continue
                
                # Detect watermarks
                detections = self.detector.detect_all_watermarks(
                    frame,
                    text_confidence=text_confidence,
                    logo_confidence=logo_confidence,
                )
                
                # Track detections across frames
                tracked_detections = self.tracker.update(
                    frame_idx,
                    detections,
                    prev_frame=prev_frame,
                    curr_frame=frame,
                )
                
                # Merge overlapping detections
                merged_detections = self.detector.merge_detections(tracked_detections)
                
                # Create combined mask from all detections
                mask = self._create_mask_from_detections(frame, merged_detections)
                
                # Dilate mask for better inpainting coverage
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.dilate(mask, kernel, iterations=2)
                
                # Save mask
                mask_path = mask_dir / f"mask_{frame_idx:06d}.png"
                cv2.imwrite(str(mask_path), mask)
                mask_paths.append(mask_path)
                
                # Store detections metadata
                detections_file = mask_dir / f"detections_{frame_idx:06d}.json"
                detections_data = [
                    {
                        "type": d.type,
                        "bbox": d.bbox,
                        "confidence": d.confidence,
                        "text": d.text,
                        "metadata": d.metadata,
                    }
                    for d in merged_detections
                ]
                with open(detections_file, "w") as f:
                    json.dump(detections_data, f)
                
                prev_frame = frame
                
                if (frame_idx + 1) % 10 == 0:
                    logger.debug(f"⛏  Auto-detected {len(merged_detections)} watermarks in frame {frame_idx + 1}/{len(frames)}")
        
        finally:
            if self.detector:
                self.detector.cleanup()
        
        logger.info(f"⛏  Auto-detection complete: {len(mask_paths)} masks")
        return mask_paths

    def generate_masks_hybrid(
        self,
        job_id: str,
        frames: list[Path],
        mask_info: dict,
    ) -> list[Path]:
        """
        Hybrid mode: AI detects watermarks, user can refine/adjust.
        
        Args:
            job_id: Job ID
            frames: List of frame paths
            mask_info: Contains auto_detections (from AI) and refinements (from user)
        
        Returns:
            List of mask file paths
        """
        logger.info("⛏  Starting hybrid detection mode")
        
        # First do auto-detection
        auto_masks = self.generate_masks_auto_detect(job_id, frames, mask_info)
        
        # Check if user provided refinements
        refinements = mask_info.get("refinements", {})
        
        if not refinements:
            # No refinements, use auto-detected masks
            return auto_masks
        
        # Apply user refinements
        mask_dir = settings.MASKS_DIR / job_id / "frame_masks"
        
        for frame_idx_str, refinement in refinements.items():
            frame_idx = int(frame_idx_str)
            mask_path = mask_dir / f"mask_{frame_idx:06d}.png"
            
            if not mask_path.exists():
                continue
            
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            
            # Apply user adjustments
            if refinement.get("mode") == "add":
                # Add new mask region (user added watermark area)
                user_mask = cv2.imread(refinement["mask_path"], cv2.IMREAD_GRAYSCALE)
                mask = cv2.bitwise_or(mask, user_mask)
            
            elif refinement.get("mode") == "remove":
                # Remove mask region (user removed false positive)
                user_mask = cv2.imread(refinement["mask_path"], cv2.IMREAD_GRAYSCALE)
                mask = cv2.bitwise_and(mask, cv2.bitwise_not(user_mask))
            
            elif refinement.get("mode") == "replace":
                # Replace entire mask
                mask = cv2.imread(refinement["mask_path"], cv2.IMREAD_GRAYSCALE)
            
            cv2.imwrite(str(mask_path), mask)
        
        logger.info(f"⛏  Applied {len(refinements)} user refinements")
        return auto_masks

    def _create_mask_from_detections(
        self,
        frame: np.ndarray,
        detections: List[Detection],
    ) -> np.ndarray:
        """
        Create a single binary mask from multiple detections.
        
        Args:
            frame: Input frame for mask dimensions
            detections: List of Detection objects
        
        Returns:
            Binary mask combining all detections
        """
        h, w = frame.shape[:2]
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        
        for detection in detections:
            # Use the detection mask directly
            combined_mask = cv2.bitwise_or(combined_mask, detection.mask)
        
        return combined_mask

    def cleanup(self):
        """Release GPU memory."""
        if self.sam_model is not None:
            del self.sam_model
            del self.sam_predictor
            self.sam_model = None
            self.sam_predictor = None
            torch.cuda.empty_cache()
            logger.info("⛏  SAM model unloaded, GPU memory freed")
