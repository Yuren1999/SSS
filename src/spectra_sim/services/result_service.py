"""Concrete persisted result service implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from spectra_sim.io import LocalResultRepository
from spectra_sim.models import SavedResultDataset, SpectrumRecord


class LocalResultService:
    """Service adapter for persistent synthesized result datasets."""

    def __init__(self, repository: LocalResultRepository) -> None:
        self._repository = repository

    @classmethod
    def from_path(cls, root_dir: str | Path) -> "LocalResultService":
        return cls(LocalResultRepository(root_dir))

    def save_records(self, records: Sequence[SpectrumRecord], name: str | None = None) -> SavedResultDataset:
        return self._repository.save_records(tuple(records), name=name)

    def list_datasets(self) -> Sequence[SavedResultDataset]:
        return self._repository.list_datasets()

    def load_records(self, dataset_id: str) -> Sequence[SpectrumRecord]:
        return self._repository.load_records(dataset_id)
