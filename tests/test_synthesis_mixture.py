import unittest

import numpy as np

from spectra_sim.models import BaselineConfig, BaselineType, NoiseConfig, NoiseType
from spectra_sim.synthesis import combine_component_absorbances, synthesize_mixture_absorbance


class MixtureSynthesisTestCase(unittest.TestCase):
    def test_component_absorbances_are_summed(self) -> None:
        wavenumber = np.array([1.0, 2.0, 3.0])
        first = np.array([0.1, 0.2, 0.3])
        second = np.array([0.01, 0.02, 0.03])

        mixed = combine_component_absorbances(wavenumber, (first, second))

        np.testing.assert_allclose(mixed, np.array([0.11, 0.22, 0.33]))

    def test_final_absorbance_contains_clean_baseline_and_noise(self) -> None:
        wavenumber = np.array([6000.0, 6000.5, 6001.0])
        clean = np.array([0.1, 0.2, 0.3])
        baseline_config = BaselineConfig(
            baseline_type=BaselineType.CONSTANT,
            parameters={"offset": 0.01},
        )
        noise_config = NoiseConfig(noise_type=NoiseType.GAUSSIAN, parameters={"std": 0.0}, seed=1)

        result = synthesize_mixture_absorbance(wavenumber, (clean,), baseline_config, noise_config)

        np.testing.assert_allclose(result.clean_absorbance, clean)
        np.testing.assert_allclose(result.baseline, np.array([0.01, 0.01, 0.01]))
        np.testing.assert_allclose(result.noise, np.zeros(3))
        np.testing.assert_allclose(result.final_absorbance, clean + 0.01)
        np.testing.assert_allclose(result.transmittance, np.exp(-clean))


if __name__ == "__main__":
    unittest.main()
