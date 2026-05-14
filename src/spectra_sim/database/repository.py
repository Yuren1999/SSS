"""Repository for the local spectral line database."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Sequence

from spectra_sim.database.coverage import merge_ranges, missing_ranges
from spectra_sim.database.schema import database_connection, initialize_database
from spectra_sim.exceptions import CoverageError, DatabaseError
from spectra_sim.models import (
    CoverageResult,
    DownloadMode,
    DownloadTaskInfo,
    DownloadTaskRequest,
    GasSpec,
    LineRecord,
    LineTable,
    TaskStatus,
    WavenumberRange,
)


class LineDatabaseRepository:
    """SQLite-backed repository for local HITRAN line data."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        """Create database tables if they do not exist."""
        try:
            initialize_database(self.db_path)
        except sqlite3.Error as exc:
            raise DatabaseError(f"初始化本地谱线数据库失败：{exc}") from exc

    def upsert_gas(self, gas: GasSpec) -> int:
        """Insert or update a gas catalog record and return its database id."""
        try:
            with database_connection(self.db_path) as connection:
                # 气体信息以 gas_name 为唯一键，后续扩展下载同一气体时复用同一 gas_id。
                connection.execute(
                    """
                    INSERT INTO gas_catalog(gas_name, hitran_molecule_id, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(gas_name) DO UPDATE SET
                        hitran_molecule_id = excluded.hitran_molecule_id,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (gas.gas_name, gas.hitran_molecule_id),
                )
                row = connection.execute(
                    "SELECT gas_id FROM gas_catalog WHERE gas_name = ?",
                    (gas.gas_name,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError(f"写入气体信息失败：{exc}") from exc

        if row is None:
            raise DatabaseError(f"未能读取气体编号：{gas.gas_name}")
        return int(row["gas_id"])

    def list_gases(self) -> tuple[GasSpec, ...]:
        """List gases registered in the local database."""
        try:
            with database_connection(self.db_path) as connection:
                rows = connection.execute(
                    """
                    SELECT gas_name, hitran_molecule_id
                    FROM gas_catalog
                    ORDER BY gas_name
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"读取气体列表失败：{exc}") from exc
        return tuple(GasSpec(row["gas_name"], int(row["hitran_molecule_id"])) for row in rows)

    def create_download_task(self, task_info: DownloadTaskInfo) -> None:
        """Persist a download task for GUI tracking."""
        try:
            with database_connection(self.db_path) as connection:
                gas_id = self._upsert_gas_in_connection(connection, task_info.request.gas)
                # 下载任务记录只保存用户可见参数；HAPI 内部同位素细节不进入任务模型。
                connection.execute(
                    """
                    INSERT INTO download_tasks(
                        task_id,
                        task_name,
                        gas_id,
                        nu_min,
                        nu_max,
                        mode,
                        status,
                        message,
                        started_at,
                        finished_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                    """,
                    (
                        task_info.task_id,
                        task_info.request.task_name,
                        gas_id,
                        task_info.request.wavenumber_range.nu_min,
                        task_info.request.wavenumber_range.nu_max,
                        task_info.request.mode.value,
                        task_info.status.value,
                        task_info.message,
                    ),
                )
        except sqlite3.Error as exc:
            raise DatabaseError(f"创建下载任务失败：{exc}") from exc

    def update_download_task(self, task_id: str, status: TaskStatus, message: str = "") -> None:
        """Update persisted download task status."""
        try:
            with database_connection(self.db_path) as connection:
                connection.execute(
                    """
                    UPDATE download_tasks
                    SET
                        status = ?,
                        message = ?,
                        started_at = CASE
                            WHEN ? = 'running' AND started_at IS NULL THEN CURRENT_TIMESTAMP
                            ELSE started_at
                        END,
                        finished_at = CASE
                            WHEN ? IN ('succeeded', 'failed', 'cancelled') THEN CURRENT_TIMESTAMP
                            ELSE finished_at
                        END
                    WHERE task_id = ?
                    """,
                    (status.value, message, status.value, status.value, task_id),
                )
                if connection.total_changes == 0:
                    raise DatabaseError(f"下载任务不存在：{task_id}")
        except sqlite3.Error as exc:
            raise DatabaseError(f"更新下载任务失败：{exc}") from exc

    def get_download_task(self, task_id: str) -> DownloadTaskInfo:
        """Read one persisted download task."""
        try:
            with database_connection(self.db_path) as connection:
                row = connection.execute(
                    """
                    SELECT
                        task.task_id,
                        task.task_name,
                        task.nu_min,
                        task.nu_max,
                        task.mode,
                        task.status,
                        task.message,
                        gas.gas_name,
                        gas.hitran_molecule_id
                    FROM download_tasks AS task
                    JOIN gas_catalog AS gas ON gas.gas_id = task.gas_id
                    WHERE task.task_id = ?
                    """,
                    (task_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError(f"读取下载任务失败：{exc}") from exc

        if row is None:
            raise DatabaseError(f"下载任务不存在：{task_id}")
        return self._download_task_from_row(row)

    def list_download_tasks(self) -> tuple[DownloadTaskInfo, ...]:
        """List persisted download tasks."""
        try:
            with database_connection(self.db_path) as connection:
                rows = connection.execute(
                    """
                    SELECT
                        task.task_id,
                        task.task_name,
                        task.nu_min,
                        task.nu_max,
                        task.mode,
                        task.status,
                        task.message,
                        gas.gas_name,
                        gas.hitran_molecule_id
                    FROM download_tasks AS task
                    JOIN gas_catalog AS gas ON gas.gas_id = task.gas_id
                    ORDER BY task.rowid
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"读取下载任务列表失败：{exc}") from exc
        return tuple(self._download_task_from_row(row) for row in rows)

    def insert_lines(
        self,
        gas: GasSpec,
        records: Sequence[LineRecord],
        coverage_range: WavenumberRange,
        source: str = "local",
        downloaded_at: str | None = None,
    ) -> None:
        """Insert line records and append one local coverage range."""
        normalized_records = tuple(records)
        for record in normalized_records:
            if record.gas_name != gas.gas_name:
                raise DatabaseError("谱线记录气体名称与写入气体不一致")
            if not coverage_range.contains(record.wavenumber):
                raise DatabaseError("谱线记录超出本次覆盖范围")

        try:
            with database_connection(self.db_path) as connection:
                gas_id = self._upsert_gas_in_connection(connection, gas)

                # coverage_range 表示本次下载/导入已经确认覆盖的波数区间，即使区间内没有谱线也要记录。
                connection.execute(
                    """
                    INSERT INTO line_coverage(gas_id, nu_min, nu_max, line_count, source, downloaded_at)
                    VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                    """,
                    (
                        gas_id,
                        coverage_range.nu_min,
                        coverage_range.nu_max,
                        len(normalized_records),
                        source,
                        downloaded_at,
                    ),
                )

                connection.executemany(
                    """
                    INSERT INTO spectral_lines(
                        gas_id,
                        wavenumber,
                        line_intensity,
                        air_width,
                        self_width,
                        lower_state_energy,
                        temperature_dependence,
                        pressure_shift,
                        source,
                        downloaded_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                    """,
                    [
                        (
                            gas_id,
                            record.wavenumber,
                            record.line_intensity,
                            record.air_width,
                            record.self_width,
                            record.lower_state_energy,
                            record.temperature_dependence,
                            record.pressure_shift,
                            source,
                            downloaded_at,
                        )
                        for record in normalized_records
                    ],
                )
        except sqlite3.Error as exc:
            raise DatabaseError(f"写入谱线数据失败：{exc}") from exc

    def get_coverage(self, gas_name: str) -> tuple[WavenumberRange, ...]:
        """Return merged coverage ranges for one gas."""
        try:
            with database_connection(self.db_path) as connection:
                gas_id = self._get_gas_id(connection, gas_name)
                if gas_id is None:
                    return ()
                rows = connection.execute(
                    """
                    SELECT nu_min, nu_max
                    FROM line_coverage
                    WHERE gas_id = ?
                    ORDER BY nu_min, nu_max
                    """,
                    (gas_id,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"读取覆盖范围失败：{exc}") from exc

        ranges = [WavenumberRange(float(row["nu_min"]), float(row["nu_max"])) for row in rows]
        return merge_ranges(ranges)

    def check_coverage(
        self,
        gas_names: Sequence[str],
        requested_range: WavenumberRange,
    ) -> tuple[CoverageResult, ...]:
        """Check local database coverage for multiple gases."""
        results: list[CoverageResult] = []
        for gas_name in gas_names:
            coverage = self.get_coverage(gas_name)
            missing = missing_ranges(coverage, requested_range)
            results.append(
                CoverageResult(
                    gas_name=gas_name,
                    requested_range=requested_range,
                    is_covered=not missing,
                    missing_ranges=missing,
                )
            )
        return tuple(results)

    def search_lines(
        self,
        gas_name: str,
        requested_range: WavenumberRange,
        require_coverage: bool = True,
    ) -> LineTable:
        """Search local line records by gas and wavenumber range."""
        try:
            with database_connection(self.db_path) as connection:
                gas_row = connection.execute(
                    """
                    SELECT gas_id, gas_name, hitran_molecule_id
                    FROM gas_catalog
                    WHERE gas_name = ?
                    """,
                    (gas_name,),
                ).fetchone()
                if gas_row is None:
                    if require_coverage:
                        raise CoverageError(gas_name, "本地数据库中不存在该气体")
                    raise DatabaseError(f"本地数据库中不存在该气体：{gas_name}")

                if require_coverage:
                    coverage = self.get_coverage(gas_name)
                    missing = missing_ranges(coverage, requested_range)
                    if missing:
                        missing_text = ", ".join(f"{item.nu_min}-{item.nu_max} cm^-1" for item in missing)
                        raise CoverageError(gas_name, f"本地谱线覆盖不足，缺失区间：{missing_text}")

                rows = connection.execute(
                    """
                    SELECT
                        wavenumber,
                        line_intensity,
                        air_width,
                        self_width,
                        lower_state_energy,
                        temperature_dependence,
                        pressure_shift
                    FROM spectral_lines
                    WHERE gas_id = ?
                      AND wavenumber >= ?
                      AND wavenumber <= ?
                    ORDER BY wavenumber, line_id
                    """,
                    (gas_row["gas_id"], requested_range.nu_min, requested_range.nu_max),
                ).fetchall()
        except CoverageError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseError(f"检索谱线数据失败：{exc}") from exc

        gas = GasSpec(gas_name=gas_row["gas_name"], hitran_molecule_id=int(gas_row["hitran_molecule_id"]))
        records = tuple(
            LineRecord(
                gas_name=gas.gas_name,
                wavenumber=float(row["wavenumber"]),
                line_intensity=float(row["line_intensity"]),
                air_width=float(row["air_width"]),
                self_width=float(row["self_width"]),
                lower_state_energy=float(row["lower_state_energy"]),
                temperature_dependence=float(row["temperature_dependence"]),
                pressure_shift=float(row["pressure_shift"]),
            )
            for row in rows
        )
        return LineTable(gas=gas, wavenumber_range=requested_range, records=records)

    def _upsert_gas_in_connection(self, connection: sqlite3.Connection, gas: GasSpec) -> int:
        connection.execute(
            """
            INSERT INTO gas_catalog(gas_name, hitran_molecule_id, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(gas_name) DO UPDATE SET
                hitran_molecule_id = excluded.hitran_molecule_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (gas.gas_name, gas.hitran_molecule_id),
        )
        row = connection.execute(
            "SELECT gas_id FROM gas_catalog WHERE gas_name = ?",
            (gas.gas_name,),
        ).fetchone()
        if row is None:
            raise DatabaseError(f"未能读取气体编号：{gas.gas_name}")
        return int(row["gas_id"])

    def _get_gas_id(self, connection: sqlite3.Connection, gas_name: str) -> int | None:
        row = connection.execute(
            "SELECT gas_id FROM gas_catalog WHERE gas_name = ?",
            (gas_name,),
        ).fetchone()
        return None if row is None else int(row["gas_id"])

    def _download_task_from_row(self, row: sqlite3.Row) -> DownloadTaskInfo:
        gas = GasSpec(row["gas_name"], int(row["hitran_molecule_id"]))
        request = DownloadTaskRequest(
            gas=gas,
            wavenumber_range=WavenumberRange(float(row["nu_min"]), float(row["nu_max"])),
            mode=DownloadMode(row["mode"]),
            task_name=row["task_name"],
        )
        return DownloadTaskInfo(
            task_id=row["task_id"],
            request=request,
            status=TaskStatus(row["status"]),
            message=row["message"],
        )
