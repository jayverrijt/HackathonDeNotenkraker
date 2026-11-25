import unittest

import numpy as np

from config import Profile
from src.alerts import AlertEngine


class FakeMetrics:
    def __init__(self):
        self.counters = {}
        self.gauges = {}

    def incr(self, name, amount=1):
        self.counters[name] = self.counters.get(name, 0) + amount

    def record(self, name, value):
        pass

    def gauge(self, name, value):
        self.gauges[name] = value


class FakeSpeech:
    def __init__(self):
        self.calls = []

    def say(self, message, key=None, priority=1, frame_ts=None):
        self.calls.append(
            {
                "message": message,
                "key": key,
                "priority": priority,
                "frame_ts": frame_ts,
            }
        )
        return True


class AlertTests(unittest.TestCase):
    def make_engine(self):
        profile = Profile(
            name="test",
            centre_left=0.35,
            centre_right=0.65,
            lower_region_top=0.55,
            alert_cooldown=5.0,
            close_persist_frames=99,
            close_immediate_bottom=1.1,
            close_immediate_area=1.0,
        )
        speech = FakeSpeech()
        metrics = FakeMetrics()
        return AlertEngine(profile, speech, metrics), speech, metrics

    def test_central_person_is_announced_once(self):
        engine, speech, metrics = self.make_engine()
        detection = {
            "name": "person",
            "confidence": 0.9,
            "box": [40, 40, 60, 100],
            "track_id": 1,
        }

        engine.generate([detection], width=100, height=100, frame_ts=1.0)
        engine.generate([detection], width=100, height=100, frame_ts=1.1)

        self.assertEqual(len(speech.calls), 1)
        self.assertEqual(speech.calls[0]["message"], "There is a person in front of you.")
        self.assertEqual(speech.calls[0]["priority"], 2)
        self.assertEqual(metrics.counters["alerts_suppressed_cooldown"], 1)

    def test_lower_obstacle_is_announced(self):
        engine, speech, _ = self.make_engine()
        detection = {
            "name": "bench",
            "confidence": 0.8,
            "box": [0, 60, 20, 100],
            "track_id": 7,
        }

        engine.generate([detection], width=100, height=100, frame_ts=1.0)

        self.assertEqual(len(speech.calls), 1)
        self.assertEqual(
            speech.calls[0]["message"],
            "There is a bench to your left.",
        )
        self.assertEqual(speech.calls[0]["key"], "bench_left_7")

    def test_upper_obstacle_is_not_announced(self):
        engine, speech, _ = self.make_engine()
        detection = {
            "name": "bench",
            "confidence": 0.8,
            "box": [0, 10, 20, 40],
            "track_id": 7,
        }

        engine.generate([detection], width=100, height=100, frame_ts=1.0)
        self.assertEqual(speech.calls, [])

    def test_group_of_people(self):
        engine, speech, _ = self.make_engine()
        detections = [
            {
                "name": "person",
                "confidence": 0.9,
                "box": [40, 40, 60, 100],
                "track_id": i,
            }
            for i in range(3)
        ]

        engine.generate(detections, width=100, height=100, frame_ts=1.0)

        self.assertEqual(len(speech.calls), 1)
        self.assertEqual(
            speech.calls[0]["message"],
            "There are several people in front of you.",
        )

    def test_close_object_warns_after_persistence(self):
        profile = Profile(
            name="test",
            centre_left=0.35,
            centre_right=0.65,
            lower_region_top=0.55,
            alert_cooldown=5.0,
            close_persist_frames=2,
            close_bottom_ratio=0.75,
            close_area_ratio=0.03,
            close_immediate_bottom=1.1,
            close_immediate_area=1.0,
        )
        speech = FakeSpeech()
        metrics = FakeMetrics()
        engine = AlertEngine(profile, speech, metrics)
        detection = {
            "name": "bench",
            "confidence": 0.9,
            "box": [40, 50, 60, 85],
            "track_id": 7,
        }

        engine.generate([detection], width=100, height=100, frame_ts=1.0)
        speech.calls.clear()  # remove the generic first-frame announcement
        engine.generate([detection], width=100, height=100, frame_ts=1.1)

        self.assertEqual(len(speech.calls), 1)
        self.assertEqual(speech.calls[0]["message"], "There is a bench close in front of you.")
        self.assertEqual(speech.calls[0]["priority"], 3)
        self.assertEqual(metrics.counters.get("close_warnings"), 1)

    def test_very_close_object_warns_immediately(self):
        profile = Profile(
            name="test",
            centre_left=0.35,
            centre_right=0.65,
            lower_region_top=0.55,
            close_persist_frames=2,
        )
        speech = FakeSpeech()
        metrics = FakeMetrics()
        engine = AlertEngine(profile, speech, metrics)
        detection = {
            "name": "bench",
            "confidence": 0.9,
            "box": [40, 40, 60, 100],
            "track_id": 8,
            "obstacle": True,
        }

        engine.generate([detection], width=100, height=100, frame_ts=1.0)

        self.assertEqual(len(speech.calls), 1)
        self.assertEqual(speech.calls[0]["message"], "There is a bench close in front of you.")
        self.assertEqual(metrics.counters.get("close_warnings"), 1)

    def test_curb_warning_integration(self):
        engine, speech, metrics = self.make_engine()
        names = {0: "road", 1: "sidewalk", 10: "sky"}
        mask = np.full((180, 320), 10, dtype=np.uint8)
        mask[153:180, 96:224] = 1
        mask[90:153, 96:224] = 0

        observation = engine.generate_curb(mask, names, frame_ts=1.0)

        self.assertIsNotNone(observation)
        self.assertEqual(len(speech.calls), 1)
        self.assertEqual(
            speech.calls[0]["message"],
            "There may be a curb or road edge ahead.",
        )
        self.assertEqual(speech.calls[0]["priority"], 3)
        self.assertEqual(metrics.counters.get("curb_warnings"), 1)


if __name__ == "__main__":
    unittest.main()
