import unittest

import numpy as np

from config import Profile
from src.proximity import (
    CloseObjectTracker,
    CurbDetector,
    SceneDescriber,
    close_score,
    detection_key,
)


class CloseObjectTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(name="test")

    def test_large_lower_centre_box_is_close(self):
        det = {
            "name": "bench",
            "box": [250, 250, 390, 350],
            "track_id": 1,
            "position": "centre",
        }
        self.assertIsNotNone(close_score(det, width=640, height=360, profile=self.profile))

    def test_high_box_is_not_close(self):
        det = {
            "name": "bench",
            "box": [250, 50, 390, 150],
            "track_id": 1,
            "position": "centre",
        }
        self.assertIsNone(close_score(det, width=640, height=360, profile=self.profile))

    def test_side_box_is_not_close(self):
        det = {
            "name": "bench",
            "box": [0, 250, 100, 350],
            "track_id": 1,
            "position": "left",
        }
        self.assertIsNone(close_score(det, width=640, height=360, profile=self.profile))

    def test_persistence_requires_two_frames(self):
        tracker = CloseObjectTracker()
        det = {
            "name": "person",
            "box": [250, 250, 390, 350],
            "track_id": 7,
            "position": "centre",
        }

        first = tracker.update([det], 640, 360, self.profile, now=1.0)
        second = tracker.update([det], 640, 360, self.profile, now=1.2)

        self.assertEqual(first, [])
        self.assertEqual(len(second), 1)
        self.assertEqual(detection_key(det), "person_7")


class CurbTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(name="test")
        self.names = {0: "road", 1: "sidewalk", 10: "sky"}

    def test_sidewalk_bottom_and_road_above_warns_ahead(self):
        mask = np.full((180, 320), 10, dtype=np.uint8)
        # Bottom band (85-100%) is sidewalk; a road band sits above it.
        mask[153:180, 96:224] = 1
        mask[90:153, 96:224] = 0

        observation = CurbDetector(self.profile).analyze(mask, self.names)

        self.assertIsNotNone(observation)
        self.assertEqual(observation["key"], "curb_ahead")
        self.assertIn("ahead", observation["message"])

    def test_all_sidewalk_does_not_warn(self):
        mask = np.full((180, 320), 1, dtype=np.uint8)
        self.assertIsNone(CurbDetector(self.profile).analyze(mask, self.names))

    def test_all_road_does_not_warn(self):
        mask = np.full((180, 320), 0, dtype=np.uint8)
        self.assertIsNone(CurbDetector(self.profile).analyze(mask, self.names))

    def test_lateral_curb_warns_left(self):
        mask = np.full((180, 320), 10, dtype=np.uint8)
        # Near lower band, left zone: sidewalk next to road.
        mask[126:180, 0:70] = 1
        mask[126:180, 70:105] = 0

        observation = CurbDetector(self.profile).analyze(mask, self.names)

        self.assertIsNotNone(observation)
        self.assertEqual(observation["key"], "curb_left")
        self.assertEqual(
            observation["message"],
            "There may be a curb on your left.",
        )


class SceneTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(name="test")
        self.names = {
            0: "road",
            1: "sidewalk",
            2: "building",
            8: "vegetation",
            10: "sky",
        }

    def test_vegetation_left(self):
        mask = np.full((180, 320), 10, dtype=np.uint8)
        mask[9:153, 0:105] = 8

        observation = SceneDescriber(self.profile).analyze(mask, self.names)

        self.assertIsNotNone(observation)
        self.assertEqual(observation["key"], "scene_vegetation_left")
        self.assertEqual(
            observation["message"],
            "There are trees or plants to your left.",
        )

    def test_building_right(self):
        mask = np.full((180, 320), 10, dtype=np.uint8)
        mask[9:153, 211:320] = 2

        observation = SceneDescriber(self.profile).analyze(mask, self.names)

        self.assertIsNotNone(observation)
        self.assertEqual(observation["key"], "scene_building_right")
        self.assertEqual(
            observation["message"],
            "There is a building to your right.",
        )

    def test_no_scene(self):
        mask = np.full((180, 320), 10, dtype=np.uint8)
        self.assertIsNone(SceneDescriber(self.profile).analyze(mask, self.names))


if __name__ == "__main__":
    unittest.main()
