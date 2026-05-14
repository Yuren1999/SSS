"""HAPI download adapter."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

from spectra_sim.exceptions import DownloadError
from spectra_sim.hitran.converter import FIELD_ALIASES, convert_hapi_columns
from spectra_sim.models import GasSpec, LineRecord, WavenumberRange

DEFAULT_LOCAL_ISOTOPOLOGUE_ID = 1


class HapiLineDownloader:
    """Download line-by-line data through the HITRAN HAPI module."""

    def __init__(
        self,
        workspace_dir: str | Path,
        hapi_module: ModuleType | None = None,
        local_isotopologue_id: int = DEFAULT_LOCAL_ISOTOPOLOGUE_ID,
    ) -> None:
        self.workspace_dir = Path(workspace_dir)
        self._hapi = hapi_module
        self.local_isotopologue_id = local_isotopologue_id

    def download_lines(self, gas: GasSpec, wavenumber_range: WavenumberRange) -> tuple[LineRecord, ...]:
        """Download one gas and one wavenumber range through HAPI."""
        hapi = self._load_hapi()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        table_name = self._table_name(gas, wavenumber_range)

        try:
            # HAPI 原生 fetch 需要同位素编号。项目不向用户暴露该参数，适配器内部使用默认主同位素编号。
            hapi.db_begin(str(self.workspace_dir))
            hapi.fetch(
                table_name,
                gas.hitran_molecule_id,
                self.local_isotopologue_id,
                wavenumber_range.nu_min,
                wavenumber_range.nu_max,
            )
            columns = self._read_columns(hapi, table_name)
        except Exception as exc:  # noqa: BLE001 - HAPI may raise non-standard exceptions.
            raise DownloadError(f"HAPI 下载失败：{exc}") from exc

        return convert_hapi_columns(gas.gas_name, columns)

    def _load_hapi(self) -> ModuleType:
        if self._hapi is not None:
            return self._hapi
        try:
            self._hapi = importlib.import_module("hapi")
        except ModuleNotFoundError as exc:
            raise DownloadError("未安装 HAPI，请先安装 hitran-api 依赖") from exc
        return self._hapi

    def _read_columns(self, hapi: ModuleType, table_name: str) -> dict[str, list[float]]:
        columns: dict[str, list[float]] = {}
        for aliases in FIELD_ALIASES.values():
            hapi_name = aliases[0]
            try:
                # getColumn 是 HAPI 表读取接口，按字段逐列取出后再做内部标准字段转换。
                columns[hapi_name] = list(hapi.getColumn(table_name, hapi_name))
            except Exception as exc:  # noqa: BLE001 - keep adapter tolerant to HAPI internals.
                raise DownloadError(f"读取 HAPI 字段失败：{hapi_name}") from exc
        return columns

    def _table_name(self, gas: GasSpec, wavenumber_range: WavenumberRange) -> str:
        safe_gas_name = "".join(char if char.isalnum() else "_" for char in gas.gas_name)
        start = str(wavenumber_range.nu_min).replace(".", "_")
        end = str(wavenumber_range.nu_max).replace(".", "_")
        return f"{safe_gas_name}_{gas.hitran_molecule_id}_{start}_{end}"

