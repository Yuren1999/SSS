"""Coverage range utilities for the local line database."""

from __future__ import annotations

from collections.abc import Iterable

from spectra_sim.models import WavenumberRange


def merge_ranges(ranges: Iterable[WavenumberRange], tolerance: float = 0.0) -> tuple[WavenumberRange, ...]:
    """Merge overlapping or touching wavenumber ranges."""
    ordered = sorted(ranges, key=lambda item: item.nu_min)
    if not ordered:
        return ()

    merged: list[WavenumberRange] = [ordered[0]]
    for current in ordered[1:]:
        previous = merged[-1]
        # 下载任务可能分段执行，覆盖表中会留下相邻或重叠区间，这里统一合并为检索用覆盖范围。
        if current.nu_min <= previous.nu_max + tolerance:
            merged[-1] = WavenumberRange(previous.nu_min, max(previous.nu_max, current.nu_max))
        else:
            merged.append(current)
    return tuple(merged)


def missing_ranges(
    coverage_ranges: Iterable[WavenumberRange],
    requested_range: WavenumberRange,
    tolerance: float = 0.0,
) -> tuple[WavenumberRange, ...]:
    """Return gaps in local coverage for a requested wavenumber range."""
    merged = merge_ranges(coverage_ranges, tolerance=tolerance)
    gaps: list[WavenumberRange] = []
    cursor = requested_range.nu_min

    for coverage in merged:
        # 与请求范围完全无交集的区间不参与缺失判断。
        if coverage.nu_max <= requested_range.nu_min + tolerance:
            continue
        if coverage.nu_min >= requested_range.nu_max - tolerance:
            break

        clipped_min = max(coverage.nu_min, requested_range.nu_min)
        clipped_max = min(coverage.nu_max, requested_range.nu_max)

        # 当前覆盖区间起点晚于 cursor，说明中间存在尚未下载的波数区间。
        if clipped_min > cursor + tolerance:
            gaps.append(WavenumberRange(cursor, clipped_min))
        cursor = max(cursor, clipped_max)
        if cursor >= requested_range.nu_max - tolerance:
            break

    if cursor < requested_range.nu_max - tolerance:
        gaps.append(WavenumberRange(cursor, requested_range.nu_max))

    return tuple(gaps)


def covers_range(
    coverage_ranges: Iterable[WavenumberRange],
    requested_range: WavenumberRange,
    tolerance: float = 0.0,
) -> bool:
    """Return whether local coverage fully covers the requested range."""
    return not missing_ranges(coverage_ranges, requested_range, tolerance=tolerance)

