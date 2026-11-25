"""Configuration profiles for desktop and phone-simulation runs.

A profile describes both the pipeline settings and the resource envelope the
process should be limited to.  ``desktop`` is unrestricted.  The phone profiles
cap threads/affinity, downscale the captured frame, reduce inference rates and
inflate measured latency so the scheduling behaviour resembles the target
handset.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class Profile:
    name: str = "desktop"

    # Models
    det_model: str = "models/yolo26n.pt"
    seg_model: str = "models/yolo26s-sem.pt"
    tracker: str = "bytetrack.yaml"

    # Camera request (for webcams; files use their native size)
    camera_index: int = 0
    camera_width: int = 1280
    camera_height: int = 720
    camera_fps: float = 30.0

    # Published capture size/rate.  Larger inputs are downscaled to fit here.
    capture_width: int = 960
    capture_height: int = 540
    capture_fps: float = 30.0

    # Inference
    det_size: int = 640
    seg_size: int = 512
    det_fps: float = 5.0
    seg_fps: float = 2.0
    confidence: float = 0.40

    # Spatial regions (image coordinates, not metres)
    centre_left: float = 0.35
    centre_right: float = 0.65
    lower_region_top: float = 0.55

    # Audio
    alert_cooldown: float = 5.0
    alert_global_cooldown: float = 0.0
    tts_mode: str = "native"  # native | stub | off
    tts_language: str = "en"
    tts_start_latency: float = 0.0
    tts_wpm: float = 175.0
    tts_volume: float = 1.0

    # Proximity warnings.  These are image-space heuristics, not distances.
    close_centre_left: float = 0.15
    close_centre_right: float = 0.85
    close_bottom_ratio: float = 0.75
    close_area_ratio: float = 0.03
    close_immediate_bottom: float = 0.90
    close_immediate_area: float = 0.08
    close_persist_frames: int = 2
    close_cooldown: float = 4.0
    curb_cooldown: float = 20.0
    curb_side_min: float = 0.40
    curb_road_min: float = 0.20
    curb_center_side_min: float = 0.35
    curb_center_road_min: float = 0.50

    # Low-priority scene descriptions from the semantic mask.
    scene_min_fraction: float = 0.22
    scene_cooldown: float = 20.0
    scene_quiet_after_alert: float = 2.0

    # Resource envelope. 0 means "not limited" (desktop).
    threads: int = 0
    interop_threads: int = 1
    cv_threads: int = 0
    cpu_affinity_count: int = 0
    slowdown: float = 1.0
    thermal_after_s: float = 0.0
    thermal_slowdown: float = 1.0
    rss_soft_mb: float = 0.0
    rss_hard_mb: float = 0.0

    # Display
    show_window: bool = True
    show_segmentation: bool = True
    render_fps: float = 30.0

    # Gate thresholds. 0 means "not enforced".
    min_det_fps: float = 0.0
    min_seg_fps: float = 0.0
    max_camera_alert_p95_ms: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


DESKTOP = Profile(name="desktop")

# Floor handset: 2022 mid-range, 4 GB class (Snapdragon 695 / Exynos 1280 /
# Dimensity 1080).  Capture is downscaled to 640x360 at 15 FPS, detection runs
# at 3 FPS with a 384 px input, and segmentation at 0.5 FPS.
PHONE_2022_MID = Profile(
    name="phone-2022-mid",
    capture_width=640,
    capture_height=360,
    capture_fps=15.0,
    det_size=384,
    seg_size=256,
    det_fps=3.0,
    seg_fps=0.5,
    threads=2,
    interop_threads=1,
    cv_threads=2,
    cpu_affinity_count=4,
    slowdown=3.0,
    thermal_after_s=120.0,
    thermal_slowdown=1.2,
    rss_soft_mb=900.0,
    rss_hard_mb=1300.0,
    show_window=False,
    alert_global_cooldown=3.0,
    tts_mode="stub",
    tts_language="en",
    tts_start_latency=0.15,
    min_det_fps=2.5,
    min_seg_fps=0.4,
    max_camera_alert_p95_ms=700.0,
)

# 2023 mid-range (Snapdragon 778G / Dimensity 1080 class, 6-8 GB).
PHONE_2023_MID = Profile(
    name="phone-2023-mid",
    capture_width=640,
    capture_height=360,
    capture_fps=15.0,
    det_size=480,
    seg_size=320,
    det_fps=4.0,
    seg_fps=1.0,
    threads=4,
    interop_threads=1,
    cv_threads=2,
    cpu_affinity_count=6,
    slowdown=2.0,
    thermal_after_s=180.0,
    thermal_slowdown=1.25,
    rss_soft_mb=1000.0,
    rss_hard_mb=1400.0,
    show_window=False,
    alert_global_cooldown=3.0,
    tts_mode="stub",
    tts_language="en",
    tts_start_latency=0.15,
    min_det_fps=3.5,
    min_seg_fps=0.8,
    max_camera_alert_p95_ms=600.0,
)

PROFILES = {p.name: p for p in (DESKTOP, PHONE_2022_MID, PHONE_2023_MID)}


def get_profile(name: Optional[str] = None) -> Profile:
    """Return a profile by name, defaulting to desktop."""
    if not name:
        return DESKTOP
    try:
        return PROFILES[name]
    except KeyError:
        available = ", ".join(PROFILES)
        raise SystemExit(f"Unknown profile {name!r}. Available: {available}")
