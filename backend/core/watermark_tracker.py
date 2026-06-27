"""
BlockForge AI – Watermark Frame Tracker
Tracks watermark locations across frames to avoid per-frame detection.
Uses optical flow and feature matching for temporal consistency.
"""

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("blockforge.tracker")


class WatermarkTracker:
    """
    Track detected watermarks across frames using:
    - Optical flow
    - Feature matching
    - Kalman filtering (simple motion prediction)
    """

    def __init__(self, max_gap: int = 5, confidence_decay: float = 0.95):
        """
        Args:
            max_gap: Maximum frames to interpolate between detections
            confidence_decay: How much confidence decreases per frame without detection
        """
        self.max_gap = max_gap
        self.confidence_decay = confidence_decay
        self.tracks = {}  # {track_id: {...}}
        self.next_track_id = 0
        self.orb = cv2.ORB_create(nfeatures=500)

    def _extract_features(self, image: np.ndarray, mask: Optional[np.ndarray] = None):
        """Extract ORB features from region."""
        if mask is not None:
            image_masked = cv2.bitwise_and(image, image, mask=mask)
        else:
            image_masked = image

        gray = cv2.cvtColor(image_masked, cv2.COLOR_BGR2GRAY)
        kp, des = self.orb.detectAndCompute(gray, mask)
        return kp, des

    def _compute_optical_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray, bbox: tuple):
        """Estimate bbox movement using optical flow."""
        x1, y1, x2, y2 = bbox
        roi_prev = prev_frame[y1:y2, x1:x2]
        roi_curr = curr_frame[y1:y2, x1:x2]

        flow = cv2.calcOpticalFlowFarneback(
            cv2.cvtColor(roi_prev, cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(roi_curr, cv2.COLOR_BGR2GRAY),
            None, 0.5, 3, 15, 3, 5, 1.2, 0,
        )

        # Average flow vector
        avg_flow = flow.mean(axis=(0, 1))
        return avg_flow

    def predict_bbox(self, track: dict, frame_gap: int) -> tuple:
        """Predict bounding box position for future frames."""
        if "velocity" not in track or frame_gap == 0:
            return track["bbox"]

        vx, vy = track["velocity"]
        x1, y1, x2, y2 = track["bbox"]

        # Linear prediction
        new_x1 = int(x1 + vx * frame_gap)
        new_y1 = int(y1 + vy * frame_gap)
        new_x2 = int(x2 + vx * frame_gap)
        new_y2 = int(y2 + vy * frame_gap)

        return (new_x1, new_y1, new_x2, new_y2)

    def _compute_iou(self, bbox1: tuple, bbox2: tuple) -> float:
        """Compute IoU between two bounding boxes."""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2

        xi_min = max(x1_min, x2_min)
        yi_min = max(y1_min, y2_min)
        xi_max = min(x1_max, x2_max)
        yi_max = min(y1_max, y2_max)

        if xi_max < xi_min or yi_max < yi_min:
            return 0.0

        intersection = (xi_max - xi_min) * (yi_max - yi_min)
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def update(
        self,
        frame_index: int,
        detections: list,
        prev_frame: Optional[np.ndarray] = None,
        curr_frame: Optional[np.ndarray] = None,
    ) -> list:
        """
        Update tracks with new detections.

        Args:
            frame_index: Current frame number
            detections: List of Detection objects from detector
            prev_frame: Previous frame (for optical flow)
            curr_frame: Current frame (for feature matching)

        Returns:
            List of tracked detections with track_id and age
        """
        # Predict positions for existing tracks
        predictions = {}
        for track_id, track in self.tracks.items():
            frame_gap = frame_index - track["last_seen"]

            if frame_gap > self.max_gap:
                # Track too old, remove
                del self.tracks[track_id]
                continue

            if frame_gap > 0 and prev_frame is not None and curr_frame is not None:
                # Predict position using optical flow
                predicted_bbox = self.predict_bbox(track, frame_gap)
                predictions[track_id] = predicted_bbox
            else:
                predictions[track_id] = track["bbox"]

        # Match detections to predictions (Hungarian algorithm simplified with greedy matching)
        matched_tracks = {}
        unmatched_detections = list(range(len(detections)))
        iou_threshold = 0.3

        for track_id, predicted_bbox in predictions.items():
            best_det_idx = -1
            best_iou = iou_threshold

            for det_idx, detection in enumerate(detections):
                if det_idx not in unmatched_detections:
                    continue

                iou = self._compute_iou(predicted_bbox, detection.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_det_idx = det_idx

            if best_det_idx >= 0:
                det = detections[best_det_idx]
                self.tracks[track_id]["bbox"] = det.bbox
                self.tracks[track_id]["mask"] = det.mask
                self.tracks[track_id]["last_seen"] = frame_index
                self.tracks[track_id]["age"] += 1
                self.tracks[track_id]["confidence"] = det.confidence

                # Update velocity
                if "prev_bbox" in self.tracks[track_id]:
                    prev_x1, prev_y1, _, _ = self.tracks[track_id]["prev_bbox"]
                    curr_x1, curr_y1, _, _ = det.bbox
                    vx = (curr_x1 - prev_x1) / max(1, frame_gap)
                    vy = (curr_y1 - prev_y1) / max(1, frame_gap)
                    self.tracks[track_id]["velocity"] = (vx, vy)

                self.tracks[track_id]["prev_bbox"] = det.bbox
                matched_tracks[track_id] = det

                unmatched_detections.remove(best_det_idx)

        # Create new tracks for unmatched detections
        for det_idx in unmatched_detections:
            det = detections[det_idx]
            track_id = self.next_track_id
            self.next_track_id += 1

            self.tracks[track_id] = {
                "bbox": det.bbox,
                "mask": det.mask,
                "first_seen": frame_index,
                "last_seen": frame_index,
                "age": 1,
                "confidence": det.confidence,
                "type": det.type,
                "text": det.text,
                "velocity": (0, 0),
            }
            matched_tracks[track_id] = det

        # Build output with track IDs
        output_detections = []
        for track_id, track in self.tracks.items():
            if track["last_seen"] == frame_index:
                # Decay confidence for old tracks
                confidence = track["confidence"] * (self.confidence_decay ** (frame_index - track["first_seen"]))
                det = detections[[d.bbox for d in detections].index(track["bbox"])]
                det.metadata["track_id"] = track_id
                det.metadata["age"] = track["age"]
                det.confidence = confidence
                output_detections.append(det)

        return output_detections

    def get_active_tracks(self, frame_index: int) -> dict:
        """Get all active tracks at current frame."""
        active = {}
        for track_id, track in self.tracks.items():
            if frame_index - track["last_seen"] <= self.max_gap:
                active[track_id] = track
        return active

    def reset(self):
        """Reset tracker state."""
        self.tracks.clear()
        self.next_track_id = 0


class FrameInterpolator:
    """Interpolate watermark masks between detected frames."""

    @staticmethod
    def interpolate_masks(
        masks: dict,  # {frame_index: mask}
        total_frames: int,
    ) -> dict:  # {frame_index: interpolated_mask}
        """
        Interpolate masks between detected frames using morphological operations.

        Args:
            masks: Dictionary of {frame_index: binary_mask}
            total_frames: Total frames in video

        Returns:
            Dictionary of interpolated masks for all frames
        """
        interpolated = {}

        frame_indices = sorted(masks.keys())
        if not frame_indices:
            return {}

        for i in range(total_frames):
            # Find nearest detected frames
            prev_idx = max([f for f in frame_indices if f <= i], default=frame_indices[0])
            next_idx = min([f for f in frame_indices if f >= i], default=frame_indices[-1])

            if prev_idx == next_idx:
                interpolated[i] = masks[prev_idx].copy()
            else:
                # Linear interpolation between frames
                alpha = (i - prev_idx) / (next_idx - prev_idx)
                mask1 = masks[prev_idx].astype(np.float32) / 255.0
                mask2 = masks[next_idx].astype(np.float32) / 255.0
                blended = (mask1 * (1 - alpha) + mask2 * alpha) * 255
                interpolated[i] = blended.astype(np.uint8)

        return interpolated
