import time
import unittest

from src.limits import Slowdown


class SlowdownTests(unittest.TestCase):
    def test_factor_one_does_not_sleep(self):
        slowdown = Slowdown(factor=1.0)
        start = time.perf_counter()
        result = slowdown.inflate(0.01)
        elapsed = time.perf_counter() - start

        self.assertAlmostEqual(result, 0.01, places=6)
        self.assertLess(elapsed, 0.02)

    def test_factor_two_inflates_wall_time(self):
        slowdown = Slowdown(factor=2.0)
        start = time.perf_counter()
        time.sleep(0.01)  # stand-in for a 10 ms inference
        compute = time.perf_counter() - start
        result = slowdown.inflate(compute)
        elapsed = time.perf_counter() - start

        self.assertAlmostEqual(result, compute * 2.0, places=6)
        self.assertGreaterEqual(elapsed, compute * 2.0 - 0.002)

    def test_thermal_factor_applies_immediately_when_window_is_zero(self):
        slowdown = Slowdown(factor=2.0, thermal_after_s=0.0, thermal_factor=1.0)
        self.assertAlmostEqual(slowdown.current_factor(), 2.0)

    def test_thermal_factor_activates_after_window(self):
        slowdown = Slowdown(factor=2.0, thermal_after_s=0.001, thermal_factor=1.5)
        time.sleep(0.003)
        self.assertAlmostEqual(slowdown.current_factor(), 3.0)
        self.assertTrue(slowdown.thermal_active)


if __name__ == "__main__":
    unittest.main()
