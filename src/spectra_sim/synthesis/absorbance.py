"""Single-gas line-by-line absorbance synthesis."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from spectra_sim.exceptions import SynthesisError
from spectra_sim.models import (
    ConcentrationUnit,
    EnvironmentConfig,
    GasComponent,
    LineRecord,
    PathLengthUnit,
    PressureUnit,
)
from spectra_sim.synthesis.line_shape import LineShapeType, evaluate_line_shape

REFERENCE_TEMPERATURE_K = 296.0
REFERENCE_PRESSURE_ATM = 1.0
SECOND_RADIATION_CONSTANT_CM_K = 1.438776877
BOLTZMANN_CONSTANT_J_K = 1.380649e-23
ATM_TO_PA = 101325.0


@dataclass(frozen=True)
class SingleGasSynthesisResult:
    """Raw arrays produced by single-gas synthesis."""

    wavenumber: np.ndarray
    absorption_coefficient: np.ndarray
    absorbance: np.ndarray
    transmittance: np.ndarray


def synthesize_single_gas_absorbance(
    wavenumber: np.ndarray,
    records: tuple[LineRecord, ...],
    component: GasComponent,
    environment: EnvironmentConfig,
    nu_step: float,
    line_shape: LineShapeType = LineShapeType.PSEUDO_VOIGT,
) -> SingleGasSynthesisResult:
    """Synthesize clean absorbance and transmittance for one gas."""
    if component.concentration == 0 or not component.presence:
        zeros = np.zeros_like(wavenumber, dtype=float)
        return SingleGasSynthesisResult(wavenumber, zeros, zeros, np.ones_like(wavenumber, dtype=float))

    pressure_atm = pressure_to_atm(environment)
    path_length_cm = path_length_to_cm(environment)
    number_density = number_density_cm3(environment)
    concentration_fraction = concentration_to_fraction(component)

    absorption_coefficient = np.zeros_like(wavenumber, dtype=float)
    gaussian_hwhm = max(nu_step / 2.0, 1.0e-6)

    for record in records:
        # 谱线强度按温度修正后乘以归一化线型，得到该谱线对吸收截面的贡献。
        line_strength = temperature_correct_line_intensity(record, environment.temperature)
        lorentz_hwhm = pressure_broadened_hwhm(record, pressure_atm, environment.temperature)
        profile = evaluate_line_shape(
            line_shape=line_shape,
            wavenumber=wavenumber,
            center=record.wavenumber + record.pressure_shift * pressure_atm,
            gaussian_hwhm=gaussian_hwhm,
            lorentz_hwhm=lorentz_hwhm,
        )
        absorption_coefficient += number_density * concentration_fraction * line_strength * profile

    # Beer-Lambert: A(nu)=alpha(nu)*L，T(nu)=exp(-A)。alpha 单位按 cm^-1 组织，L 使用 cm。
    absorbance = absorption_coefficient * path_length_cm
    transmittance = np.exp(-absorbance)
    return SingleGasSynthesisResult(wavenumber, absorption_coefficient, absorbance, transmittance)


def concentration_to_fraction(component: GasComponent) -> float:
    """Convert supported concentration units into volume fraction."""
    value = component.concentration
    if component.concentration_unit is ConcentrationUnit.PPM:
        return value * 1.0e-6
    if component.concentration_unit is ConcentrationUnit.PPB:
        return value * 1.0e-9
    if component.concentration_unit is ConcentrationUnit.PERCENT:
        return value / 100.0
    if component.concentration_unit is ConcentrationUnit.FRACTION:
        if value > 1:
            raise SynthesisError("体积分数浓度不能大于 1")
        return value
    raise SynthesisError(f"不支持的浓度单位：{component.concentration_unit}")


def pressure_to_atm(environment: EnvironmentConfig) -> float:
    """Convert pressure into atm."""
    pressure = environment.pressure
    if environment.pressure_unit is PressureUnit.ATM:
        return pressure
    if environment.pressure_unit is PressureUnit.PA:
        return pressure / ATM_TO_PA
    if environment.pressure_unit is PressureUnit.KPA:
        return pressure * 1000.0 / ATM_TO_PA
    raise SynthesisError(f"不支持的压力单位：{environment.pressure_unit}")


def path_length_to_cm(environment: EnvironmentConfig) -> float:
    """Convert path length into cm."""
    if environment.path_length_unit is PathLengthUnit.CM:
        return environment.path_length
    if environment.path_length_unit is PathLengthUnit.M:
        return environment.path_length * 100.0
    raise SynthesisError(f"不支持的光程单位：{environment.path_length_unit}")


def number_density_cm3(environment: EnvironmentConfig) -> float:
    """Return ideal-gas number density in molecules/cm^3."""
    pressure_pa = pressure_to_atm(environment) * ATM_TO_PA
    # 理想气体数密度 n=P/(k_B*T)，从 m^-3 转为 cm^-3 需除以 1e6。
    return pressure_pa / (BOLTZMANN_CONSTANT_J_K * environment.temperature) / 1.0e6


def temperature_correct_line_intensity(record: LineRecord, temperature: float) -> float:
    """Apply a first-version HITRAN-style temperature correction."""
    if temperature <= 0:
        raise SynthesisError("温度必须大于 0 K")
    if record.line_intensity == 0:
        return 0.0

    nu = record.wavenumber
    lower_energy = record.lower_state_energy
    exponent = -SECOND_RADIATION_CONSTANT_CM_K * lower_energy * (1.0 / temperature - 1.0 / REFERENCE_TEMPERATURE_K)

    # 当前阶段未接入分子配分函数 Q(T)，先使用 Q(296K)/Q(T)=1；后续可由 HAPI/TIPS 补充。
    stimulated_emission = _safe_stimulated_emission_ratio(nu, temperature)
    return record.line_intensity * math.exp(exponent) * stimulated_emission


def pressure_broadened_hwhm(record: LineRecord, pressure_atm: float, temperature: float) -> float:
    """Return pressure-broadened Lorentz half width at half maximum."""
    if pressure_atm <= 0:
        raise SynthesisError("压力必须为正数")
    temperature_power = (REFERENCE_TEMPERATURE_K / temperature) ** record.temperature_dependence
    gamma = record.air_width * (pressure_atm / REFERENCE_PRESSURE_ATM) * temperature_power
    return max(gamma, 1.0e-9)


def _safe_stimulated_emission_ratio(wavenumber: float, temperature: float) -> float:
    numerator = 1.0 - math.exp(-SECOND_RADIATION_CONSTANT_CM_K * wavenumber / temperature)
    denominator = 1.0 - math.exp(-SECOND_RADIATION_CONSTANT_CM_K * wavenumber / REFERENCE_TEMPERATURE_K)
    if denominator == 0:
        return 1.0
    return numerator / denominator

