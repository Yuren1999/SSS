import unittest

from spectra_sim.database.coverage import covers_range, merge_ranges, missing_ranges
from spectra_sim.models import WavenumberRange


class CoverageUtilsTestCase(unittest.TestCase):
    def test_merge_ranges_merges_overlapping_ranges(self) -> None:
        merged = merge_ranges(
            [
                WavenumberRange(6200.0, 6300.0),
                WavenumberRange(6000.0, 6250.0),
                WavenumberRange(6400.0, 6500.0),
            ]
        )

        self.assertEqual(merged, (WavenumberRange(6000.0, 6300.0), WavenumberRange(6400.0, 6500.0)))

    def test_missing_ranges_returns_all_gaps(self) -> None:
        gaps = missing_ranges(
            [
                WavenumberRange(6000.0, 6100.0),
                WavenumberRange(6200.0, 6300.0),
            ],
            WavenumberRange(6000.0, 6400.0),
        )

        self.assertEqual(gaps, (WavenumberRange(6100.0, 6200.0), WavenumberRange(6300.0, 6400.0)))

    def test_covers_range_detects_complete_coverage(self) -> None:
        self.assertTrue(covers_range([WavenumberRange(6000.0, 6500.0)], WavenumberRange(6100.0, 6400.0)))
        self.assertFalse(covers_range([WavenumberRange(6000.0, 6200.0)], WavenumberRange(6100.0, 6400.0)))


if __name__ == "__main__":
    unittest.main()

