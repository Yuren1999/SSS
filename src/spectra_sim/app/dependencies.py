"""Application dependency wiring for the desktop GUI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from spectra_sim.database import LineDatabaseRepository
from spectra_sim.hitran import HapiLineDownloader
from spectra_sim.app.result_store import ResultStore
from spectra_sim.services import (
    BatchSynthesisService,
    ExportService,
    HitranDownloadService,
    LineDatabaseService,
    LineDownloadService,
    LocalBatchSynthesisService,
    LocalExportService,
    LocalLineDatabaseService,
    LocalResultService,
    LocalSynthesisService,
    ResultRepositoryService,
    SynthesisService,
)


@dataclass(frozen=True)
class AppServices:
    """Service dependencies consumed by GUI pages."""

    line_database: LineDatabaseService
    line_download: LineDownloadService
    synthesis: SynthesisService
    batch: BatchSynthesisService
    export: ExportService
    result_store: ResultStore
    result_repository: ResultRepositoryService
    database_path: Path


def build_default_services(project_root: Path | None = None) -> AppServices:
    """Build production services for the desktop GUI."""
    root = project_root or Path.cwd()
    database_dir = root / "data" / "local_line_db"
    database_dir.mkdir(parents=True, exist_ok=True)
    database_path = database_dir / "lines.sqlite"

    repository = LineDatabaseRepository(database_path)
    repository.initialize()

    line_database = LocalLineDatabaseService(repository)
    downloader = HapiLineDownloader(root / "hapi-cache")
    line_download = HitranDownloadService(repository, downloader)
    synthesis = LocalSynthesisService(line_database)
    batch = LocalBatchSynthesisService(synthesis)
    export = LocalExportService()
    result_store = ResultStore()
    result_repository = LocalResultService.from_path(root / "data" / "results")

    return AppServices(
        line_database=line_database,
        line_download=line_download,
        synthesis=synthesis,
        batch=batch,
        export=export,
        result_store=result_store,
        result_repository=result_repository,
        database_path=database_path,
    )
