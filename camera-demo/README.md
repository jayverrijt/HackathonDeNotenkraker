# Offline Accessibility Vision Assistant

A chest-mounted smartphone assistant for blind and visually impaired users.
This repository is the Python prototype and phone-simulation harness.  The
Android implementation is the next phase.

> This is assistive technology under development. It is not a replacement for
> a white cane, a guide dog or established mobility techniques.

## What is implemented

- YOLO26n object detection + ByteTrack tracking.
- YOLO26s-sem semantic segmentation.
- Downscaled capture (640×360 on phone profiles) with frame skipping and a
  configurable capture FPS.
- Image-space spatial analysis (left / centre / right, lower region).
- Rate-limited spoken alerts with a priority queue and a TTS stub that
  simulates phone start latency and speech duration.
- English TTS voice selection (prefers `en-US`, then `en-GB`).
- Natural-language messages such as “There is a person close in front of you”
  and “There are trees or plants to your left.”
- Close-object and possible-curb warnings at priority 3, so they interrupt
  lower-priority narration.
- Low-priority semantic scene descriptions for vegetation/trees and buildings.
- A phone-simulation mode with thread limits, CPU affinity, RSS caps and an
  optional latency slow-down factor.
- A measured JSON report and a pass/fail performance gate.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

Models are expected in `models/`:

```text
models/yolo26n.pt
models/yolo26s-sem.pt
```

## Run

If `citywalk.mp4` exists in the repository root (or `videos/` or
`test_videos/`), it is used automatically. Otherwise the webcam is used.
The current `videos/citywalk.mp4` is 1920×1080 at 30 FPS; phone profiles
downscale it to 640×360 and publish at 15 FPS, so the report shows both the
source and capture sizes.

Desktop demo (window, native TTS):

```powershell
.\.venv\Scripts\python main.py
```

Force the webcam:

```powershell
.\.venv\Scripts\python main.py --camera
```

Use a specific video, starting 10 minutes in, without looping:

```powershell
.\.venv\Scripts\python main.py --video videos/citywalk.mp4 --start 600 --no-loop
```

Press `Q` in the preview window to quit.

Headless desktop run:

```powershell
.\.venv\Scripts\python main.py --duration 30 --headless --tts stub
```

Phone simulation (defaults to the 2022 floor profile, `citywalk.mp4`, 60
seconds, headless, stub TTS, JSON report):

```powershell
.\.venv\Scripts\python bench\run_phone_sim.py
```

Add `--tts native` if you want to hear the English warnings during a phone
simulation; the default `stub` is silent.

2023 profile with the performance gate:

```powershell
.\.venv\Scripts\python bench\run_phone_sim.py --profile phone-2023-mid --duration 60 --gate
```

Useful overrides:

```powershell
--source clip.mp4        # explicit file or camera index
--video videos/citywalk.mp4
--camera                 # force the webcam even when a test video exists
--start 600              # start 10 minutes into the video
--no-loop                # stop at the end of the video
--capture-width 640      # published frame size (downscaled if needed)
--capture-height 360
--capture-fps 15         # publish at most 15 frames/second
--det-size 384
--seg-size 256
--det-fps 3
--seg-fps 0.5
--slowdown 3.0
--threads 2
--affinity 4
--out bench/results/run.json
--record clip.mp4        # record the downscaled captured stream
```

Tests:

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

## Profiles

| | `phone-2022-mid` (floor) | `phone-2023-mid` |
|---|---|---|
| Intended device | Snapdragon 695 / Exynos 1280 class, 4 GB | Snapdragon 778G / Dimensity 1080 class, 6–8 GB |
| Capture (published) | 640×360 @ 15 FPS | 640×360 @ 15 FPS |
| Detection input / target | 384 px / 3 FPS | 480 px / 4 FPS |
| Segmentation input / target | 256 px / 0.5 FPS | 320 px / 1 FPS |
| Threads / affinity | 2 / 4 logical CPUs | 4 / 6 logical CPUs |
| Simulated slow-down | 3.0× | 2.0× |
| RSS soft / hard | 900 / 1300 MB | 1000 / 1400 MB |

A 1080p source is downscaled to 640×360 and published at 15 FPS. Detection
runs at 3–4 FPS and segmentation at 0.5–1 FPS, so the models see far fewer
frames than the source. Use `--capture-width 480 --capture-height 270` for
even more headroom, or `--capture-width 960 --capture-height 540` on desktop.

The slow-down factor sleeps after each inference so the scheduler sees
phone-like latency.  It is deliberately conservative and configurable; the
report shows both raw compute time and simulated stage time.

## Measured results (60 s, `videos/citywalk.mp4` 1920×1080@30 → 640×360@15, stub TTS)

| Metric | 2022 floor | 2023 mid |
|---|---|---|
| Detection | **2.80 FPS** | **3.80 FPS** |
| Segmentation | **0.48 FPS** | **0.95 FPS** |
| Camera → TTS start p50 | 298 ms | 252 ms |
| Camera → TTS start p95 | **473 ms** | **362 ms** |
| Camera → TTS start max | 630 ms | 523 ms |
| RSS peak | 691 MB | 693 MB |
| Detection slots missed | 0.0% | 0.0% |
| Close warnings | 15 | 15 |
| Curb warnings | 2 | 3 |
| Scene descriptions | 4 | 1 |
| Gate | **PASS** | **PASS** |

The first 60 s of this clip is a crowded road segment, so close warnings are
frequent and general narration is often dropped behind them.  Scene
descriptions still get through when the speech queue is idle (4/1 in this
segment).  Both profiles stay below 700 MB in this Python simulation; the
Android build will use less.

