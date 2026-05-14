"""Wavenumber grid generation."""

from __future__ import annotations

import numpy as np

from spectra_sim.models import SpectralAxisConfig


def build_wavenumber_grid(axis_config: SpectralAxisConfig) -> np.ndarray:
    """Build an ascending wavenumber grid in cm^-1."""
    start = axis_config.wavenumber_range.nu_min
    end = axis_config.wavenumber_range.nu_max
    step = axis_config.nu_step

    # 使用整数点数生成网格，避免 np.arange 浮点累积误差导致末端点不稳定。
    point_count = int(np.floor((end - start) / step)) + 1
    grid = start + np.arange(point_count, dtype=float) * step

    # 若最后一个常规采样点没有覆盖到 nu_max，则补上终点，方便 GUI 预览显示完整范围。
    if grid[-1] < end:
        grid = np.append(grid, end)
    return grid

