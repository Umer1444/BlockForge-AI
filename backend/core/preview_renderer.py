"""
BlockForge AI – Preview Renderer
Generates before/after preview images with watermark highlighting.
"""

import logging
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np

logger = logging.getLogger("blockforge.preview")


class PreviewRenderer:
    """
    Render preview images:
    - Before/after comparison (side-by-side)
    - Watermark highlight overlay
    - Confidence visualization
    """

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height

    def _resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Resize frame to preview dimensions, maintaining aspect ratio."""
        h, w = frame.shape[:2]
        aspect = w / h

        if aspect > self.width / self.height:
            # Width limited
            new_w = self.width
            new_h = int(self.width / aspect)
        else:
            # Height limited
            new_h = self.height
            new_w = int(self.height * aspect)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        # Pad to exact size
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        y_offset = (self.height - new_h) // 2
        x_offset = (self.width - new_w) // 2
        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return canvas

    def render_before_after(
        self,
        before_frame: np.ndarray,
        after_frame: np.ndarray,
        title: str = "Before / After",
    ) -> np.ndarray:
        """
        Render side-by-side before/after comparison.

        Args:
            before_frame: Original frame
            after_frame: Processed frame
            title: Title for the preview

        Returns:
            Composite image
        """
        h = self.height
        w = self.width // 2

        before = cv2.resize(before_frame, (w, h), interpolation=cv2.INTER_LANCZOS4)
        after = cv2.resize(after_frame, (w, h), interpolation=cv2.INTER_LANCZOS4)

        # Create composite
        composite = np.hstack([before, after])

        # Add separator line
        cv2.line(composite, (w, 0), (w, h), (0, 255, 255), 3)

        # Add labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            composite, "BEFORE",
            (int(w * 0.1), 40),
            font, 1.2, (255, 255, 255), 2,
        )
        cv2.putText(
            composite, "AFTER",
            (int(w * 1.1), 40),
            font, 1.2, (255, 255, 255), 2,
        )

        # Add title
        cv2.putText(
            composite, title,
            (20, self.height - 20),
            font, 0.8, (0, 255, 0), 2,
        )

        return composite

    def render_watermark_highlight(
        self,
        frame: np.ndarray,
        detections: List,
        opacity: float = 0.3,
    ) -> np.ndarray:
        """
        Render frame with watermark regions highlighted.

        Args:
            frame: Input frame
            detections: List of Detection objects
            opacity: Overlay opacity (0-1)

        Returns:
            Frame with highlighted watermarks
        """
        highlighted = frame.copy().astype(np.float32)
        overlay = frame.copy().astype(np.float32)

        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            color_intensity = int(detection.confidence * 255)

            # Color based on type
            if detection.type == "text":
                color = (0, 255, 0)  # Green for text
            elif detection.type == "logo":
                color = (255, 0, 0)  # Red for logos
            else:
                color = (255, 255, 0)  # Yellow for unknown

            # Fill region
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)

            # Draw border with confidence indicator
            thickness = max(2, int(detection.confidence * 5))
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness)

            # Add confidence label
            confidence_text = f"{detection.confidence:.0%}"
            cv2.putText(
                overlay,
                confidence_text,
                (x1, max(y1 - 5, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
            )

        # Blend overlay
        highlighted = (
            highlighted * (1 - opacity) +
            overlay * opacity
        ).astype(np.uint8)

        return highlighted

    def render_detection_grid(
        self,
        frame: np.ndarray,
        detections: List,
        grid_size: int = 50,
    ) -> np.ndarray:
        """
        Render detection heatmap on a grid.

        Args:
            frame: Input frame
            detections: List of Detection objects
            grid_size: Size of grid cells in pixels

        Returns:
            Frame with heatmap overlay
        """
        h, w = frame.shape[:2]
        heatmap = np.zeros((h, w), dtype=np.float32)

        # Fill heatmap with detection masks
        for detection in detections:
            mask = detection.mask.astype(np.float32) / 255.0
            heatmap = np.maximum(heatmap, mask * detection.confidence)

        # Convert to BGR image
        heatmap_color = cv2.applyColorMap(
            (heatmap * 255).astype(np.uint8),
            cv2.COLORMAP_JET,
        )

        # Blend with original
        result = cv2.addWeighted(frame, 0.7, heatmap_color, 0.3, 0)

        return result

    def save_preview(
        self,
        preview_image: np.ndarray,
        output_path: Path,
        quality: int = 90,
    ):
        """Save preview image as PNG or JPEG."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix.lower() in [".jpg", ".jpeg"]:
            cv2.imwrite(str(output_path), preview_image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        else:
            cv2.imwrite(str(output_path), preview_image)

        logger.info(f"⛏  Preview saved: {output_path}")

    def create_detection_report_image(
        self,
        frame: np.ndarray,
        detections: List,
        output_path: Path,
    ):
        """
        Create a detailed detection report image.

        Args:
            frame: Original frame
            detections: List of detections
            output_path: Where to save the report
        """
        h, w = frame.shape[:2]
        
        # Create a larger canvas
        report_height = h + 200
        report = np.zeros((report_height, w, 3), dtype=np.uint8)
        report[:h, :] = frame

        # Add detection details
        y = h + 20
        x = 20
        font = cv2.FONT_HERSHEY_SIMPLEX
        line_height = 30

        cv2.putText(
            report,
            f"WATERMARK DETECTION REPORT",
            (x, y),
            font, 0.8, (0, 255, 0), 2,
        )
        y += line_height

        cv2.putText(
            report,
            f"Total Detections: {len(detections)}",
            (x, y),
            font, 0.6, (255, 255, 255), 1,
        )
        y += line_height

        # Summary by type
        text_count = sum(1 for d in detections if d.type == "text")
        logo_count = sum(1 for d in detections if d.type == "logo")

        cv2.putText(
            report,
            f"Text: {text_count} | Logo: {logo_count}",
            (x, y),
            font, 0.6, (255, 255, 255), 1,
        )

        self.save_preview(report, output_path)
