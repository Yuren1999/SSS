import tempfile
import unittest
from pathlib import Path

from spectra_sim.database import LineDatabaseRepository
from spectra_sim.exceptions import DownloadError
from spectra_sim.models import DownloadMode, DownloadTaskRequest, GasSpec, LineRecord, TaskStatus, WavenumberRange
from spectra_sim.services import HitranDownloadService, LineDownloadService


def make_record(gas_name: str, wavenumber: float) -> LineRecord:
    return LineRecord(
        gas_name=gas_name,
        wavenumber=wavenumber,
        line_intensity=1.0,
        air_width=0.1,
        self_width=0.05,
        lower_state_energy=10.0,
        temperature_dependence=0.7,
        pressure_shift=0.0,
    )


class FakeDownloader:
    def __init__(self) -> None:
        self.calls = []

    def download_lines(self, gas, wavenumber_range):
        self.calls.append((gas, wavenumber_range))
        midpoint = (wavenumber_range.nu_min + wavenumber_range.nu_max) / 2
        return (make_record(gas.gas_name, midpoint),)


class DownloadServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "lines.sqlite"
        self.repository = LineDatabaseRepository(self.db_path)
        self.repository.initialize()
        self.downloader = FakeDownloader()
        self.service = HitranDownloadService(self.repository, self.downloader)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_service_implements_download_protocol(self) -> None:
        self.assertIsInstance(self.service, LineDownloadService)

    def test_run_download_task_downloads_missing_range_and_writes_database(self) -> None:
        request = DownloadTaskRequest(
            gas=GasSpec("CO2", 2),
            wavenumber_range=WavenumberRange(6000.0, 6500.0),
            mode=DownloadMode.SKIP_COVERED,
            task_name="download-co2",
        )

        task = self.service.create_download_task(request)
        finished = self.service.run_download_task(task.task_id)

        self.assertEqual(finished.status, TaskStatus.SUCCEEDED)
        self.assertEqual(len(self.downloader.calls), 1)
        self.assertEqual(self.repository.get_coverage("CO2"), (WavenumberRange(6000.0, 6500.0),))
        self.assertEqual(len(self.repository.search_lines("CO2", WavenumberRange(6000.0, 6500.0)).records), 1)

    def test_run_download_task_skips_complete_coverage(self) -> None:
        gas = GasSpec("CO2", 2)
        self.repository.insert_lines(gas, (make_record("CO2", 6100.0),), WavenumberRange(6000.0, 6500.0))
        task = self.service.create_download_task(
            DownloadTaskRequest(
                gas=gas,
                wavenumber_range=WavenumberRange(6000.0, 6500.0),
                mode=DownloadMode.SKIP_COVERED,
            )
        )

        finished = self.service.run_download_task(task.task_id)

        self.assertEqual(finished.status, TaskStatus.SUCCEEDED)
        self.assertEqual(len(self.downloader.calls), 0)
        self.assertIn("跳过下载", finished.message)

    def test_run_download_task_records_failure(self) -> None:
        class FailingDownloader:
            def download_lines(self, gas, wavenumber_range):
                raise DownloadError("network failed")

        service = HitranDownloadService(self.repository, FailingDownloader())
        task = service.create_download_task(
            DownloadTaskRequest(
                gas=GasSpec("CO", 5),
                wavenumber_range=WavenumberRange(6000.0, 6500.0),
            )
        )

        with self.assertRaises(DownloadError):
            service.run_download_task(task.task_id)

        failed_task = self.repository.get_download_task(task.task_id)
        self.assertEqual(failed_task.status, TaskStatus.FAILED)
        self.assertIn("network failed", failed_task.message)


if __name__ == "__main__":
    unittest.main()

