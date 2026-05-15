"""Spectrum output and label data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from spectra_sim.exceptions import ValidationError


def _as_float_tuple(values: Sequence[float] | None) -> tuple[float, ...]:
    return tuple(values or ())


@dataclass(frozen=True)
class SpectrumLabels:
    """Labels used by multi-task recognition model training."""

    resident_concentrations: Mapping[str, float] = field(default_factory=dict)
    variable_presence: Mapping[str, int] = field(default_factory=dict)
    variable_concentrations: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        resident = dict(self.resident_concentrations)
        presence = dict(self.variable_presence)
        variable = dict(self.variable_concentrations)
        object.__setattr__(self, "resident_concentrations", resident)
        object.__setattr__(self, "variable_presence", presence)
        object.__setattr__(self, "variable_concentrations", variable)

        for gas_name, flag in presence.items():
            if flag not in {0, 1}:
                raise ValidationError(f"{gas_name} 的存在性标签必须为 0 或 1")
            if flag == 0 and variable.get(gas_name, 0) != 0:
                raise ValidationError(f"{gas_name} 不存在时浓度标签必须为 0")


@dataclass(frozen=True)
class SpectrumRecord:
    """One synthesized spectrum and its supervised labels."""

    sample_id: str
    wavenumber: Sequence[float]
    clean_absorbance: Sequence[float]
    baseline: Sequence[float] = field(default_factory=tuple)
    noise: Sequence[float] = field(default_factory=tuple)
    final_absorbance: Sequence[float] = field(default_factory=tuple)
    transmittance: Sequence[float] = field(default_factory=tuple)
    labels: SpectrumLabels = field(default_factory=SpectrumLabels)
    metadata: Mapping[str, str | int | float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.sample_id.strip():
            raise ValidationError("样本编号不能为空")

        # 所有光谱分量必须与波数轴等长，保证后续导出和训练张量组织不会错位。
        wavenumber = _as_float_tuple(self.wavenumber)
        if not wavenumber:
            raise ValidationError("波数轴不能为空")
        object.__setattr__(self, "wavenumber", wavenumber)

        expected_length = len(wavenumber)
        for field_name in (
            "clean_absorbance",
            "baseline",
            "noise",
            "final_absorbance",
            "transmittance",
        ):
            values = _as_float_tuple(getattr(self, field_name))
            if values and len(values) != expected_length:
                raise ValidationError(f"{field_name} 长度必须与波数轴一致")
            object.__setattr__(self, field_name, values)

        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True)
class SavedResultDataset:
    """Persisted synthesized result dataset metadata."""

    dataset_id: str
    name: str
    record_count: int
    storage_path: Path
    created_at: str

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise ValidationError("dataset id must not be empty")
        if not self.name.strip():
            raise ValidationError("dataset name must not be empty")
        if self.record_count < 0:
            raise ValidationError("record count must be non-negative")
        object.__setattr__(self, "storage_path", Path(self.storage_path))
