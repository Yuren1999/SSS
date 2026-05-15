"""Project-wide exception types."""

from __future__ import annotations

from dataclasses import dataclass


class SpectraSimulatorError(Exception):
    """Base class for all domain errors raised by the project."""


class ValidationError(SpectraSimulatorError):
    """Raised when user input or a config object violates domain rules."""


class DatabaseError(SpectraSimulatorError):
    """Raised when the local spectral line database cannot complete an operation."""


class DownloadError(SpectraSimulatorError):
    """Raised when HITRAN/HAPI download fails."""


class SynthesisError(SpectraSimulatorError):
    """Raised when spectrum synthesis fails."""


class BatchError(SpectraSimulatorError):
    """Raised when a batch synthesis task cannot be managed."""


class ExportError(SpectraSimulatorError):
    """Raised when dataset export fails."""


@dataclass
class CoverageError(SpectraSimulatorError):
    """Raised when the local line database does not cover a requested range."""

    gas_name: str
    message: str

    def __str__(self) -> str:
        return f"{self.gas_name}: {self.message}"
