import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget  # noqa: E402

from spectra_sim.app.dependencies import AppServices  # noqa: E402
from spectra_sim.app.main_window import MainWindow  # noqa: E402
from spectra_sim.app.pages import DownloadPage, SynthesisPage  # noqa: E402
from spectra_sim.models import (  # noqa: E402
    AppInfo,
    DownloadTaskInfo,
    DownloadTaskRequest,
    GasSpec,
    LineTable,
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
    def expand_parameters(self, batch_config):
        return ()

    def run_batch(self, batch_config):
        return "batch-1"

    def pause_task(self, task_id: str) -> None:
        return None

    def resume_task(self, task_id: str) -> None:
        return None


class FakeExportService:
    def export_spectra(self, records, output_config):
        return Path("dummy")


def make_services() -> AppServices:
    line_database = FakeLineDatabaseService()
    return AppServices(
        line_database=line_database,
        line_download=FakeDownloadService(),
        synthesis=FakeSynthesisService(),
        batch=FakeBatchService(),
        export=FakeExportService(),
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
        self.assertIsNotNone(window.findChild(DownloadPage, "downloadPage"))
        self.assertIsNotNone(window.findChild(SynthesisPage, "synthesisPage"))

    def test_download_page_has_no_synthesis_service_dependency(self) -> None:
        window = MainWindow(AppInfo.default(), services=make_services())
        download_page = window.findChild(DownloadPage, "downloadPage")

        self.assertFalse(hasattr(download_page, "_synthesis_service"))

    def test_synthesis_page_has_no_download_service_dependency(self) -> None:
        window = MainWindow(AppInfo.default(), services=make_services())
        synthesis_page = window.findChild(SynthesisPage, "synthesisPage")

        self.assertFalse(hasattr(synthesis_page, "_download_service"))


if __name__ == "__main__":
    unittest.main()
