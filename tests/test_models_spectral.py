import unittest

from spectra_sim.exceptions import ValidationError
from spectra_sim.models import GasSpec, LineRecord, LineTable, SpectralAxisConfig, WavenumberRange


class SpectralModelsTestCase(unittest.TestCase):
    def test_wavenumber_range_requires_ascending_positive_bounds(self) -> None:
        spectral_range = WavenumberRange(6000.0, 6500.0)

        self.assertEqual(spectral_range.width, 500.0)
        self.assertTrue(spectral_range.contains(6200.0))

        with self.assertRaises(ValidationError):
            WavenumberRange(6500.0, 6000.0)

    def test_wavenumber_range_can_normalize_bounds(self) -> None:
        spectral_range = WavenumberRange.from_bounds(6500.0, 6000.0)

        self.assertEqual(spectral_range.nu_min, 6000.0)
        self.assertEqual(spectral_range.nu_max, 6500.0)

    def test_spectral_axis_rejects_step_larger_than_range(self) -> None:
        with self.assertRaises(ValidationError):
            SpectralAxisConfig(WavenumberRange(6000.0, 6001.0), nu_step=2.0)

    def test_line_table_rejects_records_outside_range(self) -> None:
        gas = GasSpec("CO2", 2)
        record = LineRecord(
            gas_name="CO2",
            wavenumber=6600.0,
            line_intensity=1.0,
            air_width=0.1,
            self_width=0.1,
            lower_state_energy=0.0,
            temperature_dependence=0.7,
            pressure_shift=0.0,
        )

        with self.assertRaises(ValidationError):
            LineTable(gas=gas, wavenumber_range=WavenumberRange(6000.0, 6500.0), records=(record,))


if __name__ == "__main__":
    unittest.main()

