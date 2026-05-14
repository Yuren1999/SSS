import unittest

from spectra_sim.exceptions import SynthesisError
from spectra_sim.models import (
    EnvironmentConfig,
    GasComponent,
    GasRole,
    GasSpec,
    LineRecord,
    LineTable,
    SpectralAxisConfig,
    SynthesisConfig,
    WavenumberRange,
)
from spectra_sim.services import LocalSynthesisService, SynthesisService


class FakeLineDatabaseService:
    def __init__(self) -> None:
        self.search_calls = []

    def list_gases(self):
        return [GasSpec("CO2", 2)]

    def get_coverage(self, gas_name):
        return [WavenumberRange(6000.0, 6001.0)]

    def check_coverage(self, gas_names, requested_range):
        return []

    def search_lines(self, gas_name, requested_range):
        self.search_calls.append((gas_name, requested_range))
        return LineTable(
            gas=GasSpec(gas_name, 2),
            wavenumber_range=requested_range,
            records=(
                LineRecord(
                    gas_name=gas_name,
                    wavenumber=6000.5,
                    line_intensity=1.0e-20,
                    air_width=0.08,
                    self_width=0.05,
                    lower_state_energy=10.0,
                    temperature_dependence=0.7,
                    pressure_shift=0.0,
                ),
            ),
        )


def make_config(*components: GasComponent) -> SynthesisConfig:
    resident = tuple(component for component in components if component.role is GasRole.RESIDENT)
    variable = tuple(component for component in components if component.role is GasRole.VARIABLE)
    return SynthesisConfig(
        spectral_axis=SpectralAxisConfig(WavenumberRange(6000.0, 6001.0), nu_step=0.1),
        environment=EnvironmentConfig(pressure=1.0, temperature=296.0, path_length=10.0),
        resident_gases=resident,
        variable_gases=variable,
    )


class LocalSynthesisServiceTestCase(unittest.TestCase):
    def test_service_implements_synthesis_protocol(self) -> None:
        service = LocalSynthesisService(FakeLineDatabaseService())

        self.assertIsInstance(service, SynthesisService)

    def test_synthesize_single_reads_lines_from_database_service(self) -> None:
        database = FakeLineDatabaseService()
        service = LocalSynthesisService(database)
        config = make_config(GasComponent("CO2", 400.0, role=GasRole.RESIDENT))

        record = service.synthesize_single(config)

        self.assertEqual(database.search_calls[0][0], "CO2")
        self.assertEqual(record.metadata["line_count"], 1)
        self.assertEqual(len(record.wavenumber), len(record.clean_absorbance))
        self.assertIn("CO2", record.labels.resident_concentrations)

    def test_synthesize_single_rejects_multiple_present_components(self) -> None:
        service = LocalSynthesisService(FakeLineDatabaseService())
        config = make_config(
            GasComponent("CO2", 400.0, role=GasRole.RESIDENT),
            GasComponent("CH4", 2.0, role=GasRole.VARIABLE),
        )

        with self.assertRaises(SynthesisError):
            service.synthesize_single(config)


if __name__ == "__main__":
    unittest.main()

