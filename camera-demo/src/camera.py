"""Camera / video source with downscaling, frame skipping and latest-frame-only
semantics.

The capture thread is the only writer.  Consumers request the newest published
frame by sequence number and never block the producer.  Larger sources are
downscaled to the profile's capture size, and frames are skipped so only the
requested capture FPS reaches the pipeline.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np

log = logging.getLogger(__name__)

Source = Union[int, str]


def fit_within(src_w: int, src_h: int, max_w: int, max_h: int) -> Tuple[int, int]:
    """Fit a source size inside a box without changing its aspect ratio."""
    src_w = max(1, int(src_w or 0))
    src_h = max(1, int(src_h or 0))
    max_w = max(1, int(max_w or 0))
    max_h = max(1, int(max_h or 0))

    if src_w <= max_w and src_h <= max_h:
        return src_w, src_h

    scale = min(max_w / src_w, max_h / src_h)
    return max(1, int(round(src_w * scale))), max(1, int(round(src_h * scale)))


class CameraSource:
    def __init__(
        self,
        source: Source = 0,
        width: int = 640,
        height: int = 360,
        fps: float = 15.0,
        request_width: Optional[int] = None,
        request_height: Optional[int] = None,
        request_fps: Optional[float] = None,
        pace_video: bool = True,
        record_path: Optional[str] = None,
        start: float = 0.0,
        loop: bool = True,
    ):
        if isinstance(source, Path):
            source = str(source)
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        self.source = source
        self.is_file = isinstance(source, str)
        self.record_path = record_path
        self.start_s = max(0.0, float(start or 0.0)) if self.is_file else 0.0
        self.loop = bool(loop)
        self.finished = threading.Event()

        req_w = int(request_width or width)
        req_h = int(request_height or height)
        req_fps = float(request_fps or fps)

        backend = cv2.CAP_DSHOW if (os.name == "nt" and not self.is_file) else 0
        self.cap = cv2.VideoCapture(source, backend) if backend else cv2.VideoCapture(source)
        if not self.cap.isOpened() and backend:
            self.cap.release()
            self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera/video source: {source!r}")

        if not self.is_file:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, req_w)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, req_h)
            self.cap.set(cv2.CAP_PROP_FPS, req_fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        elif self.start_s > 0:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, self.start_s * 1000.0)
            log.info("Seeking video to %.1fs", self.start_s)

        self.source_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or req_w)
        self.source_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or req_h)
        measured_fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.source_fps = measured_fps if measured_fps > 1.0 else req_fps

        # Published capture size: never upscale, fit inside the requested box.
        self.width, self.height = fit_within(
            self.source_width,
            self.source_height,
            width,
            height,
        )

        target_fps = float(fps or 0.0)
        if target_fps <= 0:
            target_fps = self.source_fps
        self.capture_fps = min(target_fps, self.source_fps) if self.source_fps > 0 else target_fps
        self.capture_fps = max(1.0, self.capture_fps)
        self.fps = self.capture_fps
        self.skip = max(1, int(round(self.source_fps / self.capture_fps)))
        self.pace_video = bool(pace_video)

        self.frames_read = 0
        self.frames_captured = 0
        self.read_failures = 0

        self._frame: Optional[np.ndarray] = None
        self._ts = 0.0
        self._seq = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="camera", daemon=True)

        self._writer: Optional[cv2.VideoWriter] = None
        if record_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._writer = cv2.VideoWriter(
                record_path,
                fourcc,
                self.capture_fps,
                (self.width, self.height),
            )
            if not self._writer.isOpened():
                log.warning("Could not open recorder %s", record_path)
                self._writer = None

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def start(self) -> "CameraSource":
        log.info(
            "Camera source=%r source=%dx%d@%.2f -> capture=%dx%d@%.2f "
            "skip=%d%s%s",
            self.source,
            self.source_width,
            self.source_height,
            self.source_fps,
            self.width,
            self.height,
            self.capture_fps,
            self.skip,
            " (file)" if self.is_file else "",
            (
                f" start={self.start_s:.1f}s loop={self.loop}"
                if self.is_file
                else ""
            ),
        )
        self._thread.start()
        return self

    def close(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self.cap.release()
        if self._writer is not None:
            self._writer.release()
            self._writer = None

    # ------------------------------------------------------------------
    # consumer API
    # ------------------------------------------------------------------

    def latest(self, last_seq: int = -1) -> Optional[Tuple[np.ndarray, float, int]]:
        """Return ``(frame, monotonic_timestamp, seq)`` if newer than last_seq."""
        with self._lock:
            if self._frame is None or self._seq == last_seq:
                return None
            return self._frame, self._ts, self._seq

    # ------------------------------------------------------------------
    # producer
    # ------------------------------------------------------------------

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        if frame.shape[1] == self.width and frame.shape[0] == self.height:
            return frame
        return cv2.resize(
            frame,
            (self.width, self.height),
            interpolation=cv2.INTER_AREA,
        )

    def _loop(self) -> None:
        source_period = 1.0 / max(self.source_fps, 1.0)
        publish_period = 1.0 / max(self.capture_fps, 1.0)
        next_deadline = time.perf_counter()
        next_publish = 0.0

        while not self._stop.is_set():
            ok, frame = self.cap.read()

            if not ok:
                if self.is_file:
                    if self.loop:
                        self.cap.set(
                            cv2.CAP_PROP_POS_MSEC, self.start_s * 1000.0
                        )
                        next_deadline = time.perf_counter()
                        next_publish = 0.0
                        continue
                    log.info(
                        "Video source finished after %.1fs",
                        self.frames_read / max(self.source_fps, 1.0),
                    )
                    self.finished.set()
                    break
                self.read_failures += 1
                self._stop.wait(0.05)
                continue

            self.frames_read += 1
            now = time.monotonic()

            # Fixed schedule with a small tolerance so 30 FPS source frames
            # land on the 15 FPS publish slots instead of drifting to 10 FPS.
            if now + 0.005 >= next_publish:
                frame = self._resize(frame)
                with self._lock:
                    self._frame = frame
                    self._ts = now
                    self._seq += 1
                self.frames_captured += 1
                next_publish += publish_period
                if next_publish <= now:
                    next_publish = now + publish_period
                if self._writer is not None:
                    self._writer.write(frame)

            if self.pace_video:
                next_deadline += source_period
                delay = next_deadline - time.perf_counter()
                if delay > 0:
                    self._stop.wait(delay)
                else:
                    # We are behind; do not try to catch up with a burst.
                    next_deadline = time.perf_counter()

        if self._writer is not None:
            self._writer.release()
            self._writer = None
