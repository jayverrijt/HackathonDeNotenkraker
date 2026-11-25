"""Lightweight metrics collection for benchmark runs."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

log = logging.getLogger(__name__)


class Metrics:
    def __init__(self, profile):
        self.profile = profile
        self.started_at = time.time()
        self._lock = threading.Lock()
        self._stages: Dict[str, List[float]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, Any] = {}

    def record(self, stage: str, value_ms: float) -> None:
        if value_ms is None:
            return
        with self._lock:
            self._stages[stage].append(float(value_ms))

    def incr(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def gauge(self, name: str, value: Any) -> None:
        with self._lock:
            self._gauges[name] = value

    # ------------------------------------------------------------------
    # reporting
    # ------------------------------------------------------------------

    @staticmethod
    def _stats(values: List[float]) -> Dict[str, float]:
        if not values:
            return {"count": 0}
        arr = np.asarray(values, dtype=np.float64)
        return {
            "count": int(arr.size),
            "mean_ms": round(float(arr.mean()), 2),
            "p50_ms": round(float(np.percentile(arr, 50)), 2),
            "p95_ms": round(float(np.percentile(arr, 95)), 2),
            "p99_ms": round(float(np.percentile(arr, 99)), 2),
            "max_ms": round(float(arr.max()), 2),
        }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            stages = {name: self._stats(values) for name, values in self._stages.items()}
            counters = dict(self._counters)
            gauges = dict(self._gauges)

        return {
            "profile": self.profile.name,
            "profile_settings": self.profile.as_dict(),
            "started_at": self.started_at,
            "stages": stages,
            "counters": counters,
            "gauges": gauges,
        }

    @staticmethod
    def write_report(path: str, snapshot: Dict[str, Any]) -> None:
        output = Path(path)
        if not output.is_absolute():
            output = Path.cwd() / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        log.info("Report written to %s", output)

    @staticmethod
    def summary(snapshot: Dict[str, Any]) -> str:
        lines = []
        gauges = snapshot.get("gauges", {})
        counters = snapshot.get("counters", {})
        stages = snapshot.get("stages", {})

        lines.append(f"Profile: {snapshot.get('profile')}")
        lines.append(f"Elapsed: {gauges.get('elapsed_s', 0):.1f}s")
        kind = gauges.get("camera_kind")
        if kind:
            source = gauges.get("camera_source")
            source_resolution = gauges.get("camera_source_resolution")
            source_fps = gauges.get("camera_source_fps", 0.0)
            capture_resolution = gauges.get("camera_resolution")
            capture_fps = gauges.get("camera_capture_fps", 0.0)
            skip = gauges.get("camera_frame_skip", 1)
            line = (
                f"Source: {kind} {source} {source_resolution} @ {source_fps:.2f} "
                f"-> capture {capture_resolution} @ {capture_fps:.2f} FPS "
                f"(skip {skip})"
            )
            if kind == "video":
                line += (
                    f" (start {gauges.get('video_start_s', 0.0):.1f}s, "
                    f"loop={gauges.get('video_loop')})"
                )
            lines.append(line)
        lines.append(
            "Achieved: "
            f"det {gauges.get('detection_fps', 0):.2f} FPS, "
            f"seg {gauges.get('segmentation_fps', 0):.2f} FPS, "
            f"render {gauges.get('render_fps', 0):.2f} FPS"
        )
        lines.append(
            "Memory: "
            f"baseline {gauges.get('rss_baseline_mb', 0):.0f} MB, "
            f"peak {gauges.get('rss_peak_mb', 0):.0f} MB, "
            f"increment {gauges.get('rss_incremental_peak_mb', 0):.0f} MB"
        )
        lines.append(
            "Detection slots missed: "
            f"{gauges.get('detection_slots_missed_pct', 0):.1f}%"
        )
        if gauges.get("camera_to_alert_note"):
            lines.append(f"Note: {gauges['camera_to_alert_note']}")
        lines.append(
            "Counters: "
            + ", ".join(
                f"{name}={counters.get(name, 0)}"
                for name in (
                    "detections_run",
                    "segmentation_run",
                    "detection_slots_missed",
                    "seg_skipped",
                    "alerts_generated",
                    "alerts_suppressed_cooldown",
                    "alerts_suppressed_global",
                    "close_warnings",
                    "curb_warnings",
                    "scene_descriptions",
                    "tts_spoken",
                    "tts_dropped",
                    "tts_dropped_low_priority",
                    "tts_retries",
                    "tts_silent_failures",
                    "tts_errors",
                    "camera_read_failures",
                )
            )
        )

        important = [
            "detect_sim_ms",
            "detect_interval_ms",
            "frame_age_ms",
            "seg_sim_ms",
            "camera_to_alert_ms",
            "tts_start_latency_ms",
            "tts_duration_ms",
        ]
        for name in important:
            stats = stages.get(name, {})
            if stats.get("count"):
                lines.append(
                    f"  {name:24s} p50={stats['p50_ms']:8.2f}  "
                    f"p95={stats['p95_ms']:8.2f}  max={stats['max_ms']:8.2f}  "
                    f"n={stats['count']}"
                )

        acceptance = snapshot.get("acceptance")
        if acceptance and acceptance.get("checks"):
            lines.append("Gate: " + ("PASS" if acceptance.get("passed") else "FAIL"))
            for name, item in acceptance.get("checks", {}).items():
                lines.append(
                    f"  {'OK' if item['ok'] else 'FAIL':4s} {name}: "
                    f"{item['actual']} (min/limit {item['threshold']})"
                )

        lines.append(
            "Slowdown: "
            f"x{gauges.get('slowdown_base', 1.0)}"
            + (
                " + thermal"
                if gauges.get("slowdown_thermal_active")
                else ""
            )
        )

        return "\n".join(lines)
