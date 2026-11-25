"""Resource limits used to approximate a phone on a desktop machine.

Two things happen here:

* environment variables and library thread counts are lowered before/after the
  heavy imports (``torch``, ``cv2``);
* a ``Slowdown`` helper inflates measured inference time by a configurable
  factor so the scheduler sees phone-like latency and drops frames the way it
  would on the target device.

This is a simulation, not a hardware measurement.  The slow-down factor is a
safety margin, not a claim about any particular SoC.
"""

from __future__ import annotations

import logging
import os
import threading
import time

import psutil

log = logging.getLogger(__name__)


def configure_environment(profile) -> dict:
    """Set process-wide environment variables *before* torch/cv2 import."""
    threads = profile.threads
    if threads:
        for key in (
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        ):
            os.environ[key] = str(threads)

    os.environ.setdefault("YOLO_VERBOSE", "false")
    # Keep OpenMP from overriding the process CPU affinity mask on Windows.
    os.environ.setdefault("KMP_AFFINITY", "disabled")
    return {"threads_env": threads}


def apply_runtime_limits(profile) -> dict:
    """Apply library thread limits and process CPU affinity."""
    import cv2  # noqa: PLC0415 - deliberately imported late
    import torch  # noqa: PLC0415

    info = {
        "torch_threads": int(torch.get_num_threads()),
        "torch_interop_threads": int(torch.get_num_interop_threads()),
        "cv_threads": int(cv2.getNumThreads()),
        "cpu_affinity": None,
    }

    if profile.threads:
        torch.set_num_threads(profile.threads)
    else:
        torch.set_num_threads(max(1, os.cpu_count() or 1))
    info["torch_threads"] = int(torch.get_num_threads())

    try:
        torch.set_num_interop_threads(profile.interop_threads)
        info["torch_interop_threads"] = int(torch.get_num_interop_threads())
    except RuntimeError:
        # Already set, or parallel work has started. Keep the existing value.
        info["torch_interop_threads"] = int(torch.get_num_interop_threads())

    if profile.cv_threads:
        cv2.setNumThreads(profile.cv_threads)
        info["cv_threads"] = int(cv2.getNumThreads())

    cv2.ocl.setUseOpenCL(False)

    if profile.cpu_affinity_count:
        try:
            process = psutil.Process()
            current = process.cpu_affinity()
            wanted = current[: max(1, min(profile.cpu_affinity_count, len(current)))]
            if len(wanted) < len(current):
                process.cpu_affinity(wanted)
            info["cpu_affinity"] = list(process.cpu_affinity())
        except (AttributeError, NotImplementedError, OSError) as exc:
            log.warning("Could not set CPU affinity: %s", exc)

    log.info(
        "Runtime limits: torch_threads=%s cv_threads=%s affinity=%s",
        info["torch_threads"],
        info["cv_threads"],
        info["cpu_affinity"],
    )
    return info


class MemoryGuard(threading.Thread):
    """Background RSS watcher with soft warning and hard stop thresholds."""

    def __init__(self, soft_mb: float = 0.0, hard_mb: float = 0.0, interval: float = 0.5):
        super().__init__(name="memory-guard", daemon=True)
        self.soft_mb = float(soft_mb or 0.0)
        self.hard_mb = float(hard_mb or 0.0)
        self.interval = float(interval)

        process = psutil.Process()
        self.baseline_mb = process.memory_info().rss / 1e6
        self.peak_mb = self.baseline_mb
        self.warned = False
        self.exceeded = threading.Event()
        self._stop = threading.Event()

    def run(self) -> None:
        process = psutil.Process()
        while not self._stop.wait(self.interval):
            rss_mb = process.memory_info().rss / 1e6
            self.peak_mb = max(self.peak_mb, rss_mb)

            if self.hard_mb and rss_mb >= self.hard_mb:
                log.error(
                    "RSS hard cap exceeded: %.0f MB >= %.0f MB", rss_mb, self.hard_mb
                )
                self.exceeded.set()
                return

            if self.soft_mb and rss_mb >= self.soft_mb and not self.warned:
                self.warned = True
                log.warning(
                    "RSS soft cap exceeded: %.0f MB >= %.0f MB", rss_mb, self.soft_mb
                )

    def stop(self) -> None:
        self._stop.set()
        if self.is_alive():
            self.join(timeout=2.0)

    @property
    def incremental_peak_mb(self) -> float:
        return self.peak_mb - self.baseline_mb


class Slowdown:
    """Inflate inference wall time to imitate a slower target device.

    ``inflate`` sleeps so the total stage time becomes ``elapsed * factor``.
    The factor can increase after ``thermal_after_s`` to imitate throttling.
    """

    def __init__(
        self,
        factor: float = 1.0,
        thermal_after_s: float = 0.0,
        thermal_factor: float = 1.0,
    ):
        self.base_factor = float(factor)
        self.thermal_after_s = float(thermal_after_s or 0.0)
        self.thermal_factor = float(thermal_factor or 1.0)
        self.started = time.monotonic()
        self.thermal_active = False
        self.total_slept_s = 0.0
        self._lock = threading.Lock()

    def current_factor(self) -> float:
        factor = self.base_factor
        if self.thermal_after_s:
            age = time.monotonic() - self.started
            if age >= self.thermal_after_s and not self.thermal_active:
                with self._lock:
                    if not self.thermal_active:
                        self.thermal_active = True
                        log.warning(
                            "Thermal simulation active after %.0fs: factor x%.2f",
                            age,
                            self.thermal_factor,
                        )
            if self.thermal_active:
                factor *= self.thermal_factor
        return factor

    def inflate(self, elapsed_s: float) -> float:
        """Sleep, then return the simulated stage duration in seconds."""
        factor = self.current_factor()
        if factor <= 1.0:
            return elapsed_s

        target = elapsed_s * factor
        remaining = target - elapsed_s
        if remaining > 0:
            time.sleep(remaining)
            with self._lock:
                self.total_slept_s += remaining
        return target


def process_cpu_seconds() -> float:
    """Total CPU time (user + system) consumed by this process."""
    times = psutil.Process().cpu_times()
    return float(times.user + times.system)


def process_rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1e6
