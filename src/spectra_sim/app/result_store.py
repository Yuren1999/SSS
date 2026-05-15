"""In-memory result store shared by GUI pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from spectra_sim.models import SpectrumRecord


@dataclass
class ResultStore:
    """Current-session synthesized records and export path."""

    records: tuple[SpectrumRecord, ...] = field(default_factory=tuple)
    last_export_path: Path | None = None

    def set_records(self, records: Sequence[SpectrumRecord]) -> None:
        self.records = tuple(records)

    def clear(self) -> None:
        self.records = ()
        self.last_export_path = None

    def set_last_export_path(self, path: Path) -> None:
        self.last_export_path = path
