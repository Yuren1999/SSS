"""Reusable validation rules for GUI and service-layer inputs."""

from __future__ import annotations

from spectra_sim.exceptions import ValidationError
from spectra_sim.models import EnvironmentConfig, GasComponent, SynthesisConfig, WavenumberRange


def validate_positive(value: float, field_name: str) -> float:
    """Require a strictly positive numeric value."""
    if value <= 0:
        raise ValidationError(f"{field_name} 必须为正数")
    return value


def validate_non_negative(value: float, field_name: str) -> float:
    """Require a zero-or-positive numeric value."""
    if value < 0:
        raise ValidationError(f"{field_name} 不得为负")
    return value


def validate_wavenumber_range(nu_min: float, nu_max: float) -> WavenumberRange:
    """Validate and return an ascending wavenumber range in cm^-1."""
    # 波数范围是下载、检索和合成共用参数，统一在这里转换为模型对象。
    return WavenumberRange(nu_min=nu_min, nu_max=nu_max)


def validate_environment(environment: EnvironmentConfig) -> EnvironmentConfig:
    """Validate environment parameters used by spectral synthesis."""
    validate_positive(environment.pressure, "压力")
    validate_positive(environment.temperature, "温度")
    validate_positive(environment.path_length, "吸收光程")
    if environment.temperature_unit != "K":
        raise ValidationError("温度单位当前仅支持 K")
    return environment


def validate_gas_component(component: GasComponent) -> GasComponent:
    """Validate one resident or variable gas component."""
    if not component.name.strip():
        raise ValidationError("气体组分名称不能为空")
    validate_non_negative(component.concentration, "气体浓度")
    if not component.presence and component.concentration != 0:
        raise ValidationError("变量组分不存在时浓度必须为 0")
    return component


def validate_synthesis_config(config: SynthesisConfig) -> SynthesisConfig:
    """Validate a complete synthesis configuration object."""
    validate_environment(config.environment)

    # 合成配置至少需要一个组分；常驻和变量组分的角色约束由模型层负责。
    if not config.resident_gases and not config.variable_gases:
        raise ValidationError("至少需要配置一种气体组分")

    for component in (*config.resident_gases, *config.variable_gases):
        validate_gas_component(component)

    return config

