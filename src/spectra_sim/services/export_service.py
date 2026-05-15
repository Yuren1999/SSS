"""Concrete export service implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from spectra_sim.io import export_spectra
from spectra_sim.models import OutputConfig, SpectrumRecord


class LocalExportService:
    """Export service that writes synthesized datasets to local files."""

    def export_spectra(self, records: Sequence[SpectrumRecord], output_config: OutputConfig) -> Path:
        return export_spectra(records, output_config)
