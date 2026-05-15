import tempfile
import unittest
from pathlib import Path

from spectra_sim.io import LocalResultRepository
from spectra_sim.models import SpectrumLabels, SpectrumRecord
from spectra_sim.services import LocalResultService, ResultRepositoryService


def make_record(sample_id: str = "sample-1") -> SpectrumRecord:
    return SpectrumRecord(
        sample_id=sample_id,
        wavenumber=(6000.0, 6000.1),
        clean_absorbance=(0.1, 0.2),
        baseline=(0.01, 0.01),
        noise=(0.001, -0.001),
        final_absorbance=(0.111, 0.209),
        transmittance=(0.9, 0.8),
        labels=SpectrumLabels(
            resident_concentrations={"CO2": 400.0},
            variable_presence={"CH4": 1},
            variable_concentrations={"CH4": 2.0},
        ),
        metadata={"sample_index": 0},
    )


class ResultRepositoryTestCase(unittest.TestCase):
    def test_local_result_service_implements_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = LocalResultService.from_path(temp_dir)

            self.assertIsInstance(service, ResultRepositoryService)

    def test_save_list_and_load_records_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = LocalResultRepository(temp_dir)

            dataset = repository.save_records((make_record(),), name="demo")
            datasets = repository.list_datasets()
            loaded = repository.load_records(dataset.dataset_id)

            self.assertEqual(dataset.name, "demo")
            self.assertEqual(dataset.record_count, 1)
            self.assertEqual(datasets[0].dataset_id, dataset.dataset_id)
            self.assertTrue((Path(temp_dir) / dataset.dataset_id / "records.npz").exists())
            self.assertEqual(loaded[0].sample_id, "sample-1")
            self.assertEqual(loaded[0].labels.resident_concentrations["CO2"], 400.0)
            self.assertEqual(loaded[0].metadata["sample_index"], 0)


if __name__ == "__main__":
    unittest.main()
