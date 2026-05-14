import unittest

from spectra_sim.exceptions import ValidationError
from spectra_sim.models import EnvironmentConfig, GasComponent
from spectra_sim.validation import (
    validate_environment,
    validate_gas_component,
    validate_non_negative,
    validate_positive,
    validate_wavenumber_range,
)


class ValidationRulesTestCase(unittest.TestCase):
    def test_validate_positive(self) -> None:
        self.assertEqual(validate_positive(1.0, "压力"), 1.0)
        with self.assertRaises(ValidationError):
            validate_positive(0.0, "压力")

    def test_validate_non_negative(self) -> None:
        self.assertEqual(validate_non_negative(0.0, "浓度"), 0.0)
        with self.assertRaises(ValidationError):
            validate_non_negative(-1.0, "浓度")

    def test_validate_wavenumber_range(self) -> None:
        spectral_range = validate_wavenumber_range(6000.0, 6500.0)

        self.assertEqual(spectral_range.nu_min, 6000.0)

    def test_validate_environment_and_component(self) -> None:
        environment = EnvironmentConfig(pressure=1.0, temperature=296.0, path_length=10.0)
        component = GasComponent(name="CO2", concentration=420.0)

        self.assertIs(validate_environment(environment), environment)
        self.assertIs(validate_gas_component(component), component)


if __name__ == "__main__":
    unittest.main()

