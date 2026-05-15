import unittest

from spectra_sim.batch import apply_parameter_overrides, expand_parameter_grid
from spectra_sim.exceptions import ValidationError
from spectra_sim.models import (
    EnvironmentConfig,
    GasComponent,
    GasRole,
    NoiseConfig,
    SpectralAxisConfig,
    SynthesisConfig,
    WavenumberRange,
)


def make_base_config() -> SynthesisConfig:
    return SynthesisConfig(
        spectral_axis=SpectralAxisConfig(WavenumberRange(6000.0, 6001.0), nu_step=0.1),
        environment=EnvironmentConfig(pressure=1.0, temperature=296.0, path_length=10.0),
        resident_gases=(GasComponent("CO2", 400.0, role=GasRole.RESIDENT),),
        variable_gases=(GasComponent("CH4", 1.0, role=GasRole.VARIABLE),),
        noise=NoiseConfig(seed=1),
    )


class BatchParameterExpansionTestCase(unittest.TestCase):
    def test_expand_parameter_grid_builds_cartesian_product(self) -> None:
        configs = expand_parameter_grid(
            {
                "base_config": make_base_config(),
                "grid": {
                    "environment.pressure": [0.8, 1.0],
                    "variable_gases.CH4.concentration": [1.0, 2.0],
                    "noise.seed": [11, 12],
                },
            }
        )

        self.assertEqual(len(configs), 8)
        self.assertEqual(configs[0].environment.pressure, 0.8)
        self.assertEqual(configs[-1].variable_gases[0].concentration, 2.0)
        self.assertEqual(configs[-1].noise.seed, 12)

    def test_apply_parameter_overrides_supports_nested_parameter_maps(self) -> None:
        config = apply_parameter_overrides(
            make_base_config(),
            {
                "noise.parameters.std": 0.01,
                "spectral_axis.wavenumber_range.nu_max": 6002.0,
            },
        )

        self.assertEqual(config.noise.parameters["std"], 0.01)
        self.assertEqual(config.spectral_axis.wavenumber_range.nu_max, 6002.0)

    def test_expand_parameter_grid_rejects_unknown_gas(self) -> None:
        with self.assertRaises(ValidationError):
            expand_parameter_grid(
                {
                    "base_config": make_base_config(),
                    "grid": {"variable_gases.N2O.concentration": [1.0]},
                }
            )


if __name__ == "__main__":
    unittest.main()
