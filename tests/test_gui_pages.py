import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget  # noqa: E402

from spectra_sim.app.dependencies import AppServices  # noqa: E402
from spectra_sim.app.main_window import MainWindow  # noqa: E402
from spectra_sim.app.pages import BatchExportPage, DownloadPage, ResultsPage, SynthesisPage  # noqa: E402
from spectra_sim.app.result_store import ResultStore  # noqa: E402
from spectra_sim.models import (  # noqa: E402
    AppInfo,
    BatchTaskResult,
    DownloadTaskInfo,
    DownloadTaskRequest,
    GasSpec,
    LineTable,
    SavedResultDataset,
    SpectrumRecord,
    TaskStatus,
    WavenumberRange,
)


class FakeDownloadService:
    def __init__(self) -> None:
        self.created = []
        self.tasks = []

    def create_download_task(self, request: DownloadTaskRequest) -> DownloadTaskInfo:
        self.created.append(request)
        task = DownloadTaskInfo("task-1", request, TaskStatus.PENDING, "waiting")
        self.tasks.append(task)
        return task

    def run_download_task(self, task_id: str) -> DownloadTaskInfo:
        return self.tasks[0]

    def list_download_tasks(self):
        return tuple(self.tasks)


class FakeLineDatabaseService:
    def list_gases(self):
        return (GasSpec("CO2", 2),)

    def get_coverage(self, gas_name: str):
        return (WavenumberRange(6000.0, 6500.0),)

    def check_coverage(self, gas_names, requested_range):
        return []

    def search_lines(self, gas_name, requested_range):
        return LineTable(GasSpec(gas_name, 2), requested_range, ())


class FakeSynthesisService:
    def preview(self, config):
        return SpectrumRecord(
            sample_id="preview",
            wavenumber=(6000.0, 6001.0),
            clean_absorbance=(0.1, 0.2),
            final_absorbance=(0.1, 0.2),
            transmittance=(0.9, 0.8),
        )

    def synthesize_single(self, config):
        return self.preview(config)

    def synthesize_mixture(self, config):
        return self.preview(config)


class FakeBatchService:
    def __init__(self) -> None:
        self.result = BatchTaskResult(
            task_id="batch-1",
            status=TaskStatus.SUCCEEDED,
            records=(make_record("batch-1-000000"),),
        )

    def expand_parameters(self, batch_config):
        return ()

    def run_batch(self, batch_config):
        return "batch-1"

    def get_task_result(self, task_id: str) -> BatchTaskResult:
        return self.result

    def pause_task(self, task_id: str) -> None:
        return None

    def resume_task(self, task_id: str) -> None:
        return None


class FakeExportService:
    def export_spectra(self, records, output_config):
        return Path("dummy")


class FakeResultRepository:
    def __init__(self) -> None:
        self.saved_records = ()
        self.dataset = SavedResultDataset(
            dataset_id="dataset-1",
            name="dataset-1",
            record_count=1,
            storage_path=Path("dummy"),
            created_at="2026-05-15T00:00:00+00:00",
        )

    def save_records(self, records, name=None):
        self.saved_records = tuple(records)
        return self.dataset

    def list_datasets(self):
        return (self.dataset,) if self.saved_records else ()

    def load_records(self, dataset_id: str):
        return self.saved_records


def make_record(sample_id: str = "preview") -> SpectrumRecord:
    return SpectrumRecord(
        sample_id=sample_id,
        wavenumber=(6000.0, 6001.0),
        clean_absorbance=(0.1, 0.2),
        final_absorbance=(0.1, 0.2),
        transmittance=(0.9, 0.8),
    )


def make_services() -> AppServices:
    line_database = FakeLineDatabaseService()
    return AppServices(
        line_database=line_database,
        line_download=FakeDownloadService(),
        synthesis=FakeSynthesisService(),
        batch=FakeBatchService(),
        export=FakeExportService(),
        result_store=ResultStore(),
        result_repository=FakeResultRepository(),
        database_path=Path("dummy.sqlite"),
    )


class GuiPagesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_keeps_download_and_synthesis_on_separate_tabs(self) -> None:
        window = MainWindow(AppInfo.default(), services=make_services())
        tabs = window.findChild(QTabWidget, "mainTabs")

        tab_names = [tabs.tabText(index) for index in range(tabs.count())]

        self.assertIn("谱线下载", tab_names)
        self.assertIn("光谱合成", tab_names)
        self.assertIn("批量与导出", tab_names)
        self.assertIn("结果浏览", tab_names)
        self.assertIsNotNone(window.findChild(DownloadPage, "downloadPage"))
        self.assertIsNotNone(window.findChild(SynthesisPage, "synthesisPage"))
        self.assertIsNotNone(window.findChild(BatchExportPage, "batchExportPage"))
        self.assertIsNotNone(window.findChild(ResultsPage, "resultsPage"))

    def test_download_page_has_no_synthesis_service_dependency(self) -> None:
        window = MainWindow(AppInfo.default(), services=make_services())
        download_page = window.findChild(DownloadPage, "downloadPage")

        self.assertFalse(hasattr(download_page, "_synthesis_service"))

    def test_synthesis_page_has_no_download_service_dependency(self) -> None:
        window = MainWindow(AppInfo.default(), services=make_services())
        synthesis_page = window.findChild(SynthesisPage, "synthesisPage")

        self.assertFalse(hasattr(synthesis_page, "_download_service"))

    def test_batch_export_page_has_no_download_service_dependency(self) -> None:
        window = MainWindow(AppInfo.default(), services=make_services())
        batch_page = window.findChild(BatchExportPage, "batchExportPage")

        self.assertFalse(hasattr(batch_page, "_download_service"))

    def test_batch_page_updates_shared_result_store(self) -> None:
        services = make_services()
        window = MainWindow(AppInfo.default(), services=services)
        batch_page = window.findChild(BatchExportPage, "batchExportPage")

        batch_page.run_batch()

        self.assertEqual(len(services.result_store.records), 1)
        self.assertEqual(services.result_store.records[0].sample_id, "batch-1-000000")
        self.assertEqual(len(services.result_repository.saved_records), 1)


if __name__ == "__main__":
    unittest.main()
