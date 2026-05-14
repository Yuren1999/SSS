"""Shared enum definitions."""

from __future__ import annotations

from enum import Enum


class ConcentrationUnit(str, Enum):
    """Supported concentration units for gas components."""

    PPM = "ppm"
    PPB = "ppb"
    FRACTION = "fraction"
    PERCENT = "percent"


class PressureUnit(str, Enum):
    """Supported pressure units."""

    ATM = "atm"
    PA = "Pa"
    KPA = "kPa"


class PathLengthUnit(str, Enum):
    """Supported path length units."""

    CM = "cm"
    M = "m"


class GasRole(str, Enum):
    """Gas role in the training-data synthesis task."""

    RESIDENT = "resident"
    VARIABLE = "variable"


class NoiseType(str, Enum):
    """Supported first-version noise models."""

    NONE = "none"
    GAUSSIAN = "gaussian"
    UNIFORM = "uniform"
    RELATIVE = "relative"
    SPIKE = "spike"


class BaselineType(str, Enum):
    """Supported first-version baseline models."""

    NONE = "none"
    CONSTANT = "constant"
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    SINE = "sine"
    RANDOM_SMOOTH = "random_smooth"


class OutputFormat(str, Enum):
    """Dataset export formats."""

    CSV = "csv"
    NPZ = "npz"
    HDF5 = "hdf5"
    PARQUET = "parquet"


class DownloadMode(str, Enum):
    """How a download task should handle existing local coverage."""

    ADD_MISSING = "add_missing"
    OVERWRITE = "overwrite"
    SKIP_COVERED = "skip_covered"


class TaskStatus(str, Enum):
    """Generic task status for download and batch jobs."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

