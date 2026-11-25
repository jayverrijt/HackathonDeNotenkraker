import unittest

from config import Profile
from src.alerts import get_image_position


class SpatialTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            name="test",
            centre_left=0.35,
            centre_right=0.65,
            lower_region_top=0.55,
        )

    def test_left_centre_right(self):
        width = height = 100
        self.assertEqual(
            get_image_position([0, 10, 20, 50], width, height, self.profile),
            ("left", False),
        )
        self.assertEqual(
            get_image_position([40, 10, 60, 50], width, height, self.profile),
            ("centre", False),
        )
        self.assertEqual(
            get_image_position([80, 10, 100, 50], width, height, self.profile),
            ("right", False),
        )

    def test_lower_region_uses_box_bottom(self):
        width = height = 100
        _, lower = get_image_position([40, 10, 60, 60], width, height, self.profile)
        self.assertTrue(lower)

        _, not_lower = get_image_position([40, 10, 60, 50], width, height, self.profile)
        self.assertFalse(not_lower)


if __name__ == "__main__":
    unittest.main()
