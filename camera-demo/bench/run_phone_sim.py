"""Run the phone-simulation benchmark.

By default this uses ``citywalk.mp4`` from the repository root (or ``videos/``
/ ``test_videos/``) when it exists, otherwise the webcam.

Examples:
    python bench/run_phone_sim.py
    python bench/run_phone_sim.py --start 600 --duration 120
    python bench/run_phone_sim.py --camera
    python bench/run_phone_sim.py --profile phone-2023-mid --window
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import run_cli  # noqa: E402


def _has_flag(args, flag: str) -> bool:
    return any(item == flag or item.startswith(flag + "=") for item in args)


def main() -> int:
    args = list(sys.argv[1:])

    if not _has_flag(args, "--profile"):
        args = ["--profile", "phone-2022-mid"] + args
    if not _has_flag(args, "--headless") and not _has_flag(args, "--window"):
        args.append("--headless")
    if not _has_flag(args, "--tts"):
        args += ["--tts", "stub"]
    if not _has_flag(args, "--duration"):
        args += ["--duration", "60"]
    if not _has_flag(args, "--out"):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        args += ["--out", str(ROOT / "bench" / "results" / f"phone-sim_{stamp}.json")]

    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
