import unittest

import numpy as np

from spectra_sim.exceptions import SynthesisError
from spectra_sim.models import (
    BaselineConfig,
    BaselineType,
    EnvironmentConfig,
    GasComponent,
    GasRole,
    GasSpec,
    LineRecord,
    LineTable,
    NoiseConfig,
    NoiseType,
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
        center = 6000.4 if gas_name == "CO2" else 6000.6
        return LineTable(
            gas=GasSpec(gas_name, 2),
            wavenumber_range=requested_range,
            records=(
                LineRecord(
                    gas_name=gas_name,
                    wavenumber=center,
                    line_intensity=1.0e-20,
                    air_width=0.08,
                    self_width=0.05,
                    lower_state_energy=10.0,
                    temperature_dependence=0.7,
                    pressure_shift=0.0,
                ),
            ),
        )


def make_config(
    *components: GasComponent,
    baseline: BaselineConfig | None = None,
    noise: NoiseConfig | None = None,
) -> SynthesisConfig:
    resident = tuple(component for component in components if component.role is GasRole.RESIDENT)
    variable = tuple(component for component in components if component.role is GasRole.VARIABLE)
    return SynthesisConfig(
        spectral_axis=SpectralAxisConfig(WavenumberRange(6000.0, 6001.0), nu_step=0.1),
        environment=EnvironmentConfig(pressure=1.0, temperature=296.0, path_length=10.0),
        resident_gases=resident,
        variable_gases=variable,
        baseline=baseline or BaselineConfig(),
        noise=noise or NoiseConfig(),
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

    def test_synthesize_mixture_sums_single_component_absorbance(self) -> None:
        service = LocalSynthesisService(FakeLineDatabaseService())
        co2 = GasComponent("CO2", 400.0, role=GasRole.RESIDENT)
        ch4 = GasComponent("CH4", 2.0, role=GasRole.VARIABLE)

        co2_record = service.synthesize_single(make_config(co2))
        ch4_record = service.synthesize_single(make_config(ch4))
        mixture_record = service.synthesize_mixture(make_config(co2, ch4))

        expected = np.array(co2_record.clean_absorbance) + np.array(ch4_record.clean_absorbance)
        np.testing.assert_allclose(mixture_record.clean_absorbance, expected)
        self.assertEqual(mixture_record.labels.resident_concentrations["CO2"], 400.0)
        self.assertEqual(mixture_record.labels.variable_presence["CH4"], 1)
        self.assertEqual(mixture_record.metadata["synthesis_mode"], "mixture")

    def test_synthesize_mixture_labels_absent_variable_without_line_search(self) -> None:
        database = FakeLineDatabaseService()
        service = LocalSynthesisService(database)
        config = make_config(
            GasComponent("CO2", 400.0, role=GasRole.RESIDENT),
            GasComponent("CH4", 0.0, role=GasRole.VARIABLE, presence=False),
        )

        record = service.synthesize_mixture(config)

        self.assertEqual([call[0] for call in database.search_calls], ["CO2"])
        self.assertEqual(record.labels.variable_presence["CH4"], 0)
        self.assertEqual(record.labels.variable_concentrations["CH4"], 0.0)

    def test_synthesize_mixture_reproducible_noise_and_baseline(self) -> None:
        service = LocalSynthesisService(FakeLineDatabaseService())
        config = make_config(
            GasComponent("CO2", 400.0, role=GasRole.RESIDENT),
            baseline=BaselineConfig(
                baseline_type=BaselineType.RANDOM_SMOOTH,
                parameters={"amplitude": 0.01, "anchor_count": 4},
            ),
            noise=NoiseConfig(noise_type=NoiseType.GAUSSIAN, parameters={"std": 0.001}, seed=42),
        )

        first = service.synthesize_mixture(config)
        second = service.synthesize_mixture(config)

        np.testing.assert_allclose(first.baseline, second.baseline)
        np.testing.assert_allclose(first.noise, second.noise)
        np.testing.assert_allclose(first.final_absorbance, second.final_absorbance)


if __name__ == "__main__":
    unittest.main()
