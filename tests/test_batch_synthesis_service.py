import unittest

from spectra_sim.exceptions import BatchError, SynthesisError
from spectra_sim.models import (
    EnvironmentConfig,
    GasComponent,
    GasRole,
    SpectralAxisConfig,
    SpectrumRecord,
    SynthesisConfig,
    TaskStatus,
    WavenumberRange,
)
from spectra_sim.services import LocalBatchSynthesisService


def make_base_config() -> SynthesisConfig:
    return SynthesisConfig(
        spectral_axis=SpectralAxisConfig(WavenumberRange(6000.0, 6000.2), nu_step=0.1),
        environment=EnvironmentConfig(pressure=1.0, temperature=296.0, path_length=10.0),
        variable_gases=(GasComponent("CH4", 1.0, role=GasRole.VARIABLE),),
    )


class FakeSynthesisService:
    def preview(self, config: SynthesisConfig) -> SpectrumRecord:
        if config.environment.pressure == 99.0:
            raise SynthesisError("synthetic failure")
        return SpectrumRecord(
            sample_id="preview",
            wavenumber=(6000.0, 6000.1, 6000.2),
            clean_absorbance=(config.environment.pressure, 0.1, 0.2),
            final_absorbance=(config.environment.pressure, 0.1, 0.2),
        )

    def synthesize_single(self, config: SynthesisConfig) -> SpectrumRecord:
        return self.preview(config)

    def synthesize_mixture(self, config: SynthesisConfig) -> SpectrumRecord:
        return self.preview(config)


class LocalBatchSynthesisServiceTestCase(unittest.TestCase):
    def test_run_batch_keeps_successful_records_and_failures(self) -> None:
        service = LocalBatchSynthesisService(FakeSynthesisService())
        task_id = service.run_batch(
            {
                "task_id": "task-1",
                "base_config": make_base_config(),
                "grid": {"environment.pressure": [1.0, 99.0, 2.0]},
            }
        )

        result = service.get_task_result(task_id)

        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertEqual(len(result.records), 2)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.records[0].sample_id, "task-1-000000")
        self.assertEqual(result.records[1].metadata["sample_index"], 2)

    def test_unknown_task_raises_batch_error(self) -> None:
        service = LocalBatchSynthesisService(FakeSynthesisService())

        with self.assertRaises(BatchError):
            service.get_task_result("missing")


if __name__ == "__main__":
    unittest.main()
