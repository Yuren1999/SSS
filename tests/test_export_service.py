import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np

from spectra_sim.exceptions import ExportError
from spectra_sim.models import OutputConfig, OutputFormat, SpectrumLabels, SpectrumRecord
from spectra_sim.services import ExportService, LocalExportService


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


class ExportServiceTestCase(unittest.TestCase):
    def test_local_export_service_implements_protocol(self) -> None:
        self.assertIsInstance(LocalExportService(), ExportService)

    def test_export_csv_writes_spectra_labels_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = LocalExportService()
            output_path = service.export_spectra(
                [make_record()],
                OutputConfig(output_format=OutputFormat.CSV, output_dir=temp_dir),
            )

            self.assertEqual(output_path, Path(temp_dir))
            self.assertTrue((output_path / "spectra.csv").exists())
            self.assertTrue((output_path / "labels.csv").exists())
            self.assertTrue((output_path / "metadata.csv").exists())

            with (output_path / "labels.csv").open("r", newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["resident.CO2"], "400.0")
            self.assertEqual(rows[0]["presence.CH4"], "1")

    def test_export_npz_writes_array_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = LocalExportService()
            output_path = service.export_spectra(
                [make_record("sample-1"), make_record("sample-2")],
                OutputConfig(output_format=OutputFormat.NPZ, output_dir=temp_dir),
            )

            with np.load(output_path) as dataset:
                self.assertEqual(dataset["clean_absorbance"].shape, (2, 2))
                self.assertEqual(dataset["sample_id"].tolist(), ["sample-1", "sample-2"])

    def test_export_hdf5_writes_file_when_dependency_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = LocalExportService()
            if importlib.util.find_spec("h5py") is None:
                with self.assertRaises(ExportError):
                    service.export_spectra(
                        [make_record()],
                        OutputConfig(output_format=OutputFormat.HDF5, output_dir=temp_dir),
                    )
                return

            output_path = service.export_spectra(
                [make_record()],
                OutputConfig(output_format=OutputFormat.HDF5, output_dir=temp_dir),
            )

            self.assertEqual(output_path.name, "spectra_dataset.h5")
            self.assertTrue(output_path.exists())

    def test_export_parquet_writes_tables_when_dependencies_are_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = LocalExportService()
            if importlib.util.find_spec("pandas") is None or importlib.util.find_spec("pyarrow") is None:
                with self.assertRaises(ExportError):
                    service.export_spectra(
                        [make_record()],
                        OutputConfig(output_format=OutputFormat.PARQUET, output_dir=temp_dir),
                    )
                return

            output_path = service.export_spectra(
                [make_record()],
                OutputConfig(output_format=OutputFormat.PARQUET, output_dir=temp_dir),
            )

            self.assertTrue((output_path / "spectra.parquet").exists())
            self.assertTrue((output_path / "labels.parquet").exists())
            self.assertTrue((output_path / "metadata.parquet").exists())


if __name__ == "__main__":
    unittest.main()
