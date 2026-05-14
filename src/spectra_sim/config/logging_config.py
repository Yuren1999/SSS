"""Logging configuration for the application."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_dir: Path | None = None, level: int = logging.INFO) -> Path:
    """Configure file and console logging, returning the log file path."""
    # 日志默认写入当前项目目录下的 logs，方便开发阶段直接查看任务运行状态。
    target_dir = log_dir or Path.cwd() / "logs"
    target_dir.mkdir(parents=True, exist_ok=True)
    log_file = target_dir / "spectra_simulator.log"

    # force=True 确保多次启动测试时能刷新配置，避免旧 handler 重复写入。
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    logging.getLogger(__name__).info("日志系统已初始化：%s", log_file)
    return log_file

