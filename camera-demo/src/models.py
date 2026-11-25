"""Model loading and per-stage inference helpers."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
from ultralytics import YOLO

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]

OBSTACLE_CLASSES = {
    "person",
    "bicycle",
    "motorcycle",
    "car",
    "bus",
    "truck",
    "stop sign",
    "bench",
    "chair",
    "suitcase",
    "backpack",
    "handbag",
    "skateboard",
}


def resolve_model_path(path: str) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return str(p)


def class_name(model: YOLO, class_id: int) -> str:
    names = model.names
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    return str(names[class_id])


def load_models(profile, metrics=None):
    """Load and warm up both models.  Returns (detector, segmenter, info)."""
    det_path = resolve_model_path(profile.det_model)
    seg_path = resolve_model_path(profile.seg_model)

    t0 = time.perf_counter()
    detector = YOLO(det_path)
    det_load_ms = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    segmenter = YOLO(seg_path)
    seg_load_ms = (time.perf_counter() - t0) * 1000.0

    # Warm up kernels and allocators before the timed loop starts.
    blank = np.zeros((profile.camera_height, profile.camera_width, 3), dtype=np.uint8)

    t0 = time.perf_counter()
    detector.predict(blank, imgsz=profile.det_size, verbose=False)
    det_warm_ms = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    segmenter.predict(blank, imgsz=profile.seg_size, verbose=False)
    seg_warm_ms = (time.perf_counter() - t0) * 1000.0

    info = {
        "det_model": det_path,
        "seg_model": seg_path,
        "det_load_ms": det_load_ms,
        "seg_load_ms": seg_load_ms,
        "det_warmup_ms": det_warm_ms,
        "seg_warmup_ms": seg_warm_ms,
    }

    if metrics is not None:
        for key, value in info.items():
            if key.endswith("_ms"):
                metrics.gauge(key, value)

    log.info(
        "Models loaded: det %.0f ms (warm %.0f ms), seg %.0f ms (warm %.0f ms)",
        det_load_ms,
        det_warm_ms,
        seg_load_ms,
        seg_warm_ms,
    )
    return detector, segmenter, info


def process_detection(detector: YOLO, frame, profile, slowdown, metrics):
    """Run detection + tracking on one frame."""
    t0 = time.perf_counter()
    results = detector.track(
        frame,
        persist=True,
        tracker=profile.tracker,
        imgsz=profile.det_size,
        conf=profile.confidence,
        verbose=False,
    )
    compute_s = time.perf_counter() - t0
    sim_s = slowdown.inflate(compute_s)

    metrics.record("detect_compute_ms", compute_s * 1000.0)
    metrics.record("detect_sim_ms", sim_s * 1000.0)

    detections = []
    if not results:
        return detections

    result = results[0]
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return detections

    xyxy = boxes.xyxy.cpu().numpy()
    classes = boxes.cls.cpu().numpy().astype(int)
    confidences = boxes.conf.cpu().numpy()
    track_ids = (
        boxes.id.cpu().numpy().astype(int)
        if boxes.id is not None
        else None
    )

    for i in range(len(classes)):
        name = class_name(detector, int(classes[i]))
        detections.append(
            {
                "name": name,
                "confidence": float(confidences[i]),
                "box": xyxy[i],
                "track_id": (
                    int(track_ids[i]) if track_ids is not None else None
                ),
                "obstacle": name in OBSTACLE_CLASSES,
            }
        )

    return detections


def process_segmentation(segmenter: YOLO, frame, profile, slowdown, metrics) -> Optional[np.ndarray]:
    """Run semantic segmentation and return a uint8 class map."""
    t0 = time.perf_counter()
    results = segmenter.predict(
        frame,
        imgsz=profile.seg_size,
        verbose=False,
    )
    compute_s = time.perf_counter() - t0
    sim_s = slowdown.inflate(compute_s)

    metrics.record("seg_compute_ms", compute_s * 1000.0)
    metrics.record("seg_sim_ms", sim_s * 1000.0)

    if not results:
        return None

    semantic_mask = getattr(results[0], "semantic_mask", None)
    if semantic_mask is None:
        return None

    mask = semantic_mask.data.cpu().numpy()
    return mask.astype(np.uint8)
