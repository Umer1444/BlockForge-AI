"""
BlockForge AI – Multi-Modal Watermark Detection
Detects watermarks using OCR (text) and Object Detection (logos/objects)
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import cv2
import numpy as np
import torch

from config import settings
from services.gpu_manager import gpu_manager

logger = logging.getLogger("blockforge.detector")


@dataclass
class Detection:
    """Single watermark detection result."""
    bbox: tuple  # (x1, y1, x2, y2)
    mask: np.ndarray  # Binary mask of detected region
    confidence: float  # 0-1 confidence score
    type: str  # 'text', 'logo', 'object'
    text: Optional[str] = None  # Extracted text (if OCR)
    metadata: dict = None  # Extra info


class WatermarkDetector:
    """
    Multi-modal watermark detector combining:
    - PaddleOCR for text watermarks
    - YOLOv8 for logo/object watermarks
    """

    def __init__(self, device: Optional[str] = None, ocr_enabled: bool = True, yolo_enabled: bool = True):
        self.device = device or gpu_manager.current_device
        self.ocr_enabled = ocr_enabled
        self.yolo_enabled = yolo_enabled
        self.ocr_model = None
        self.yolo_model = None
        self._load_models()

    def _load_models(self):
        """Lazily load detection models."""
        if self.ocr_enabled:
            try:
                from paddleocr import PaddleOCR
                logger.info(f"⛏  Loading PaddleOCR on {self.device}")
                use_gpu = self.device.startswith("cuda")
                self.ocr_model = PaddleOCR(
                    use_angle_cls=True,
                    lang='en',
                    use_gpu=use_gpu,
                )
                logger.info("⛏  PaddleOCR loaded successfully")
            except ImportError:
                logger.warning("paddleocr not installed. Text detection disabled.")
                self.ocr_enabled = False

        if self.yolo_enabled:
            try:
                from ultralytics import YOLO
                logger.info(f"⛏  Loading YOLOv8 on {self.device}")
                # Use small model for faster inference
                self.yolo_model = YOLO(
                    settings.YOLOV8_MODEL_PATH or 'yolov8s.pt'
                )
                self.yolo_model.to(self.device)
                logger.info("⛏  YOLOv8 loaded successfully")
            except ImportError:
                logger.warning("ultralytics not installed. Object detection disabled.")
                self.yolo_enabled = False

    def detect_text_watermarks(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.5,
    ) -> list[Detection]:
        """
        Detect text watermarks using OCR.

        Returns:
            List of Detection objects with type='text'
        """
        if not self.ocr_enabled or self.ocr_model is None:
            return []

        try:
            # OCR expects BGR
            if image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image

            results = self.ocr_model.ocr(image_rgb, cls=True)

            detections = []
            for line in results:
                if line is None:
                    continue
                for text_info in line:
                    coords, text, confidence = text_info
                    if confidence < confidence_threshold:
                        continue

                    # Extract bounding box
                    coords = np.array(coords, dtype=np.int32)
                    x1 = max(0, int(coords[:, 0].min()))
                    y1 = max(0, int(coords[:, 1].min()))
                    x2 = min(image.shape[1], int(coords[:, 0].max()))
                    y2 = min(image.shape[0], int(coords[:, 1].max()))

                    # Create binary mask for text region
                    mask = np.zeros(image.shape[:2], dtype=np.uint8)
                    mask[y1:y2, x1:x2] = 255

                    detections.append(
                        Detection(
                            bbox=(x1, y1, x2, y2),
                            mask=mask,
                            confidence=float(confidence),
                            type="text",
                            text=text,
                            metadata={"bbox_points": coords.tolist()},
                        )
                    )

            logger.info(f"⛏  Detected {len(detections)} text watermarks")
            return detections

        except Exception as e:
            logger.error(f"Text detection failed: {e}")
            return []

    def detect_logo_watermarks(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.4,
    ) -> list[Detection]:
        """
        Detect logo/object watermarks using YOLOv8.

        Returns:
            List of Detection objects with type='logo'
        """
        if not self.yolo_enabled or self.yolo_model is None:
            return []

        try:
            # YOLOv8 expects BGR
            results = self.yolo_model.predict(
                image,
                conf=confidence_threshold,
                device=self.device,
                verbose=False,
            )

            detections = []
            for result in results:
                if result.boxes is None or len(result.boxes) == 0:
                    continue

                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    confidence = float(box.conf[0])

                    # Create binary mask for detected region
                    mask = np.zeros(image.shape[:2], dtype=np.uint8)
                    mask[y1:y2, x1:x2] = 255

                    # Get class name
                    class_id = int(box.cls[0]) if box.cls is not None else 0
                    class_name = result.names.get(class_id, f"class_{class_id}")

                    detections.append(
                        Detection(
                            bbox=(x1, y1, x2, y2),
                            mask=mask,
                            confidence=confidence,
                            type="logo",
                            metadata={"class": class_name, "class_id": class_id},
                        )
                    )

            logger.info(f"⛏  Detected {len(detections)} logo/object watermarks")
            return detections

        except Exception as e:
            logger.error(f"Logo detection failed: {e}")
            return []

    def detect_all_watermarks(
        self,
        image: np.ndarray,
        text_confidence: float = 0.5,
        logo_confidence: float = 0.4,
    ) -> list[Detection]:
        """
        Detect all watermarks (text + logo) in an image.

        Returns:
            List of Detection objects sorted by confidence (descending)
        """
        detections = []

        # Text detection
        if self.ocr_enabled:
            detections.extend(
                self.detect_text_watermarks(image, confidence_threshold=text_confidence)
            )

        # Logo/object detection
        if self.yolo_enabled:
            detections.extend(
                self.detect_logo_watermarks(image, confidence_threshold=logo_confidence)
            )

        # Sort by confidence
        detections.sort(key=lambda d: d.confidence, reverse=True)

        logger.info(f"⛏  Total detections: {len(detections)}")
        return detections

    def merge_detections(self, detections: list[Detection], iou_threshold: float = 0.3) -> list[Detection]:
        """
        Merge overlapping detections using NMS (Non-Maximum Suppression).

        Args:
            detections: List of Detection objects
            iou_threshold: IoU threshold for merging

        Returns:
            Merged list of detections
        """
        if len(detections) <= 1:
            return detections

        # Sort by confidence
        detections.sort(key=lambda d: d.confidence, reverse=True)

        merged = []
        used = set()

        for i, det_i in enumerate(detections):
            if i in used:
                continue

            current_mask = det_i.mask.copy()
            current_confidence = det_i.confidence

            # Check overlap with remaining detections
            for j, det_j in enumerate(detections[i + 1 :], start=i + 1):
                if j in used:
                    continue

                # Calculate IoU
                intersection = cv2.bitwise_and(current_mask, det_j.mask)
                union = cv2.bitwise_or(current_mask, det_j.mask)
                intersection_area = cv2.countNonZero(intersection)
                union_area = cv2.countNonZero(union)

                if union_area == 0:
                    continue

                iou = intersection_area / union_area

                if iou > iou_threshold:
                    # Merge masks
                    current_mask = cv2.bitwise_or(current_mask, det_j.mask)
                    # Average confidence
                    current_confidence = (current_confidence + det_j.confidence) / 2
                    used.add(j)

            # Create merged detection
            contours, _ = cv2.findContours(current_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                x1, y1, w, h = cv2.boundingRect(contours[0])
                x2, y2 = x1 + w, y1 + h

                merged.append(
                    Detection(
                        bbox=(x1, y1, x2, y2),
                        mask=current_mask,
                        confidence=current_confidence,
                        type=det_i.type,
                        text=det_i.text,
                        metadata=det_i.metadata,
                    )
                )

        logger.info(f"⛏  After NMS: {len(merged)} merged detections")
        return merged

    def cleanup(self):
        """Clean up GPU memory."""
        if self.yolo_model is not None:
            del self.yolo_model
        if self.ocr_model is not None:
            del self.ocr_model
        gpu_manager.clear_cache()
