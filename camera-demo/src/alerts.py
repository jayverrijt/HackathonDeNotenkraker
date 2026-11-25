"""Spatial analysis and alert generation."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

from .messages import there_are_people, there_is_object
from .proximity import CloseObjectTracker, CurbDetector, SceneDescriber, detection_key


def get_image_position(box, width, height, profile):
    """Return ``(horizontal, lower)`` for a bounding box.

    Horizontal is ``left``/``centre``/``right``; lower means the bottom of the
    box is inside the lower image region.  This is image space, not a distance.
    """
    x1, _, x2, y2 = box
    cx = (x1 + x2) / 2.0 / float(width)
    bottom = y2 / float(height)

    if cx < profile.centre_left:
        horizontal = "left"
    elif cx > profile.centre_right:
        horizontal = "right"
    else:
        horizontal = "centre"

    return horizontal, bottom > profile.lower_region_top


class AlertEngine:
    """Turn detections into concise, rate-limited spoken messages."""

    def __init__(self, profile, speech, metrics):
        self.profile = profile
        self.speech = speech
        self.metrics = metrics
        self.last_alerts = {}
        self.last_global_alert = 0.0
        self.last_safety_alert = 0.0
        self.close_tracker = CloseObjectTracker()
        self.curb_detector = CurbDetector(profile)
        self.scene_describer = SceneDescriber(profile)

    def _cooldown_ok(self, key: str, priority: int, cooldown=None) -> bool:
        now = time.monotonic()
        cooldown = self.profile.alert_cooldown if cooldown is None else cooldown

        if now - self.last_alerts.get(key, 0.0) < cooldown:
            self.metrics.incr("alerts_suppressed_cooldown")
            return False

        # A global cooldown stops a queue of unrelated objects from turning
        # into constant narration.  High-priority safety warnings bypass it.
        if (
            self.profile.alert_global_cooldown
            and priority == 1
            and now - self.last_global_alert < self.profile.alert_global_cooldown
        ):
            self.metrics.incr("alerts_suppressed_global")
            return False

        self.last_alerts[key] = now
        return True

    def _say(
        self,
        message: str,
        key: str,
        priority: int,
        frame_ts: float,
        cooldown=None,
    ) -> bool:
        if not self._cooldown_ok(key, priority, cooldown=cooldown):
            return False

        self.metrics.incr("alerts_generated")
        queued = self.speech.say(
            message,
            key=key,
            priority=priority,
            frame_ts=frame_ts,
        )
        if queued:
            logger.info(
                "Audio alert queued: %s | key=%s | priority=%s",
                message,
                key,
                priority,
            )
        else:
            logger.debug(
                "Audio alert dropped by TTS: %s | key=%s | priority=%s",
                message,
                key,
                priority,
            )
        if queued:
            now = time.monotonic()
            self.last_global_alert = now
            if priority >= 2:
                self.last_safety_alert = now
        else:
            self.metrics.incr("alerts_not_queued")
        return bool(queued)

    # ------------------------------------------------------------------
    # detection alerts
    # ------------------------------------------------------------------

    def generate(self, detections, width: int, height: int, frame_ts: float) -> None:
        people = []
        obstacles = []

        for detection in detections:
            horizontal, lower = get_image_position(
                detection["box"], width, height, self.profile
            )
            detection["position"] = horizontal
            detection["lower"] = lower

            if detection["name"] == "person":
                people.append(detection)
            elif detection.get("obstacle", True):
                obstacles.append(detection)

        # Safety-critical: a large object low in the central walking band.
        close_objects = self.close_tracker.update(
            detections, width, height, self.profile
        )
        if close_objects:
            obj = close_objects[0]
            if obj["name"] == "person":
                message = there_are_people(
                    1,
                    obj["position"],
                    obj["lower"],
                    close=True,
                )
            else:
                message = there_is_object(
                    obj["name"],
                    obj["position"],
                    obj["lower"],
                    close=True,
                )
            if self._say(
                message,
                key=f"close_{detection_key(obj)}",
                priority=3,
                frame_ts=frame_ts,
                cooldown=self.profile.close_cooldown,
            ):
                self.metrics.incr("close_warnings")
            # Do not also narrate general scene objects in the same cycle.
            return

        central_people = [
            p for p in people if p["position"] == "centre" and p["lower"]
        ]

        if central_people:
            self._say(
                there_are_people(len(central_people), "centre", True),
                "group_people" if len(central_people) >= 2 else "person_centre",
                priority=2,
                frame_ts=frame_ts,
            )
            # People are higher priority; do not also narrate an object.
            return

        lower_obstacles = [obj for obj in obstacles if obj["lower"]]
        if not lower_obstacles:
            return

        def score(obj):
            x1, _, x2, y2 = obj["box"]
            cx = (x1 + x2) / 2.0 / float(width)
            # Prefer objects that are low in the image and near the centre,
            # then higher confidence.
            return (y2 / float(height), -abs(cx - 0.5), obj["confidence"])

        for obj in sorted(lower_obstacles, key=score, reverse=True):
            position = obj["position"]
            if self._say(
                there_is_object(obj["name"], position, obj["lower"]),
                key=f"{obj['name']}_{position}_{obj['track_id']}",
                priority=1,
                frame_ts=frame_ts,
            ):
                break

    # ------------------------------------------------------------------
    # curb alerts
    # ------------------------------------------------------------------

    def generate_curb(self, mask, class_names, frame_ts: float):
        observation = self.curb_detector.analyze(mask, class_names)
        if not observation:
            return None

        self.metrics.gauge(
            "last_curb_confidence", observation.get("confidence", 0.0)
        )
        if self._say(
            observation["message"],
            key=observation["key"],
            priority=3,
            frame_ts=frame_ts,
            cooldown=self.profile.curb_cooldown,
        ):
            self.metrics.incr("curb_warnings")

        return observation

    # ------------------------------------------------------------------
    # low-priority scene descriptions
    # ------------------------------------------------------------------

    def generate_scene(self, mask, class_names, frame_ts: float):
        if (
            time.monotonic() - self.last_safety_alert
            < self.profile.scene_quiet_after_alert
        ):
            return None

        observation = self.scene_describer.analyze(mask, class_names)
        if not observation:
            return None

        self.metrics.gauge(
            "last_scene_confidence", observation.get("confidence", 0.0)
        )
        if self._say(
            observation["message"],
            key=observation["key"],
            priority=0,
            frame_ts=frame_ts,
            cooldown=self.profile.scene_cooldown,
        ):
            self.metrics.incr("scene_descriptions")

        return observation
