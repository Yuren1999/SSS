import unittest

import numpy as np

from spectra_sim.models import EnvironmentConfig, GasComponent, LineRecord
from spectra_sim.synthesis.absorbance import (
    concentration_to_fraction,
    path_length_to_cm,
    synthesize_single_gas_absorbance,
)


def make_record() -> LineRecord:
    return LineRecord(
        gas_name="CO2",
        wavenumber=6000.5,
        line_intensity=1.0e-20,
        air_width=0.08,
        self_width=0.05,
        lower_state_energy=10.0,
        temperature_dependence=0.7,
        pressure_shift=0.0,
    )


class AbsorbanceSynthesisTestCase(unittest.TestCase):
    def test_concentration_to_fraction_supports_ppm(self) -> None:
        self.assertAlmostEqual(concentration_to_fraction(GasComponent("CO2", 400.0)), 400.0e-6)

    def test_path_length_to_cm_supports_default_cm(self) -> None:
        self.assertEqual(path_length_to_cm(EnvironmentConfig(pressure=1.0, temperature=296.0, path_length=10.0)), 10.0)

    def test_absorbance_increases_with_concentration(self) -> None:
        wavenumber = np.linspace(6000.0, 6001.0, 101)
        environment = EnvironmentConfig(pressure=1.0, temperature=296.0, path_length=10.0)
        low = synthesize_single_gas_absorbance(
            wavenumber=wavenumber,
            records=(make_record(),),
            component=GasComponent("CO2", 100.0),
            environment=environment,
            nu_step=0.01,
        )
        high = synthesize_single_gas_absorbance(
            wavenumber=wavenumber,
            records=(make_record(),),
            component=GasComponent("CO2", 200.0),
            environment=environment,
            nu_step=0.01,
        )

        self.assertGreater(float(high.absorbance.max()), float(low.absorbance.max()))

    def test_zero_concentration_returns_unit_transmittance(self) -> None:
        wavenumber = np.linspace(6000.0, 6001.0, 101)
        result = synthesize_single_gas_absorbance(
            wavenumber=wavenumber,
            records=(make_record(),),
            component=GasComponent("CO2", 0.0),
            environment=EnvironmentConfig(pressure=1.0, temperature=296.0, path_length=10.0),
            nu_step=0.01,
        )

        self.assertTrue(np.all(result.absorbance == 0))
        self.assertTrue(np.all(result.transmittance == 1))


if __name__ == "__main__":
    unittest.main()

