"""Detection pipeline: video source → YOLO vehicles → YOLO plates → OCR.

Designed to run in a background thread and call a callback with PlateResult.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import cv2

# Try to import heavy dependencies; we handle missing gracefully.
try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover - ultralytics may not be installed
    YOLO = None  # type: ignore

try:
    from paddleocr import PaddleOCR  # type: ignore
except Exception:  # pragma: no cover
    PaddleOCR = None  # type: ignore

import numpy as np

from . import plate_parser
from .database import Visit


class DetectionPipeline:
    """
    Parameters
    ----------
    source : str | int
        Video source for cv2.VideoCapture (file path, rtsp/http URL, or cam index).
    plate_model_path : str | None
        Path to a YOLOv8 model fine-tuned for license plates. If None, we skip plate detection
        and assume the vehicle bbox *is* the plate bbox (less accurate).
    vehicle_model_path : str | None
        Path to a YOLOv8 model for vehicle detection. If None, we use yolov8n.pt (COCO pretrained)
        and keep only car, truck, bus, motorbike.
    ocr_lang : str
        Language for PaddleOCR (default 'en').
    min_confidence : float
        Minimum OCR confidence to accept a plate reading.
    callback : Callable[[PlateResult, np.ndarray], None]
        Called for every accepted plate result with the annotated frame (or None if display disabled).
    """

    def __init__(
        self,
        source: str | int,
        *,
        plate_model_path: Optional[str] = None,
        vehicle_model_path: Optional[str] = None,
        ocr_lang: str = "en",
        min_confidence: float = 0.5,
        callback: Optional[Callable[[PlateResult, np.ndarray], None]] = None,
    ) -> None:
        self.source = source
        self.plate_model_path = plate_model_path
        self.vehicle_model_path = vehicle_model_path
        self.ocr_lang = ocr_lang
        self.min_confidence = min_confidence
        self.callback = callback

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None

        # These will be initialised in _load_models()
        self.vehicle_model: Optional[YOLO] = None
        self.plate_model: Optional[YOLO] = None
        self.ocr: Optional[PaddleOCR] = None

        # simple internal counters
        self._frame_id = 0

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="PlateTrack-Detection", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        self._release_capture()
        self._thread = None

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #
    def _load_models(self) -> None:
        """Load YOLO models and OCR; log if any missing."""
        from platetrack.logging_setup import setup_logging

        logger = setup_logging()

        if YOLO is None:
            logger.warning("ultralytics not installed – detection disabled")
            return

        # Vehicle model
        v_path = self.vehicle_model_path or "yolov8n.pt"
        try:
            self.vehicle_model = YOLO(v_path)
            logger.info("Loaded vehicle model: %s", v_path)
        except Exception as e:  # pragma: no cover
            logger.error("Failed to load vehicle model %s: %s", v_path, e)

        # Plate model (optional)
        if self.plate_model_path:
            try:
                self.plate_model = YOLO(self.plate_model_path)
                logger.info("Loaded plate model: %s", self.plate_model_path)
            except Exception as e:  # pragma: no cover
                logger.error("Failed to load plate model %s: %s", self.plate_model_path, e)
                self.plate_model = None

        # OCR
        if PaddleOCR is None:
            logger.warning("PaddleOCR not installed – OCR disabled")
        else:
            try:
                self.ocr = PaddleOCR(use_angle_cls=True, lang=self.ocr_lang, show_log=False)
                logger.info("Initialized PaddleOCR (lang=%s)", self.ocr_lang)
            except Exception as e:  # pragma: no cover
                logger.error("Failed to init PaddleOCR: %s", e)
                self.ocr = None

    def _open_capture(self) -> bool:
        """Try to open the video source; return True on success."""
        self._release_capture()
        try:
            self._cap = cv2.VideoCapture(self.source)
            if not self._cap.isOpened():
                raise IOError(f"Cannot open video source {self.source}")
            return True
        except Exception as e:  # pragma: no cover
            from platetrack.logging_setup import setup_logging

            setup_logging().error("Failed to open video source %s: %s", self.source, e)
            self._cap = None
            return False

    def _release_capture(self) -> None:
        if self._cap and self._cap.isOpened():
            self._cap.release()
        self._cap = None

    def _process_frame(self, frame: np.ndarray) -> list[PlateResult]:
        """Run detection+OCR on a single BGR frame; return list of PlateResult."""
        if self.vehicle_model is None:
            return []

        # Vehicle detection (we only keep a subset of COCO classes)
        vehicle_results = self.vehicle_model(frame, verbose=False)[0]
        plates: list[PlateResult] = []

        for box in vehicle_results.boxes:
            cls = int(box.cls[0])
            # COCO class ids: car=2, motorbike=3, bus=5, truck=7
            if cls not in {2, 3, 5, 7}:
                continue
            conf = float(box.conf[0])
            if conf < 0.25:  # low vehicle confidence -> skip
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            vehicle_bbox = (x1, y1, x2, y2)
            vehicle_crop = frame[y1:y2, x1:x2]

            # Plate detection: if we have a plate model, run it on the vehicle crop;
            # otherwise assume the whole vehicle crop is the plate (fallback).
            if self.plate_model is not None:
                plate_results = self.plate_model(vehicle_crop, verbose=False)[0]
                # Take the highest-confidence plate box
                if len(plate_results.boxes) == 0:
                    continue
                pb = plate_results.boxes[0]  # already sorted by confidence desc by ultralytics
                px1, py1, px2, py2 = map(int, pb.xyxy[0])
                # Convert to frame coordinates
                px1 += x1
                py1 += y1
                px2 += x1
                py2 += y1
                plate_conf = float(pb.conf[0])
                plate_crop = vehicle_crop[py1 - y1:py2 - y1, px1 - x1:px2 - x1]
            else:
                # No plate model: treat the whole vehicle bbox as the plate bbox
                px1, py1, px2, py2 = vehicle_bbox
                plate_conf = conf
                plate_crop = vehicle_crop

            # OCR
            if self.ocr is None:
                continue
            ocr_result = self.ocr.ocr(plate_crop, cls=False)
            if not ocr_result or not ocr_result[0]:
                continue
            # PaddleOCR returns [[[box], (text, confidence)], ...]
            text, conf = ocr_result[0][0][1]  # type: ignore[index]
            if conf < self.min_confidence:
                continue
            plate_norm = plate_parser.normalize(text)
            if not plate_parser.validate(plate_norm):
                continue

            plates.append(
                PlateResult(
                    plate_text=plate_norm,
                    confidence=conf,
                    bbox=(px1, py1, px2, py2),
                    frame_id=self._frame_id,
                    timestamp=time.time(),
                    vehicle_bbox=vehicle_bbox,
                )
            )
        return plates

    def _run(self) -> None:
        """Main thread: grab frames, run detection, callback."""
        logger = None  # initialised lazily to avoid circular import at module level

        if not self._open_capture():
            return

        self._load_models()

        while not self._stop_event.is_set():
            if self._cap is None or not self._cap.isOpened():
                # try to reconnect after a short pause
                time.sleep(1.0)
                if not self._open_capture():
                    continue
                # reload models after reconnect? (not needed)
                continue

            ret, frame = self._cap.read()
            if not ret or frame is None:
                # end of file or read error – try to reconnect
                self._release_capture()
                continue

            self._frame_id += 1
            plates = self._process_frame(frame)

            if self.callback:
                for p in plates:
                    # draw on a copy so the original frame is not mutated for next pipeline steps
                    annotated = frame.copy()
                    draw_plate_result(annotated, p)
                    if p.vehicle_bbox:
                        # optional: draw vehicle box in a different colour
                        cv2.rectangle(
                            annotated,
                            (p.vehicle_bbox[0], p.vehicle_bbox[1]),
                            (p.vehicle_bbox[2], p.vehicle_bbox[3]),
                            (255, 0, 0),
                            1,
                        )
                    self.callback(p, annotated)

        self._release_capture()
