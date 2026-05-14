"""Application-level data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppInfo:
    """Basic application metadata shown by the GUI and logs."""

    name: str
    version: str
    organization: str = "SSS"

    @classmethod
    def default(cls) -> "AppInfo":
        # 应用名称和版本集中在模型层，避免 GUI 页面分散硬编码。
        return cls(name="吸收光谱数据模拟软件", version="0.1.0")

