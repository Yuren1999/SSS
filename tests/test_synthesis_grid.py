import unittest

from spectra_sim.models import SpectralAxisConfig, WavenumberRange
from spectra_sim.synthesis import build_wavenumber_grid


class SynthesisGridTestCase(unittest.TestCase):
    def test_build_wavenumber_grid_includes_end_when_needed(self) -> None:
        grid = build_wavenumber_grid(SpectralAxisConfig(WavenumberRange(6000.0, 6000.25), nu_step=0.1))

        self.assertEqual(grid[0], 6000.0)
        self.assertEqual(grid[-1], 6000.25)
        self.assertEqual(len(grid), 4)

    def test_build_wavenumber_grid_uses_regular_step(self) -> None:
        grid = build_wavenumber_grid(SpectralAxisConfig(WavenumberRange(6000.0, 6000.3), nu_step=0.1))

        self.assertEqual(grid.tolist(), [6000.0, 6000.1, 6000.2, 6000.3])


if __name__ == "__main__":
    unittest.main()

