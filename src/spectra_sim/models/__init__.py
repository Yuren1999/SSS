"""Shared application data models."""

from spectra_sim.models.app import AppInfo
from spectra_sim.models.config import (
    BaselineConfig,
    EnvironmentConfig,
    GasComponent,
    NoiseConfig,
    OutputConfig,
    SynthesisConfig,
)
from spectra_sim.models.enums import (
    BaselineType,
    ConcentrationUnit,
    DownloadMode,
    GasRole,
    NoiseType,
    OutputFormat,
    PathLengthUnit,
    PressureUnit,
    TaskStatus,
)
from spectra_sim.models.results import SpectrumLabels, SpectrumRecord
from spectra_sim.models.spectral import GasSpec, LineRecord, LineTable, SpectralAxisConfig, WavenumberRange
from spectra_sim.models.tasks import (
    BatchSampleFailure,
    BatchTaskResult,
    CoverageResult,
    DownloadTaskInfo,
    DownloadTaskRequest,
)

__all__ = [
    "AppInfo",
    "BaselineConfig",
    "BaselineType",
    "BatchSampleFailure",
    "BatchTaskResult",
    "ConcentrationUnit",
    "CoverageResult",
    "DownloadMode",
    "DownloadTaskInfo",
    "DownloadTaskRequest",
    "EnvironmentConfig",
    "GasComponent",
    "GasRole",
    "GasSpec",
    "LineRecord",
    "LineTable",
    "NoiseConfig",
    "NoiseType",
    "OutputConfig",
    "OutputFormat",
    "PathLengthUnit",
    "PressureUnit",
    "SpectralAxisConfig",
    "SpectrumLabels",
    "SpectrumRecord",
    "SynthesisConfig",
    "TaskStatus",
    "WavenumberRange",
]