The gates are detection ≥ 2.5/3.5 FPS, segmentation ≥ 0.4/0.8 FPS and alert
p95 ≤ 700/600 ms for the 2022/2023 profiles.  Both profiles stay below 700 MB
in this Python simulation; the Android build will use far less.

The source clip is 1080p; the pipeline downscales it to 640×360 before
detection and segmentation.  Use `--camera` or a different `--video` to test
other scenes, and `--start` to sample a different part of a long clip.

Reports are in `bench/results/` (`phone-2022-mid_final.json`,
`phone-2023-mid_final.json`).  A 30-second run has too few spoken alerts for a
stable p95, so the latency check is skipped with a note; use 60 seconds or
longer when evaluating alert latency.

## English audio

The desktop native backend uses **Windows SAPI** (via `comtypes`) and reuses one
voice object, so every alert is spoken.  It selects the English voice at
startup, preferring `en-US` then `en-GB`; on this machine it selects
*Microsoft Zira Desktop - English (United States)* instead of the German
default.  If SAPI is unavailable, it falls back to a fresh `pyttsx3` engine per
utterance, which avoids the Windows “only the first sentence plays” bug.

The logs show the audio path:

- `Audio alert queued: ...` — an alert passed the cooldown and was queued.
- `TTS speaking: ...` — the backend is starting that sentence.
- `TTS spoke: ... (2.91s)` — the sentence actually played for a realistic
  duration.
- Dropped low-priority alerts are logged at debug level; the report counts
  `tts_spoken`, `tts_dropped`, `tts_silent_failures`, `tts_errors` and
  `tts_duration_ms`.

A busy street produces more alerts than any TTS engine can speak, so the queue
keeps the highest-priority one and drops stale/general narration.  The
benchmark uses the stub backend and is quiet; add `--tts native` to hear it.

Check the audio backend directly:

```powershell
.\.venv\Scripts\python bench\tts_check.py
```

This speaks three English messages and fails if any of them is silent.

All alert messages are English and conversational:

- `There is a person close in front of you.`
- `There is a car close on your right.`
- `There is a bench to your left.`
- `There is a bench in front of you.`
- `There are several people in front of you.`
- `There may be a curb on your left.`
- `There may be a curb or road edge ahead.`
- `There are trees or plants to your left.`
- `There is a building to your right.`

## Close-object and curb warnings

**Close object** — an image-space heuristic, not a distance:

- the box must be in the walking band (15–85% of image width);
- its bottom must be low in the frame (≥ 75% of height);
- its area must be ≥ 3% of the frame;
- it must appear in 2 of the last 3 detection frames, or immediately if it is
  very close (bottom ≥ 90%, area ≥ 8%);
- warnings use priority 3 and a 4 s cooldown per tracked object.

Warnings sound like `There is a person close in front of you` or
`There is a bench close on your left`.  No metres are announced.

**Possible curb** — the semantic model has no `curb` class, so this is a
road/sidewalk-boundary heuristic:

- sidewalk underfoot with road above it in the centre → *There may be a curb or
  road edge ahead*;
- road and sidewalk both close in the lower left/right band → *There may be a
  curb on your left/right*;
- warnings use priority 3 and a 20 s cooldown per side.

**Scene descriptions** — the semantic mask can describe large vegetation,
building, wall or fence regions:

- `There are trees or plants to your left.`
- `There is a building to your right.`

These are low priority, use a 20 s cooldown per side/class, and are skipped for
2 s after a safety warning.  The model class is `vegetation`, not `tree`, so
the wording is “trees or plants”.

This is deliberately uncertain and can miss curbs or produce false positives.
A real curb class or monocular depth estimation is future work.  General scene
narration is dropped if a higher-priority warning is already speaking, so close
and curb alerts are not queued behind it.

## What the simulation does and does not cover

It does:

- limit inference threads and pin the process to a small CPU set;
- cap RSS and stop on a hard breach;
- downscale the source to the profile capture size and publish at the capture
  FPS (15 FPS on phone profiles);
- pace video files in real time and use latest-frame-only semantics;
- simulate TTS start latency and speech duration;
- select an English voice for native desktop TTS;
- inflate inference wall time to approximate a slower SoC;
- increase latency after a thermal window to verify graceful degradation.

It does **not** replace on-device testing:

- x86 PyTorch kernels are not ARM NEON/NPU/GPU delegates;
- phone thermal throttling, battery drain and camera HAL are not modelled;
- Android/iOS TTS engines and haptics are not exercised;
- the slow-down factor is a safety margin, not a measurement of any SoC.

The next step is an Android build using CameraX + LiteRT/ONNX Runtime with the
same profile budgets, followed by a physical 2022/2023 handset test.

## Project layout

```text
config.py              profiles and budgets
main.py                CLI entry point
src/limits.py          thread/affinity/RSS limits + slow-down
src/camera.py          webcam/video source, latest-frame-only
src/models.py          model loading, detection, segmentation
src/alerts.py          spatial analysis and rate-limited alerts
src/messages.py        natural-language message templates
src/proximity.py       close-object, curb and scene heuristics
src/tts.py             non-blocking native/stub speech, English voice selection
src/scheduler.py       detection-first inference scheduler
src/overlay.py         preview rendering
src/metrics.py         per-stage timings and JSON report
src/pipeline.py        wiring, render loop, acceptance gate
bench/run_phone_sim.py phone-simulation launcher
bench/tts_check.py     three-message audio backend check
tests/                 spatial, proximity, audio, source and limit tests
```
