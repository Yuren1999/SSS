"""Synthesis configuration data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from spectra_sim.exceptions import ValidationError
from spectra_sim.models.enums import (
    BaselineType,
    ConcentrationUnit,
    GasRole,
    NoiseType,
    OutputFormat,
    PathLengthUnit,
    PressureUnit,
)
from spectra_sim.models.spectral import SpectralAxisConfig


@dataclass(frozen=True)
class EnvironmentConfig:
    """Shared environment parameters for one synthesis run."""

    pressure: float
    temperature: float
    path_length: float
    pressure_unit: PressureUnit = PressureUnit.ATM
    temperature_unit: str = "K"
    path_length_unit: PathLengthUnit = PathLengthUnit.CM

    def __post_init__(self) -> None:
        # 温度、压力和光程直接进入 Beer-Lambert 计算与谱线修正，不能允许非物理取值。
        if self.pressure <= 0:
            raise ValidationError("压力必须为正数")
        if self.temperature <= 0:
            raise ValidationError("温度必须大于 0 K")
        if self.path_length <= 0:
            raise ValidationError("吸收光程必须为正数")
        if self.temperature_unit != "K":
            raise ValidationError("温度单位当前仅支持 K")


@dataclass(frozen=True)
class GasComponent:
    """Gas component and its label-related metadata."""

    name: str
    concentration: float
    concentration_unit: ConcentrationUnit = ConcentrationUnit.PPM
    role: GasRole = GasRole.VARIABLE
    presence: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("组分名称不能为空")
        if self.concentration < 0:
            raise ValidationError("气体浓度不得为负")
        if not self.presence and self.concentration != 0:
            raise ValidationError("变量组分不存在时浓度必须为 0")


@dataclass(frozen=True)
class NoiseConfig:
    """Noise model configuration."""

    noise_type: NoiseType = NoiseType.NONE
    parameters: Mapping[str, float] = field(default_factory=dict)
    seed: int | None = None

    def __post_init__(self) -> None:
        params = dict(self.parameters)
        object.__setattr__(self, "parameters", params)
        if self.seed is not None and self.seed < 0:
            raise ValidationError("随机种子不得为负")
        for name, value in params.items():
            if value < 0 and name.lower() not in {"offset", "slope", "phase"}:
                raise ValidationError(f"噪声参数 {name} 不得为负")


@dataclass(frozen=True)
class BaselineConfig:
    """Baseline model configuration."""

    baseline_type: BaselineType = BaselineType.NONE
    parameters: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        params = dict(self.parameters)
        object.__setattr__(self, "parameters", params)
        order = params.get("order")
        if order is not None and order < 0:
            raise ValidationError("多项式基线阶数不得为负")


@dataclass(frozen=True)
class OutputConfig:
    """Dataset output options."""

    output_format: OutputFormat = OutputFormat.HDF5
    output_dir: str | None = None


@dataclass(frozen=True)
class SynthesisConfig:
    """Complete configuration for single or mixture spectrum synthesis."""

    spectral_axis: SpectralAxisConfig
    environment: EnvironmentConfig
    resident_gases: tuple[GasComponent, ...] = field(default_factory=tuple)
    variable_gases: tuple[GasComponent, ...] = field(default_factory=tuple)
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    baseline: BaselineConfig = field(default_factory=BaselineConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def __post_init__(self) -> None:
        resident_gases = tuple(self.resident_gases)
        variable_gases = tuple(self.variable_gases)
        object.__setattr__(self, "resident_gases", resident_gases)
        object.__setattr__(self, "variable_gases", variable_gases)

        if not resident_gases and not variable_gases:
            raise ValidationError("至少需要配置一种气体组分")

        for gas in resident_gases:
            if gas.role is not GasRole.RESIDENT:
                raise ValidationError("resident_gases 中只能包含常驻组分")
        for gas in variable_gases:
            if gas.role is not GasRole.VARIABLE:
                raise ValidationError("variable_gases 中只能包含变量组分")
