"""Core spectral-line and axis data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from spectra_sim.exceptions import ValidationError


@dataclass(frozen=True)
class WavenumberRange:
    """Wavenumber range in cm^-1."""

    nu_min: float
    nu_max: float

    def __post_init__(self) -> None:
        # 波数范围是所有下载、检索和合成任务的公共边界，必须在模型层保证为正向区间。
        if self.nu_min <= 0 or self.nu_max <= 0:
            raise ValidationError("波数范围必须为正数")
        if self.nu_min >= self.nu_max:
            raise ValidationError("nu_min 必须小于 nu_max")

    @property
    def width(self) -> float:
        return self.nu_max - self.nu_min

    def contains(self, value: float) -> bool:
        return self.nu_min <= value <= self.nu_max

    @classmethod
    def from_bounds(cls, first: float, second: float) -> "WavenumberRange":
        # 外部输入可能先后顺序不固定，统一转换为升序区间后再进入业务层。
        nu_min, nu_max = sorted((first, second))
        return cls(nu_min=nu_min, nu_max=nu_max)


@dataclass(frozen=True)
class GasSpec:
    """Gas identity used by HITRAN download and local storage."""

    gas_name: str
    hitran_molecule_id: int

    def __post_init__(self) -> None:
        if not self.gas_name.strip():
            raise ValidationError("气体名称不能为空")
        if self.hitran_molecule_id <= 0:
            raise ValidationError("HITRAN 分子编号必须为正整数")


@dataclass(frozen=True)
class SpectralAxisConfig:
    """Uniform wavenumber grid configuration."""

    wavenumber_range: WavenumberRange
    nu_step: float

    def __post_init__(self) -> None:
        # nu_step 是输出采样间隔，不表示仪器线型或仪器分辨率。
        if self.nu_step <= 0:
            raise ValidationError("波数采样间隔必须为正数")
        if self.nu_step > self.wavenumber_range.width:
            raise ValidationError("波数采样间隔不能大于波数范围宽度")


@dataclass(frozen=True)
class LineRecord:
    """Single line-by-line record in the internal standard field format."""

    gas_name: str
    wavenumber: float
    line_intensity: float
    air_width: float
    self_width: float
    lower_state_energy: float
    temperature_dependence: float
    pressure_shift: float

    def __post_init__(self) -> None:
        # 这里校验内部标准字段，避免 HAPI 字段转换错误进入后续物理计算。
        if not self.gas_name.strip():
            raise ValidationError("谱线记录的气体名称不能为空")
        if self.wavenumber <= 0:
            raise ValidationError("谱线中心波数必须为正数")
        if self.line_intensity < 0:
            raise ValidationError("谱线强度不得为负")
        if self.air_width < 0 or self.self_width < 0:
            raise ValidationError("谱线展宽参数不得为负")


@dataclass(frozen=True)
class LineTable:
    """Collection of spectral lines returned by local database search."""

    gas: GasSpec
    wavenumber_range: WavenumberRange
    records: Sequence[LineRecord] = field(default_factory=tuple)
    source: str = "local"
    downloaded_at: str | None = None

    def __post_init__(self) -> None:
        records = tuple(self.records)
        object.__setattr__(self, "records", records)

        for record in records:
            if record.gas_name != self.gas.gas_name:
                raise ValidationError("谱线记录气体名称与 LineTable 气体不一致")
            if not self.wavenumber_range.contains(record.wavenumber):
                raise ValidationError("谱线记录超出 LineTable 波数范围")

