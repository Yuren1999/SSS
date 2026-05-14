import unittest

from spectra_sim.exceptions import ValidationError
from spectra_sim.models import (
    EnvironmentConfig,
    GasComponent,
    GasRole,
    SpectralAxisConfig,
    SynthesisConfig,
    WavenumberRange,
)


class ConfigModelsTestCase(unittest.TestCase):
    def test_environment_requires_physical_values(self) -> None:
        with self.assertRaises(ValidationError):
            EnvironmentConfig(pressure=0.0, temperature=296.0, path_length=10.0)

    def test_absent_variable_component_requires_zero_concentration(self) -> None:
        with self.assertRaises(ValidationError):
            GasComponent(name="CH4", concentration=2.0, presence=False)

    def test_synthesis_config_requires_correct_roles(self) -> None:
        spectral_axis = SpectralAxisConfig(WavenumberRange(6000.0, 6500.0), nu_step=0.1)
        environment = EnvironmentConfig(pressure=1.0, temperature=296.0, path_length=10.0)
        wrong_resident = GasComponent(name="H2O", concentration=10000.0, role=GasRole.VARIABLE)

        with self.assertRaises(ValidationError):
            SynthesisConfig(
                spectral_axis=spectral_axis,
                environment=environment,
                resident_gases=(wrong_resident,),
            )


if __name__ == "__main__":
    unittest.main()

