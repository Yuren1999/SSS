"""Task-related data models shared by services and GUI."""

from __future__ import annotations

from dataclasses import dataclass, field

from spectra_sim.exceptions import ValidationError
from spectra_sim.models.enums import DownloadMode, TaskStatus
from spectra_sim.models.spectral import GasSpec, WavenumberRange


@dataclass(frozen=True)
class DownloadTaskRequest:
    """User request for downloading one gas and one wavenumber range."""

    gas: GasSpec
    wavenumber_range: WavenumberRange
    mode: DownloadMode = DownloadMode.SKIP_COVERED
    task_name: str = ""


@dataclass(frozen=True)
class DownloadTaskInfo:
    """Runtime state of a download task."""

    task_id: str
    request: DownloadTaskRequest
    status: TaskStatus = TaskStatus.PENDING
    message: str = ""

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValidationError("下载任务编号不能为空")


@dataclass(frozen=True)
class CoverageResult:
    """Local line database coverage result for one gas."""

    gas_name: str
    requested_range: WavenumberRange
    is_covered: bool
    missing_ranges: tuple[WavenumberRange, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "missing_ranges", tuple(self.missing_ranges))
        if self.is_covered and self.missing_ranges:
            raise ValidationError("覆盖完整时不应包含缺失区间")

