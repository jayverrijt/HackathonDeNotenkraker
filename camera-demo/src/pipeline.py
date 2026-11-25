"""Pipeline wiring: models, camera, scheduler, speech, render loop, report."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import replace

import cv2

from .alerts import AlertEngine
from .camera import CameraSource
from .limits import (
    MemoryGuard,
    Slowdown,
    apply_runtime_limits,
    process_cpu_seconds,
    process_rss_mb,
)
from .metrics import Metrics
from .models import load_models
from .overlay import render
from .scheduler import Scheduler
from .tts import SpeechEngine

log = logging.getLogger(__name__)

WINDOW_NAME = "Outdoor Accessibility Assistant"


def _evaluate_gate(profile, snapshot: dict) -> dict:
    gauges = snapshot.get("gauges", {})
    stages = snapshot.get("stages", {})
    counters = snapshot.get("counters", {})

    checks = {}

    def add(name, actual, threshold, ok, unit=""):
        checks[name] = {
            "actual": round(float(actual), 2) if isinstance(actual, (int, float)) else actual,
            "threshold": threshold,
            "unit": unit,
            "ok": bool(ok),
        }

    if profile.min_det_fps > 0:
        actual = gauges.get("detection_fps", 0.0)
        add("detection_fps", actual, profile.min_det_fps, actual >= profile.min_det_fps)

    if profile.min_seg_fps > 0:
        actual = gauges.get("segmentation_fps", 0.0)
        add("segmentation_fps", actual, profile.min_seg_fps, actual >= profile.min_seg_fps)

    if profile.max_camera_alert_p95_ms > 0:
        stats = stages.get("camera_to_alert_ms", {})
        count = stats.get("count", 0)
        if count >= 8:
            actual = stats["p95_ms"]
            add(
                "camera_to_alert_p95_ms",
                actual,
                profile.max_camera_alert_p95_ms,
                actual <= profile.max_camera_alert_p95_ms,
            )
        else:
            gauges["camera_to_alert_note"] = (
                f"latency gate skipped: only {count} spoken alerts "
                "(run longer for a stable p95)"
            )

    if profile.rss_hard_mb > 0:
        actual = gauges.get("rss_peak_mb", 0.0)
        add("rss_peak_mb", actual, profile.rss_hard_mb, actual <= profile.rss_hard_mb)

    missed = counters.get("detection_slots_missed", 0)
    total = max(1, counters.get("detections_run", 0) + missed)
    gauges["detection_slots_missed_pct"] = round(missed / total * 100.0, 2)

    return {
        "passed": all(item["ok"] for item in checks.values()),
        "checks": checks,
    }


def run(
    profile,
    source=0,
    duration: float = 0.0,
    show_window=None,
    tts_mode=None,
    record: str | None = None,
    out: str | None = None,
    gate: bool = False,
    video_start: float = 0.0,
    loop: bool = True,
):
    if show_window is not None:
        profile = replace(profile, show_window=show_window)
    if tts_mode is not None:
        profile = replace(profile, tts_mode=tts_mode)

    if profile.tts_mode == "stub":
        log.warning(
            "TTS mode is 'stub' (silent); pass --tts native to hear alerts"
        )
    elif profile.tts_mode == "native":
        log.info(
            "TTS mode: native (%s voice selected on first utterance)",
            profile.tts_language,
        )

    limits_info = apply_runtime_limits(profile)
    metrics = Metrics(profile)

    guard = MemoryGuard(profile.rss_soft_mb, profile.rss_hard_mb)
    guard.start()

    detector, segmenter, model_info = load_models(profile, metrics)

    speech = SpeechEngine(profile, metrics)
    speech.start()
    alerts = AlertEngine(profile, speech, metrics)

    camera = CameraSource(
        source,
        width=profile.capture_width,
        height=profile.capture_height,
        fps=profile.capture_fps,
        request_width=profile.camera_width,
        request_height=profile.camera_height,
        request_fps=profile.camera_fps,
        record_path=record,
        start=video_start,
        loop=loop,
    ).start()

    metrics.gauge("camera_source", str(camera.source))
    metrics.gauge("camera_kind", "video" if camera.is_file else "camera")
    metrics.gauge("camera_source_resolution", f"{camera.source_width}x{camera.source_height}")
    metrics.gauge("camera_source_fps", camera.source_fps)
    metrics.gauge("camera_resolution", f"{camera.width}x{camera.height}")
    metrics.gauge("camera_capture_fps", camera.capture_fps)
    metrics.gauge("camera_fps_nominal", camera.fps)
    metrics.gauge("camera_frame_skip", camera.skip)
    metrics.gauge("video_start_s", camera.start_s)
    metrics.gauge("video_loop", camera.loop)

    slowdown = Slowdown(
        factor=profile.slowdown,
        thermal_after_s=profile.thermal_after_s,
        thermal_factor=profile.thermal_slowdown,
    )
    stop_event = threading.Event()
    scheduler = Scheduler(
        profile,
        camera,
        detector,
        segmenter,
        alerts,
        metrics,
        slowdown,
        stop_event,
    )

    memory_exceeded = False
    start = time.monotonic()
    cpu_start = process_cpu_seconds()
    scheduler.start()

    try:
        if profile.show_window:
            _render_loop(
                camera, scheduler, profile, metrics, stop_event, duration, start, guard
            )
        else:
            _wait_loop(camera, scheduler, guard, stop_event, duration, start)
        memory_exceeded = bool(guard.exceeded.is_set())
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    finally:
        stop_event.set()
        scheduler.join(timeout=5.0)
        speech.stop()
        camera.close()
        guard.stop()
        if profile.show_window:
            cv2.destroyAllWindows()

    elapsed = max(1e-6, time.monotonic() - start)
    cpu_seconds = max(0.0, process_cpu_seconds() - cpu_start)

    counters = metrics.snapshot()["counters"]
    metrics.gauge("elapsed_s", elapsed)
    metrics.gauge("detection_fps", counters.get("detections_run", 0) / elapsed)
    metrics.gauge("segmentation_fps", counters.get("segmentation_run", 0) / elapsed)
    metrics.gauge("render_fps", counters.get("render_frames", 0) / elapsed)
    metrics.gauge("camera_fps", camera.frames_captured / elapsed)
    metrics.gauge("camera_frames_captured", camera.frames_captured)
    metrics.gauge("camera_frames_read", camera.frames_read)
    metrics.gauge("camera_finished", camera.finished.is_set())
    metrics.gauge("process_cpu_percent", cpu_seconds / elapsed * 100.0)
    metrics.gauge("camera_read_failures", camera.read_failures)

    metrics.gauge("rss_baseline_mb", guard.baseline_mb)
    metrics.gauge("rss_peak_mb", guard.peak_mb)
    metrics.gauge("rss_incremental_peak_mb", guard.incremental_peak_mb)
    metrics.gauge("rss_end_mb", process_rss_mb())
    metrics.gauge("rss_soft_cap_exceeded", guard.warned)

    metrics.gauge("limits", limits_info)
    metrics.gauge("models", model_info)
    metrics.gauge("slowdown_base", profile.slowdown)
    metrics.gauge("slowdown_thermal_active", slowdown.thermal_active)
    metrics.gauge("slowdown_total_slept_s", round(slowdown.total_slept_s, 2))

    snapshot = metrics.snapshot()
    snapshot["acceptance"] = _evaluate_gate(profile, snapshot)

    print()
    print(Metrics.summary(snapshot))

    if out:
        Metrics.write_report(out, snapshot)

    if memory_exceeded:
        log.error("Stopped because the RSS hard cap was exceeded")
        return 2

    if gate and not snapshot["acceptance"]["passed"]:
        log.error("Performance gate failed")
        return 1

    return 0


def _wait_loop(camera, scheduler, guard, stop_event, duration, start) -> None:
    while not stop_event.is_set():
        if duration and time.monotonic() - start >= duration:
            break
        if camera.finished.is_set():
            log.info("Video source ended; stopping run")
            break
        if guard is not None and guard.exceeded.is_set():
            break
        if not scheduler.is_alive():
            log.error("Scheduler thread stopped unexpectedly")
            break
        stop_event.wait(0.1)


def _render_loop(camera, scheduler, profile, metrics, stop_event, duration, start, guard=None) -> None:
    last_seq = -1
    while not stop_event.is_set():
        if duration and time.monotonic() - start >= duration:
            break
        if camera.finished.is_set():
            log.info("Video source ended; stopping run")
            break
        if guard is not None and guard.exceeded.is_set():
            break
        if not scheduler.is_alive():
            log.error("Scheduler thread stopped unexpectedly")
            break

        latest = camera.latest(last_seq)
        if latest is None:
            stop_event.wait(0.003)
            continue

        frame, _, seq = latest
        last_seq = seq
        _, detections, mask = scheduler.snapshot()

        t0 = time.perf_counter()
        output = render(frame, detections, mask, profile)
        cv2.imshow(WINDOW_NAME, output)
        key = cv2.waitKey(1) & 0xFF
        metrics.record("render_compute_ms", (time.perf_counter() - t0) * 1000.0)
        metrics.incr("render_frames")

        if key == ord("q"):
            break
