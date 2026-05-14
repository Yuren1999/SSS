import tempfile
import unittest
from pathlib import Path

from spectra_sim.database import LineDatabaseRepository
from spectra_sim.exceptions import CoverageError, DatabaseError
from spectra_sim.models import (
    DownloadMode,
    DownloadTaskInfo,
    DownloadTaskRequest,
    GasSpec,
    LineRecord,
    TaskStatus,
    WavenumberRange,
)


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


class LineDatabaseRepositoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "lines.sqlite"
        self.repository = LineDatabaseRepository(self.db_path)
        self.repository.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_upsert_and_list_gases(self) -> None:
        self.repository.upsert_gas(GasSpec("CO2", 2))

        gases = self.repository.list_gases()

        self.assertEqual(gases, (GasSpec("CO2", 2),))

    def test_insert_lines_records_coverage_and_searches_local_lines(self) -> None:
        gas = GasSpec("CO2", 2)
        coverage = WavenumberRange(6000.0, 6500.0)
        records = (make_record("CO2", 6100.0), make_record("CO2", 6200.0))

        self.repository.insert_lines(gas, records, coverage)

        line_table = self.repository.search_lines("CO2", WavenumberRange(6050.0, 6250.0))

        self.assertEqual(line_table.gas, gas)
        self.assertEqual([record.wavenumber for record in line_table.records], [6100.0, 6200.0])
        self.assertEqual(self.repository.get_coverage("CO2"), (coverage,))

    def test_insert_empty_covered_range_allows_empty_search_result(self) -> None:
        gas = GasSpec("H2O", 1)
        coverage = WavenumberRange(6000.0, 6500.0)

        self.repository.insert_lines(gas, (), coverage)

        line_table = self.repository.search_lines("H2O", WavenumberRange(6100.0, 6200.0))

        self.assertEqual(line_table.records, ())

    def test_check_coverage_reports_missing_ranges(self) -> None:
        gas = GasSpec("CH4", 6)
        self.repository.insert_lines(gas, (make_record("CH4", 6050.0),), WavenumberRange(6000.0, 6100.0))

        result = self.repository.check_coverage(["CH4"], WavenumberRange(6000.0, 6200.0))[0]

        self.assertFalse(result.is_covered)
        self.assertEqual(result.missing_ranges, (WavenumberRange(6100.0, 6200.0),))

    def test_search_lines_raises_coverage_error_when_range_is_missing(self) -> None:
        gas = GasSpec("CO", 5)
        self.repository.insert_lines(gas, (make_record("CO", 6050.0),), WavenumberRange(6000.0, 6100.0))

        with self.assertRaises(CoverageError):
            self.repository.search_lines("CO", WavenumberRange(6000.0, 6200.0))

    def test_insert_lines_rejects_record_outside_coverage(self) -> None:
        with self.assertRaises(DatabaseError):
            self.repository.insert_lines(
                GasSpec("CO2", 2),
                (make_record("CO2", 6600.0),),
                WavenumberRange(6000.0, 6500.0),
            )

    def test_download_task_roundtrip_preserves_mode_and_status(self) -> None:
        task_info = DownloadTaskInfo(
            task_id="task-1",
            request=DownloadTaskRequest(
                gas=GasSpec("CO2", 2),
                wavenumber_range=WavenumberRange(6000.0, 6500.0),
                mode=DownloadMode.ADD_MISSING,
                task_name="CO2 download",
            ),
            status=TaskStatus.PENDING,
            message="waiting",
        )

        self.repository.create_download_task(task_info)
        self.repository.update_download_task("task-1", TaskStatus.RUNNING, "running")
        loaded = self.repository.get_download_task("task-1")

        self.assertEqual(loaded.request.mode, DownloadMode.ADD_MISSING)
        self.assertEqual(loaded.status, TaskStatus.RUNNING)
        self.assertEqual(loaded.message, "running")


if __name__ == "__main__":
    unittest.main()
