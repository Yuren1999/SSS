"""Download task service for HITRAN/HAPI line data."""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from spectra_sim.database import LineDatabaseRepository, missing_ranges
from spectra_sim.exceptions import DownloadError
from spectra_sim.models import (
    DownloadMode,
    DownloadTaskInfo,
    DownloadTaskRequest,
    LineRecord,
    TaskStatus,
    WavenumberRange,
)


class LineDownloader(Protocol):
    """Minimal downloader boundary used by the service."""

    def download_lines(self, gas, wavenumber_range: WavenumberRange) -> tuple[LineRecord, ...]:
        """Download line records for one gas and range."""
        ...


class HitranDownloadService:
    """Coordinate download tasks and local database writes."""

    def __init__(self, repository: LineDatabaseRepository, downloader: LineDownloader) -> None:
        self._repository = repository
        self._downloader = downloader

    def create_download_task(self, request: DownloadTaskRequest) -> DownloadTaskInfo:
        task_info = DownloadTaskInfo(
            task_id=uuid4().hex,
            request=request,
            status=TaskStatus.PENDING,
            message="等待下载",
        )
        self._repository.create_download_task(task_info)
        return task_info

    def run_download_task(self, task_id: str) -> DownloadTaskInfo:
        task_info = self._repository.get_download_task(task_id)
        self._repository.update_download_task(task_id, TaskStatus.RUNNING, "正在检查本地覆盖范围")

        try:
            downloaded_ranges = self._run_request(task_info.request)
        except Exception as exc:
            self._repository.update_download_task(task_id, TaskStatus.FAILED, str(exc))
            if isinstance(exc, DownloadError):
                raise
            raise DownloadError(f"下载任务失败：{exc}") from exc

        if downloaded_ranges:
            message = f"下载完成，新增 {len(downloaded_ranges)} 个波数区间"
        else:
            message = "本地数据库已完整覆盖，跳过下载"
        self._repository.update_download_task(task_id, TaskStatus.SUCCEEDED, message)
        return self._repository.get_download_task(task_id)

    def list_download_tasks(self) -> tuple[DownloadTaskInfo, ...]:
        return self._repository.list_download_tasks()

    def _run_request(self, request: DownloadTaskRequest) -> tuple[WavenumberRange, ...]:
        if request.mode is DownloadMode.OVERWRITE:
            raise DownloadError("当前阶段暂不支持覆盖已有谱线区间，请使用新增缺失区间模式")

        existing_coverage = self._repository.get_coverage(request.gas.gas_name)
        gaps = missing_ranges(existing_coverage, request.wavenumber_range)
        if not gaps:
            return ()

        ranges_to_download = gaps
        downloaded: list[WavenumberRange] = []
        for download_range in ranges_to_download:
            # 下载服务只协调任务流程，具体 HAPI 调用由 downloader 完成，数据库写入由 repository 完成。
            records = self._downloader.download_lines(request.gas, download_range)
            self._repository.insert_lines(
                gas=request.gas,
                records=records,
                coverage_range=download_range,
                source="HITRAN/HAPI",
            )
            downloaded.append(download_range)
        return tuple(downloaded)
