"""Convert HAPI table columns into internal spectral line records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from spectra_sim.exceptions import DownloadError
from spectra_sim.models import LineRecord


FIELD_ALIASES = {
    "wavenumber": ("nu", "wavenumber"),
    "line_intensity": ("sw", "line_intensity"),
    "air_width": ("gamma_air", "air_width"),
    "self_width": ("gamma_self", "self_width"),
    "lower_state_energy": ("elower", "lower_state_energy"),
    "temperature_dependence": ("n_air", "temperature_dependence"),
    "pressure_shift": ("delta_air", "pressure_shift"),
}


def convert_hapi_columns(gas_name: str, columns: Mapping[str, Sequence[float]]) -> tuple[LineRecord, ...]:
    """Convert a HAPI column mapping into internal line records."""
    normalized_columns = {name.lower(): values for name, values in columns.items()}

    resolved: dict[str, Sequence[float]] = {}
    for field_name, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias.lower() in normalized_columns:
                resolved[field_name] = normalized_columns[alias.lower()]
                break
        if field_name not in resolved:
            raise DownloadError(f"HAPI 谱线表缺少字段：{aliases[0]}")

    lengths = {len(values) for values in resolved.values()}
    if len(lengths) != 1:
        raise DownloadError("HAPI 谱线字段长度不一致")

    line_count = lengths.pop() if lengths else 0
    records: list[LineRecord] = []
    for index in range(line_count):
        # HAPI 使用 nu/sw/gamma_air 等原始字段名，这里转换为项目内部标准字段。
        records.append(
            LineRecord(
                gas_name=gas_name,
                wavenumber=float(resolved["wavenumber"][index]),
                line_intensity=float(resolved["line_intensity"][index]),
                air_width=float(resolved["air_width"][index]),
                self_width=float(resolved["self_width"][index]),
                lower_state_energy=float(resolved["lower_state_energy"][index]),
                temperature_dependence=float(resolved["temperature_dependence"][index]),
                pressure_shift=float(resolved["pressure_shift"][index]),
            )
        )
    return tuple(records)

