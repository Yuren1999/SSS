import unittest

import numpy as np

from spectra_sim.models import BaselineConfig, BaselineType, NoiseConfig, NoiseType
from spectra_sim.synthesis import evaluate_baseline, generate_noise


class PerturbationSynthesisTestCase(unittest.TestCase):
    def test_polynomial_baseline_uses_centered_axis(self) -> None:
        wavenumber = np.array([6000.0, 6000.5, 6001.0])
        baseline = evaluate_baseline(
            wavenumber,
            BaselineConfig(
                baseline_type=BaselineType.POLYNOMIAL,
                parameters={"c0": 1.0, "c1": 0.5, "c2": 0.25},
            ),
        )

        np.testing.assert_allclose(baseline, np.array([0.75, 1.0, 1.75]))

    def test_gaussian_noise_is_reproducible_with_seed(self) -> None:
        signal = np.ones(8)
        config = NoiseConfig(noise_type=NoiseType.GAUSSIAN, parameters={"std": 0.01}, seed=123)

        first = generate_noise(signal, config)
        second = generate_noise(signal, config)

        np.testing.assert_allclose(first, second)

    def test_random_smooth_baseline_is_reproducible_with_seed(self) -> None:
        wavenumber = np.linspace(6000.0, 6001.0, 11)
        config = BaselineConfig(
            baseline_type=BaselineType.RANDOM_SMOOTH,
            parameters={"amplitude": 0.01, "anchor_count": 4},
        )

        first = evaluate_baseline(wavenumber, config, seed=99)
        second = evaluate_baseline(wavenumber, config, seed=99)

        np.testing.assert_allclose(first, second)


if __name__ == "__main__":
    unittest.main()
