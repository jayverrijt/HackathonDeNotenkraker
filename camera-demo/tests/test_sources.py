import argparse
import tempfile
import unittest
from pathlib import Path

import main
from config import Profile


def make_args(**overrides):
    values = {
        "source": None,
        "video": None,
        "camera": False,
        "start": 0.0,
        "loop": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class SourceResolutionTests(unittest.TestCase):
    def test_find_test_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            videos = root / "videos"
            videos.mkdir()
            expected = videos / "citywalk.mp4"
            expected.write_bytes(b"x")

            found = main.find_test_video(directories=(root, videos))
            self.assertEqual(found, expected)

    def test_find_test_video_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(main.find_test_video(directories=(Path(tmp),)))

    def test_explicit_source_wins(self):
        profile = Profile(name="test")
        source, start, loop, origin = main.resolve_source(
            make_args(source="0", start=12.0, loop=False),
            profile,
            test_video=Path("citywalk.mp4"),
        )

        self.assertEqual(source, 0)
        self.assertEqual(start, 0.0)
        self.assertFalse(loop)
        self.assertEqual(origin, "source")

    def test_video_alias_wins(self):
        profile = Profile(name="test")
        source, start, loop, origin = main.resolve_source(
            make_args(video="foo.mp4", start=5.0),
            profile,
            test_video=Path("citywalk.mp4"),
        )

        self.assertEqual(source, "foo.mp4")
        self.assertEqual(start, 5.0)
        self.assertTrue(loop)
        self.assertEqual(origin, "video")

    def test_camera_forces_camera(self):
        profile = Profile(name="test", camera_index=2)
        source, start, loop, origin = main.resolve_source(
            make_args(camera=True, start=10.0),
            profile,
            test_video=Path("citywalk.mp4"),
        )

        self.assertEqual(source, 2)
        self.assertEqual(start, 0.0)
        self.assertEqual(origin, "camera")

    def test_auto_uses_test_video(self):
        profile = Profile(name="test")
        source, start, loop, origin = main.resolve_source(
            make_args(start=7.0),
            profile,
            test_video=Path("citywalk.mp4"),
        )

        self.assertEqual(source, "citywalk.mp4")
        self.assertEqual(start, 7.0)
        self.assertEqual(origin, "auto-video")

    def test_camera_fallback(self):
        profile = Profile(name="test", camera_index=0)
        source, start, loop, origin = main.resolve_source(
            make_args(),
            profile,
            test_video=None,
        )

        self.assertEqual(source, 0)
        self.assertEqual(start, 0.0)
        self.assertEqual(origin, "camera-fallback")


if __name__ == "__main__":
    unittest.main()
