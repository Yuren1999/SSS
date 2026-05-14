"""Application entry point for the desktop GUI."""

from __future__ import annotations

import sys

from spectra_sim.config.logging_config import configure_logging
from spectra_sim.models.app import AppInfo


def main() -> int:
    """Start the desktop GUI application."""
    configure_logging()

    try:
        from PySide6.QtWidgets import QApplication

        from spectra_sim.app.main_window import MainWindow
    except ModuleNotFoundError as exc:
        # GUI 依赖缺失时给出明确提示，避免用户只看到底层导入错误。
        missing_name = exc.name or "PySide6"
        print(f"缺少桌面 GUI 运行依赖：{missing_name}。请先安装项目依赖。", file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    window = MainWindow(AppInfo.default())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

