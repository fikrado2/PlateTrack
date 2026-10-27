"""Simple data class for a detected license plate in a single frame."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class PlateResult:
    plate_text: str          # raw string from OCR (already normalised)
    confidence: float        # OCR confidence (0-1)
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2) in pixels
    frame_id: int            # increasing id per video frame
    timestamp: float         # seconds since epoch (monotonic)
    vehicle_bbox: Optional[tuple[int, int, int, int]] = None  # (x1,y1,x2,y2) of the whole vehicle
