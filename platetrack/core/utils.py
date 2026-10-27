"""Drawing utilities: overlay boxes, text, etc. on video frames (no Qt dependency)."""
from __future__ import annotations

import cv2
import numpy as np

from .detection import PlateResult


def draw_plate_result(
    frame: np.ndarray,
    result: PlateResult,
    *,
    plate_color: tuple[int, int, int] = (0, 255, 0),
    text_color: tuple[int, int, int] = (0, 0, 0),
    thickness: int = 2,
    font_scale: float = 0.6,
) -> np.ndarray:
    """Draw bounding box and plate text on the frame (in-place). Returns the same frame."""
    x1, y1, x2, y2 = result.bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), plate_color, thickness)

    label = f"{result.plate_text} {result.confidence:.2f}"
    (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    cv2.rectangle(
        frame,
        (x1, y1 - th - baseline),
        (x1 + tw, y1),
        plate_color,
        -1,
    )
    cv2.putText(
        frame,
        label,
        (x1, y1 - baseline),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        text_color,
        thickness,
        cv2.LINE_AA,
    )
    return frame


def draw_zone(
    frame: np.ndarray,
    zone_polygon: list[tuple[int, int]],
    *,
    color: tuple[int, int, int] = (0, 165, 255),
    thickness: int = 2,
) -> np.ndarray:
    """Draw the detection zone polygon (closed)."""
    if len(zone_polygon) < 3:
        return frame
    pts = np.array(zone_polygon, dtype=np.int32)
    cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=thickness)
    return frame


def draw_track_id(
    frame: np.ndarray,
    track_id: int,
    bbox: tuple[int, int, int, int],
    *,
    color: tuple[int, int, int] = (255, 0, 0),
    thickness: int = 2,
    font_scale: float = 0.6,
) -> np.ndarray:
    """Draw a track ID label above the bounding box."""
    x1, y1, x2, y2 = bbox
    label = f"ID {track_id}"
    (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    cv2.rectangle(
        frame,
        (x1, y1 - th - baseline),
        (x1 + tw, y1),
        color,
        -1,
    )
    cv2.putText(
        frame,
        label,
        (x1, y1 - baseline),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )
    return frame
