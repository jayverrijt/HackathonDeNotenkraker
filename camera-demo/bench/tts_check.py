"""Speak three English messages and verify that every one is audible.

Run:
    python bench/tts_check.py
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DESKTOP  # noqa: E402
from src.metrics import Metrics  # noqa: E402
from src.tts import SpeechEngine  # noqa: E402

MESSAGES = [
    "There is a person close in front of you.",
    "There is a bench to your left.",
    "There are trees or plants to your left.",
]


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    profile = replace(DESKTOP, tts_mode="native", tts_volume=0.7)
    metrics = Metrics(profile)
    speech = SpeechEngine(profile, metrics)
    speech.start()

    for index, message in enumerate(MESSAGES):
        print(f"Speak {index + 1}/{len(MESSAGES)}: {message}")
        speech.say(
            message,
            key=f"check_{index}",
            priority=3,
            frame_ts=time.monotonic(),
        )
        time.sleep(4.0)

    speech.stop()
    snapshot = metrics.snapshot()
    counters = snapshot["counters"]
    duration = snapshot["stages"].get("tts_duration_ms", {})

    print()
    print("Counters:", counters)
    if duration.get("count"):
        print(
            "Speech duration ms: "
            f"n={duration['count']} "
            f"p50={duration['p50_ms']:.0f} "
            f"p95={duration['p95_ms']:.0f} "
            f"max={duration['max_ms']:.0f}"
        )

    spoken = counters.get("tts_spoken", 0)
    silent = counters.get("tts_silent_failures", 0)
    errors = counters.get("tts_errors", 0)

    if spoken < len(MESSAGES) or silent or errors:
        print(
            f"FAIL: spoken={spoken}/{len(MESSAGES)} "
            f"silent_failures={silent} errors={errors}"
        )
        return 1

    print(f"PASS: {spoken}/{len(MESSAGES)} messages spoken")
    return 0


if __name__ == "__main__":
    sys.exit(main())
