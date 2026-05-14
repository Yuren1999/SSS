"""Main window for the desktop GUI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QStatusBar, QTabWidget, QVBoxLayout, QWidget

from spectra_sim.models.app import AppInfo


class MainWindow(QMainWindow):
    """Empty shell used by the P0 engineering skeleton."""

    def __init__(self, app_info: AppInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app_info = app_info
        self.setWindowTitle(f"{app_info.name} v{app_info.version}")
        self.resize(1180, 760)

        self._build_central_widget()
        self._build_status_bar()

    def _build_central_widget(self) -> None:
        # 当前阶段只搭建页面占位，后续各模块通过服务层接入，避免 GUI 直接承载业务逻辑。
        tabs = QTabWidget(self)
        tabs.addTab(self._placeholder_page("谱线下载", "P3 阶段接入 HAPI 下载服务"), "谱线下载")
        tabs.addTab(self._placeholder_page("本地数据库", "P2 阶段接入本地谱线数据库服务"), "本地数据库")
        tabs.addTab(self._placeholder_page("本地检索", "P2 阶段接入覆盖检查与谱线检索"), "本地检索")
        tabs.addTab(self._placeholder_page("单条合成", "P4 阶段接入单气体光谱合成"), "单条合成")
        tabs.addTab(self._placeholder_page("批量合成", "P6 阶段接入批量任务服务"), "批量合成")
        tabs.addTab(self._placeholder_page("结果浏览", "P7 阶段接入结果预览与导出"), "结果浏览")
        self.setCentralWidget(tabs)

    def _placeholder_page(self, title: str, description: str) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title, page)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("pageTitle")

        description_label = QLabel(description, page)
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        return page

    def _build_status_bar(self) -> None:
        # 状态栏先展示工程阶段，后续长任务进度和错误信息统一从 worker 回传到这里。
        status_bar = QStatusBar(self)
        status_bar.showMessage("P0 工程骨架已加载")
        self.setStatusBar(status_bar)

