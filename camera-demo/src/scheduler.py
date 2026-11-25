"""Detection-first inference scheduler.

Both models run in one thread.  On a phone they compete for the same
CPU/GPU/NPU, so serialising them keeps the benchmark honest.  Detection has
priority; segmentation runs only when it is due and there is enough slack
before the next detection, or immediately after a detection finishes.

Detection is the safety-critical path.  If segmentation cannot fit, it is
skipped rather than allowed to queue.
"""

from __future__ import annotations

import logging
import threading
import time

from .models import process_detection, process_segmentation

log = logging.getLogger(__name__)


class Scheduler(threading.Thread):
    def __init__(self, profile, camera, detector, segmenter, alerts, metrics, slowdown, stop_event):
        super().__init__(name="inference", daemon=True)
        self.profile = profile
        self.camera = camera
        self.detector = detector
        self.segmenter = segmenter
        self.alerts = alerts
        self.metrics = metrics
        self.slowdown = slowdown
        self.stop_event = stop_event

        self.det_enabled = profile.det_fps > 0
        self.seg_enabled = profile.seg_fps > 0
        self.det_interval = 1.0 / profile.det_fps if self.det_enabled else float("inf")
        self.seg_interval = 1.0 / profile.seg_fps if self.seg_enabled else float("inf")

        self._seg_estimate = 0.30
        self._seg_waiting = False
        self._latest_detections = []
        self._latest_mask = None
        self._latest_frame = None
        self._pub_lock = threading.Lock()

    # ------------------------------------------------------------------
    # public state for the render loop
    # ------------------------------------------------------------------

    def snapshot(self):
        with self._pub_lock:
            return (
                self._latest_frame,
                list(self._latest_detections),
                self._latest_mask,
            )

    # ------------------------------------------------------------------
    # thread body
    # ------------------------------------------------------------------

    def run(self) -> None:
        last_seq = -1
        last_det_start = None
        next_det = time.monotonic()
        next_seg = time.monotonic() + min(self.seg_interval, 1.0)

        log.info(
            "Scheduler: det %.1f FPS @ %dpx, seg %.1f FPS @ %dpx",
            self.profile.det_fps,
            self.profile.det_size,
            self.profile.seg_fps,
            self.profile.seg_size,
        )

        while not self.stop_event.is_set():
            now = time.monotonic()

            # ----------------------------------------------------------
            # Detection has priority
            # ----------------------------------------------------------
            if self.det_enabled and now >= next_det:
                latest = self.camera.latest(last_seq)
                if latest is None:
                    self.stop_event.wait(0.003)
                    continue

                frame, frame_ts, seq = latest
                last_seq = seq

                if now - next_det > 0.5 * self.det_interval:
                    self.metrics.incr("detection_slots_missed")

                if last_det_start is not None:
                    self.metrics.record(
                        "detect_interval_ms", (now - last_det_start) * 1000.0
                    )
                last_det_start = now
                self.metrics.record("frame_age_ms", (now - frame_ts) * 1000.0)

                detections = process_detection(
                    self.detector,
                    frame,
                    self.profile,
                    self.slowdown,
                    self.metrics,
                )
                self.metrics.incr("detections_run")

                t_alert = time.monotonic()
                self.alerts.generate(
                    detections,
                    width=frame.shape[1],
                    height=frame.shape[0],
                    frame_ts=frame_ts,
                )
                self.metrics.record("alert_ms", (time.monotonic() - t_alert) * 1000.0)

                with self._pub_lock:
                    self._latest_frame = frame
                    self._latest_detections = detections

                next_det = now + self.det_interval
                if next_det <= time.monotonic():
                    # Skip the missed slot instead of bursting to catch up.
                    next_det = time.monotonic() + self.det_interval

                # If segmentation is due (or was waiting for a gap), run it
                # now.  The next detection may be delayed; that cost is
                # recorded by the benchmark.
                if (
                    self.seg_enabled
                    and (self._seg_waiting or time.monotonic() >= next_seg)
                ):
                    seg_start = time.monotonic()
                    self._run_segmentation(frame, frame_ts)
                    self._seg_waiting = False
                    next_seg = seg_start + self.seg_interval
                    if next_seg <= time.monotonic():
                        next_seg = time.monotonic() + self.seg_interval

                continue

            # ----------------------------------------------------------
            # Segmentation in the slack before the next detection
            # ----------------------------------------------------------
            if self.seg_enabled and (
                (not self._seg_waiting) or (not self.det_enabled)
            ) and now >= next_seg:
                slack = next_det - now
                if (not self.det_enabled) or slack >= self._seg_estimate:
                    latest = self.camera.latest(last_seq)
                    if latest is None:
                        self.stop_event.wait(0.003)
                        continue
                    frame, seg_frame_ts, seq = latest
                    last_seq = seq
                    seg_start = time.monotonic()
                    self._run_segmentation(frame, seg_frame_ts)
                    next_seg = seg_start + self.seg_interval
                    if next_seg <= time.monotonic():
                        next_seg = time.monotonic() + self.seg_interval
                else:
                    self.metrics.incr("seg_skipped")
                    self._seg_waiting = True
                continue

            # ----------------------------------------------------------
            # Sleep until the next deadline
            # ----------------------------------------------------------
            sleep_for = 0.01
            if self.det_enabled:
                sleep_for = min(sleep_for, max(0.001, next_det - now))
            if self.seg_enabled and not self._seg_waiting:
                sleep_for = min(sleep_for, max(0.001, next_seg - now))
            self.stop_event.wait(sleep_for)

    def _run_segmentation(self, frame, frame_ts: float) -> None:
        t0 = time.monotonic()
        mask = process_segmentation(
            self.segmenter,
            frame,
            self.profile,
            self.slowdown,
            self.metrics,
        )
        elapsed = time.monotonic() - t0
        self.metrics.incr("segmentation_run")

        if mask is not None:
            self.alerts.generate_curb(mask, self.segmenter.names, frame_ts)
            self.alerts.generate_scene(mask, self.segmenter.names, frame_ts)

        # Wall time includes the simulated slow-down; use it for slack checks.
        self._seg_estimate = 0.7 * self._seg_estimate + 0.3 * elapsed

        with self._pub_lock:
            self._latest_mask = mask
