"""Service-layer protocols used by the desktop GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from spectra_sim.models import (
    CoverageResult,
    DownloadTaskInfo,
    DownloadTaskRequest,
    GasSpec,
    LineTable,
    OutputConfig,
    SpectrumRecord,
    SynthesisConfig,
    WavenumberRange,
)


@runtime_checkable
class LineDownloadService(Protocol):
    """Boundary for HITRAN/HAPI download workflows."""

    def create_download_task(self, request: DownloadTaskRequest) -> DownloadTaskInfo:
        """Create a download task without running it immediately."""
        ...

    def run_download_task(self, task_id: str) -> DownloadTaskInfo:
        """Run a queued download task."""
        ...

    def list_download_tasks(self) -> Sequence[DownloadTaskInfo]:
        """Return known download tasks for GUI display."""
        ...


@runtime_checkable
class LineDatabaseService(Protocol):
    """Boundary for local spectral line database access."""

    def list_gases(self) -> Sequence[GasSpec]:
        """List gases already known by the local database."""
        ...

    def get_coverage(self, gas_name: str) -> Sequence[WavenumberRange]:
        """Return downloaded wavenumber coverage ranges for one gas."""
        ...

    def check_coverage(self, gas_names: Sequence[str], requested_range: WavenumberRange) -> Sequence[CoverageResult]:
        """Check whether local data covers all requested gases and ranges."""
        ...

    def search_lines(self, gas_name: str, requested_range: WavenumberRange) -> LineTable:
        """Search local line-by-line records for one gas and range."""
        ...


@runtime_checkable
class SynthesisService(Protocol):
    """Boundary for single and mixture spectrum synthesis."""

    def preview(self, config: SynthesisConfig) -> SpectrumRecord:
        """Generate a lightweight preview spectrum for GUI display."""
        ...

    def synthesize_single(self, config: SynthesisConfig) -> SpectrumRecord:
        """Generate one single-gas spectrum."""
        ...

    def synthesize_mixture(self, config: SynthesisConfig) -> SpectrumRecord:
        """Generate one mixed-gas spectrum."""
        ...


@runtime_checkable
class BatchSynthesisService(Protocol):
    """Boundary for parameter expansion and batch synthesis jobs."""

    def expand_parameters(self, batch_config: Mapping[str, Any]) -> Sequence[SynthesisConfig]:
        """Expand a batch task config into concrete synthesis configs."""
        ...

    def run_batch(self, batch_config: Mapping[str, Any]) -> str:
        """Run a batch task and return the task id."""
        ...

    def pause_task(self, task_id: str) -> None:
        """Pause a running batch task."""
        ...

    def resume_task(self, task_id: str) -> None:
        """Resume a paused batch task."""
        ...


@runtime_checkable
class ExportService(Protocol):
    """Boundary for writing synthesized datasets."""

    def export_spectra(self, records: Sequence[SpectrumRecord], output_config: OutputConfig) -> Path:
        """Write spectra, labels and metadata to disk."""
        ...

