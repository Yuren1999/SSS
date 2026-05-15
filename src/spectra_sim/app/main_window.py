"""Main window for the desktop GUI."""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QStatusBar, QTabWidget, QWidget

from spectra_sim.app.dependencies import AppServices, build_default_services
from spectra_sim.app.pages import DownloadPage, LocalDatabasePage, PlaceholderPage, SynthesisPage
from spectra_sim.models.app import AppInfo


class MainWindow(QMainWindow):
    """Desktop shell that keeps download and synthesis workflows separate."""

    def __init__(
        self,
        app_info: AppInfo,
        services: AppServices | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._app_info = app_info
        self._services = services or build_default_services()
        self.setWindowTitle(f"{app_info.name} v{app_info.version}")
        self.resize(1180, 760)

        self._build_central_widget()
        self._build_status_bar()

    def _build_central_widget(self) -> None:
        tabs = QTabWidget(self)
        tabs.setObjectName("mainTabs")
        tabs.addTab(
            DownloadPage(self._services.line_download, self._services.line_database, self),
            "谱线下载",
        )
        tabs.addTab(
            LocalDatabasePage(self._services.line_database, self),
            "本地数据库",
        )
        tabs.addTab(
            SynthesisPage(self._services.synthesis, self._services.line_database, self),
            "光谱合成",
        )
        tabs.addTab(
            PlaceholderPage("批量与导出", "后续接入批量参数、任务结果和 CSV/NPZ 导出服务", self),
            "批量与导出",
        )
        tabs.addTab(
            PlaceholderPage("结果浏览", "后续接入历史结果、曲线显示和导出文件浏览", self),
            "结果浏览",
        )
        self.setCentralWidget(tabs)

    def _build_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        status_bar.showMessage(f"本地数据库：{self._services.database_path}")
        self.setStatusBar(status_bar)
