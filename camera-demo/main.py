"""Command-line entry point.

Heavy imports (torch/cv2/ultralytics) happen only after the selected profile's
environment variables have been applied, so thread limits take effect.

If ``citywalk.mp4`` exists in the repository root (or ``videos/`` /
``test_videos/``), it is used as the default test source.  Pass ``--camera``
to force the webcam.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_TEST_VIDEO = "citywalk.mp4"
TEST_VIDEO_DIRS = (ROOT, ROOT / "videos", ROOT / "test_videos")

log = logging.getLogger(__name__)


def find_test_video(filename: str = DEFAULT_TEST_VIDEO, directories=None):
    """Return the first existing test video path, or ``None``."""
    search_dirs = TEST_VIDEO_DIRS if directories is None else tuple(directories)
    for directory in search_dirs:
        candidate = Path(directory) / filename
        if candidate.is_file():
            return candidate
    return None


def _parse_source(source):
    if isinstance(source, Path):
        return str(source)
    if isinstance(source, str) and source.isdigit():
        return int(source)
    return source


def resolve_source(args, profile, test_video=None):
    """Resolve the camera/video source and its start/loop settings.

    Precedence: ``--source`` / ``--video`` > ``--camera`` > auto-detected test
    video > webcam.
    """
    if args.source is not None:
        parsed = _parse_source(args.source)
        return parsed, (0.0 if isinstance(parsed, int) else args.start), args.loop, "source"
    if args.video is not None:
        parsed = _parse_source(args.video)
        return parsed, (0.0 if isinstance(parsed, int) else args.start), args.loop, "video"
    if args.camera:
        return profile.camera_index, 0.0, args.loop, "camera"
    if test_video is not None:
        return str(test_video), args.start, args.loop, "auto-video"
    return profile.camera_index, 0.0, args.loop, "camera-fallback"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline accessibility vision assistant"
    )
    parser.add_argument(
        "--profile",
        default="desktop",
        help="desktop | phone-2022-mid | phone-2023-mid",
    )

    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--source",
        default=None,
        help="Camera index or video file (auto-uses citywalk.mp4 if present)",
    )
    source_group.add_argument(
        "--video",
        default=None,
        help="Video file to use instead of the webcam (alias for --source)",
    )
    source_group.add_argument(
        "--camera",
        action="store_true",
        help="Force the webcam even if a test video exists",
    )

    parser.add_argument(
        "--start",
        type=float,
        default=0.0,
        help="Start offset in the video in seconds",
    )
    parser.add_argument(
        "--no-loop",
        dest="loop",
        action="store_false",
        default=True,
        help="Stop at the end of the video instead of looping",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Seconds to run (0 = until Q/Ctrl+C or end of a non-looping video)",
    )
    parser.add_argument("--headless", dest="headless", action="store_true", default=None)
    parser.add_argument("--window", dest="headless", action="store_false", default=None)
    parser.add_argument("--tts", choices=["native", "stub", "off"], default=None)
    parser.add_argument("--record", default=None, help="Write the captured video to this path")
    parser.add_argument("--out", default=None, help="Write a JSON metrics report here")
    parser.add_argument("--gate", action="store_true", help="Exit non-zero if the profile gate fails")

    parser.add_argument("--det-size", type=int, default=None)
    parser.add_argument("--seg-size", type=int, default=None)
    parser.add_argument("--det-fps", type=float, default=None)
    parser.add_argument("--seg-fps", type=float, default=None)
    parser.add_argument("--capture-width", type=int, default=None)
    parser.add_argument("--capture-height", type=int, default=None)
    parser.add_argument("--capture-fps", type=float, default=None)
    parser.add_argument("--slowdown", type=float, default=None)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--affinity", type=int, default=None)
    return parser.parse_args(argv)


def run_cli(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    from config import get_profile  # noqa: PLC0415 - stdlib only

    profile = get_profile(args.profile)

    overrides = {}
    for arg_name, profile_name in (
        ("det_size", "det_size"),
        ("seg_size", "seg_size"),
        ("det_fps", "det_fps"),
        ("seg_fps", "seg_fps"),
        ("capture_width", "capture_width"),
        ("capture_height", "capture_height"),
        ("capture_fps", "capture_fps"),
        ("slowdown", "slowdown"),
        ("threads", "threads"),
        ("affinity", "cpu_affinity_count"),
    ):
        value = getattr(args, arg_name)
        if value is not None:
            overrides[profile_name] = value
    if overrides:
        profile = replace(profile, **overrides)

    # Must happen before torch/cv2 are imported by src.pipeline.
    from src.limits import configure_environment  # noqa: PLC0415

    configure_environment(profile)

    from src.pipeline import run  # noqa: PLC0415

    test_video = find_test_video()
    source, start, loop, origin = resolve_source(args, profile, test_video)

    if isinstance(source, int):
        if args.start:
            log.warning("--start is ignored for camera sources")
        start = 0.0
        if origin == "camera-fallback":
            log.info(
                "No %s found; using camera %s",
                DEFAULT_TEST_VIDEO,
                source,
            )
        else:
            log.info("Using camera %s", source)
    else:
        if origin == "auto-video":
            log.info("Auto-selected test video %s", source)
        log.info(
            "Using video %s (start %.1fs, loop=%s)",
            source,
            start,
            loop,
        )

    show_window = None if args.headless is None else (not args.headless)

    return run(
        profile,
        source=source,
        video_start=start,
        loop=loop,
        duration=args.duration,
        show_window=show_window,
        tts_mode=args.tts,
        record=args.record,
        out=args.out,
        gate=args.gate,
    )


if __name__ == "__main__":
    sys.exit(run_cli())
