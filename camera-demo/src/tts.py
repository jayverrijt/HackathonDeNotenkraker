"""Non-blocking speech output with a queue depth of one.

``stub`` simulates the timing of a phone TTS engine (start latency + speech
duration) without making noise, which is what the phone-simulation benchmarks
use.  ``native`` uses Windows SAPI (via comtypes) for the desktop demo, with a
pyttsx3 fallback.  ``off`` disables speech.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional, Tuple

log = logging.getLogger(__name__)

Pending = Tuple[str, int, Optional[float], float]  # message, priority, frame_ts, enqueued_at


def pick_english_voice(engine, language: str = "en"):
    """Return the best English voice exposed by a pyttsx3 engine.

    Prefer en-US, then en-GB, then any voice whose name/id mentions English.
    Returns ``None`` when no English voice is available.
    """
    try:
        voices = engine.getProperty("voices") or []
    except Exception:
        return None

    language = (language or "en").lower()
    best = None
    best_score = 0

    for voice in voices:
        pieces = [str(getattr(voice, "id", "")), str(getattr(voice, "name", ""))]
        for lang in getattr(voice, "languages", None) or []:
            if isinstance(lang, bytes):
                lang = lang.decode("utf-8", "ignore")
            pieces.append(str(lang))
        blob = " ".join(pieces).lower()

        if "en-us" in blob or "en_us" in blob:
            score = 3
        elif "en-gb" in blob or "en_gb" in blob:
            score = 2
        elif (
            "english" in blob
            or "en-" in blob
            or "en_" in blob
            or f"{language}-" in blob
            or f"{language}_" in blob
        ):
            score = 1
        else:
            continue

        if score > best_score:
            best = voice
            best_score = score

    return best


def pick_sapi_voice(voice):
    """Return the best English SAPI voice token, or ``None``."""
    try:
        tokens = voice.GetVoices()
    except Exception:
        return None

    best = None
    best_score = 0
    for token in tokens:
        try:
            description = token.GetDescription()
        except Exception:
            continue
        lower = description.lower()
        if "en-us" in lower or "united states" in lower:
            score = 3
        elif (
            "en-gb" in lower
            or "great britain" in lower
            or "united kingdom" in lower
        ):
            score = 2
        elif "english" in lower or "en-" in lower:
            score = 1
        else:
            continue
        if score > best_score:
            best = token
            best_score = score
    return best


def expected_speech_seconds(message: str, wpm: float) -> float:
    words = max(1, len(message.split()))
    return max(0.6, words / max(60.0, float(wpm)) * 60.0)


class SapiBackend:
    """Windows SAPI voice that can speak repeatedly without restarting."""

    def __init__(self, profile, metrics):
        self.profile = profile
        self.metrics = metrics
        self.voice = None
        self._comtypes = None
        self._com_initialized = False

    def start(self) -> None:
        import comtypes  # noqa: PLC0415 - Windows-only backend
        import comtypes.client  # noqa: PLC0415

        self._comtypes = comtypes
        comtypes.CoInitialize()
        self._com_initialized = True

        try:
            self.voice = comtypes.client.CreateObject("SAPI.SpVoice")
        except Exception:
            self.stop()
            raise

        self.voice.Volume = int(
            max(0.0, min(1.0, float(self.profile.tts_volume))) * 100
        )
        # SAPI rate is -10..10; 0 is the normal rate.
        rate = int(round((float(self.profile.tts_wpm) - 175.0) / 25.0))
        self.voice.Rate = max(-10, min(10, rate))

        token = pick_sapi_voice(self.voice)
        if token is not None:
            self.voice.Voice = token
            log.info(
                "TTS backend: Windows SAPI; voice: %s",
                token.GetDescription(),
            )
        else:
            log.warning(
                "TTS backend: Windows SAPI; no English voice found, "
                "using the default"
            )

    def speak(self, message: str) -> float:
        if self.voice is None:
            raise RuntimeError("SAPI voice is not initialized")
        start = time.monotonic()
        self.voice.Speak(message)
        return time.monotonic() - start

    def stop(self) -> None:
        self.voice = None
        if self._com_initialized and self._comtypes is not None:
            try:
                self._comtypes.CoUninitialize()
            except Exception:
                pass
            self._com_initialized = False


class Pyttsx3Backend:
    """Fallback backend.

    pyttsx3 on Windows can only speak once per engine instance, so a fresh
    engine is created for every utterance.
    """

    def __init__(self, profile, metrics):
        self.profile = profile
        self.metrics = metrics
        self._voice_logged = False

    def start(self) -> None:
        pass

    def speak(self, message: str) -> float:
        import pyttsx3  # noqa: PLC0415 - fallback backend

        engine = pyttsx3.init()
        try:
            engine.setProperty("rate", int(self.profile.tts_wpm))
            engine.setProperty("volume", float(self.profile.tts_volume))

            voice = pick_english_voice(engine, self.profile.tts_language)
            if voice is not None:
                engine.setProperty("voice", voice.id)
                if not self._voice_logged:
                    log.info(
                        "TTS backend: pyttsx3; voice: %s (%s)",
                        voice.name,
                        getattr(voice, "id", ""),
                    )
                    self._voice_logged = True
            elif not self._voice_logged:
                log.warning(
                    "No English TTS voice found for language %r; "
                    "using the engine default",
                    self.profile.tts_language,
                )
                self._voice_logged = True

            start = time.monotonic()
            engine.say(message)
            engine.runAndWait()
            return time.monotonic() - start
        finally:
            try:
                engine.stop()
            except Exception:
                pass

    def stop(self) -> None:
        pass


class SpeechEngine:
    def __init__(self, profile, metrics):
        self.profile = profile
        self.metrics = metrics

        self._pending: Optional[Pending] = None
        self._pending_priority = -1
        self._speaking = False
        self._current_priority = -1
        self._interrupt = False
        self._stop = threading.Event()
        self._cv = threading.Condition()
        self._thread = threading.Thread(target=self._run, name="tts", daemon=True)
        self._native = None
        self._started = False

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self.profile.tts_mode == "off":
            return
        if not self._started:
            self._thread.start()
            self._started = True

    def stop(self) -> None:
        with self._cv:
            self._stop.set()
            self._cv.notify_all()
        if self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def say(
        self,
        message: str,
        key: Optional[str] = None,
        priority: int = 1,
        frame_ts: Optional[float] = None,
    ) -> bool:
        if self.profile.tts_mode == "off":
            self.metrics.incr("tts_disabled")
            return False

        with self._cv:
            # Do not queue general narration behind a higher-priority warning.
            if self._speaking and priority < self._current_priority:
                self.metrics.incr("tts_dropped_low_priority")
                log.debug("TTS dropped low priority: %s", message)
                return False

            if self._pending is not None and priority <= self._pending_priority:
                self.metrics.incr("tts_dropped")
                log.debug("TTS dropped pending: %s", message)
                return False

            self._pending = (message, priority, frame_ts, time.monotonic())
            self._pending_priority = priority

            # A newer alert of equal or higher priority replaces the current
            # utterance: stale scene descriptions are less useful than the
            # latest observation.
            if self._speaking and priority >= self._current_priority:
                self._interrupt = True

            self._cv.notify()
            return True

    # ------------------------------------------------------------------
    # worker
    # ------------------------------------------------------------------

    def _run(self) -> None:
        try:
            while True:
                with self._cv:
                    while self._pending is None and not self._stop.is_set():
                        self._cv.wait(0.2)
                    if self._stop.is_set():
                        break

                    message, priority, frame_ts, enqueued_at = self._pending
                    self._pending = None
                    self._pending_priority = -1
                    self._speaking = True
                    self._current_priority = priority
                    self._interrupt = False

                try:
                    self._speak_one(message, priority, frame_ts, enqueued_at)
                except Exception as exc:  # keep the audio thread alive
                    log.error("Speech error: %s", exc)
                    self.metrics.incr("tts_errors")
                finally:
                    with self._cv:
                        self._speaking = False
                        self._current_priority = -1
                        self._interrupt = False
        finally:
            if self._native is not None:
                try:
                    self._native.stop()
                except Exception as exc:
                    log.warning("TTS backend shutdown error: %s", exc)

    def _speak_one(
        self,
        message: str,
        priority: int,
        frame_ts: Optional[float],
        enqueued_at: float,
    ) -> None:
        if self.profile.tts_mode == "stub":
            self._speak_stub(message, frame_ts, enqueued_at)
        elif self.profile.tts_mode == "native":
            self._speak_native(message, frame_ts, enqueued_at)
        else:
            return

    def _speak_stub(
        self,
        message: str,
        frame_ts: Optional[float],
        enqueued_at: float,
    ) -> None:
        if not self._wait(self.profile.tts_start_latency):
            self.metrics.incr("tts_interrupted")
            return

        log.debug("TTS stub: %s", message)
        start = time.monotonic()
        self._record_start(start, frame_ts, enqueued_at)

        words = max(1, len(message.split()))
        duration = max(0.6, words / max(self.profile.tts_wpm, 60.0) * 60.0)
        completed = self._wait(duration)

        if not completed:
            self.metrics.incr("tts_interrupted")

        self.metrics.record("tts_duration_ms", (time.monotonic() - start) * 1000.0)
        self.metrics.incr("tts_spoken")

    def _get_native_backend(self):
        if self._native is not None:
            return self._native

        if os.name == "nt":
            try:
                backend = SapiBackend(self.profile, self.metrics)
                backend.start()
                self._native = backend
                return backend
            except Exception as exc:
                log.warning(
                    "Windows SAPI TTS unavailable (%s); falling back to pyttsx3",
                    exc,
                )

        backend = Pyttsx3Backend(self.profile, self.metrics)
        backend.start()
        self._native = backend
        return backend

    def _speak_native(
        self,
        message: str,
        frame_ts: Optional[float],
        enqueued_at: float,
    ) -> None:
        start = time.monotonic()
        try:
            backend = self._get_native_backend()
        except Exception as exc:
            log.error("Could not initialize TTS backend: %s", exc)
            self.metrics.incr("tts_errors")
            return

        self._record_start(start, frame_ts, enqueued_at)
        log.info("TTS speaking: %s", message)

        try:
            duration = backend.speak(message)
        except Exception as exc:
            log.error("Speech error: %s", exc)
            self.metrics.incr("tts_errors")
            return

        expected = expected_speech_seconds(message, self.profile.tts_wpm)
        too_short = expected >= 0.5 and duration < expected * 0.35

        if too_short:
            log.warning(
                "TTS returned after %.2fs (expected about %.2fs); retrying",
                duration,
                expected,
            )
            self.metrics.incr("tts_retries")
            try:
                if isinstance(backend, SapiBackend):
                    retry = Pyttsx3Backend(self.profile, self.metrics)
                    retry.start()
                    retry_duration = retry.speak(message)
                    retry.stop()
                else:
                    retry_duration = backend.speak(message)
                duration = max(duration, retry_duration)
                too_short = duration < expected * 0.35
            except Exception as exc:
                log.error("TTS retry failed: %s", exc)
                self.metrics.incr("tts_errors")

        self.metrics.record("tts_duration_ms", duration * 1000.0)

        if too_short:
            log.error(
                "TTS produced no audible speech after retry (%.2fs)", duration
            )
            self.metrics.incr("tts_silent_failures")
        else:
            self.metrics.incr("tts_spoken")
            log.info("TTS spoke: %s (%.2fs)", message, duration)

    def _record_start(
        self,
        start: float,
        frame_ts: Optional[float],
        enqueued_at: float,
    ) -> None:
        self.metrics.record("tts_start_latency_ms", (start - enqueued_at) * 1000.0)
        if frame_ts is not None:
            self.metrics.record("camera_to_alert_ms", (start - frame_ts) * 1000.0)

    def _wait(self, seconds: float) -> bool:
        """Sleep in small slices so a higher-priority message can interrupt."""
        deadline = time.monotonic() + max(0.0, seconds)
        while True:
            with self._cv:
                if self._stop.is_set() or self._interrupt:
                    return False
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return True
                self._cv.wait(min(0.02, remaining))
