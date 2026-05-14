"""Concrete service for local spectral line database access."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from spectra_sim.database import LineDatabaseRepository
from spectra_sim.models import CoverageResult, GasSpec, LineTable, WavenumberRange


class LocalLineDatabaseService:
    """Service adapter that keeps GUI code away from Repository details."""

    def __init__(self, repository: LineDatabaseRepository) -> None:
        self._repository = repository

    @classmethod
    def from_path(cls, db_path: str | Path) -> "LocalLineDatabaseService":
        repository = LineDatabaseRepository(db_path)
        repository.initialize()
        return cls(repository)

    def list_gases(self) -> Sequence[GasSpec]:
        return self._repository.list_gases()

    def get_coverage(self, gas_name: str) -> Sequence[WavenumberRange]:
        return self._repository.get_coverage(gas_name)

    def check_coverage(self, gas_names: Sequence[str], requested_range: WavenumberRange) -> Sequence[CoverageResult]:
        return self._repository.check_coverage(gas_names, requested_range)

    def search_lines(self, gas_name: str, requested_range: WavenumberRange) -> LineTable:
        return self._repository.search_lines(gas_name, requested_range)

