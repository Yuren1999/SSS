"""Baseline perturbation models for synthesized absorbance spectra."""

from __future__ import annotations

import math

import numpy as np

from spectra_sim.exceptions import SynthesisError
from spectra_sim.models import BaselineConfig, BaselineType


def evaluate_baseline(
    wavenumber: np.ndarray,
    config: BaselineConfig,
    seed: int | None = None,
) -> np.ndarray:
    """Evaluate the configured baseline component on a wavenumber grid."""
    if config.baseline_type is BaselineType.NONE:
        return np.zeros_like(wavenumber, dtype=float)

    params = dict(config.parameters)
    offset = float(params.get("offset", 0.0))

    if config.baseline_type is BaselineType.CONSTANT:
        return np.full_like(wavenumber, offset, dtype=float)

    if config.baseline_type is BaselineType.LINEAR:
        slope = float(params.get("slope", 0.0))
        return offset + slope * _centered_axis(wavenumber)

    if config.baseline_type is BaselineType.POLYNOMIAL:
        return _evaluate_polynomial_baseline(wavenumber, params)

    if config.baseline_type is BaselineType.SINE:
        return _evaluate_sine_baseline(wavenumber, params)

    if config.baseline_type is BaselineType.RANDOM_SMOOTH:
        return _evaluate_random_smooth_baseline(wavenumber, params, seed=seed)

    raise SynthesisError(f"Unsupported baseline type: {config.baseline_type}")


def _centered_axis(wavenumber: np.ndarray) -> np.ndarray:
    if wavenumber.size == 0:
        return np.array([], dtype=float)
    span = float(wavenumber[-1] - wavenumber[0])
    if span == 0:
        return np.zeros_like(wavenumber, dtype=float)
    midpoint = (float(wavenumber[0]) + float(wavenumber[-1])) / 2.0
    return (wavenumber - midpoint) / (span / 2.0)


def _unit_axis(wavenumber: np.ndarray) -> np.ndarray:
    if wavenumber.size == 0:
        return np.array([], dtype=float)
    span = float(wavenumber[-1] - wavenumber[0])
    if span == 0:
        return np.zeros_like(wavenumber, dtype=float)
    return (wavenumber - float(wavenumber[0])) / span


def _evaluate_polynomial_baseline(wavenumber: np.ndarray, params: dict[str, float]) -> np.ndarray:
    x = _centered_axis(wavenumber)
    coefficient_keys = [
        int(name[1:])
        for name in params
        if name.startswith("c") and name[1:].isdigit()
    ]
    max_degree = max(coefficient_keys, default=int(params.get("order", 0)))
    baseline = np.zeros_like(wavenumber, dtype=float)
    for degree in range(max_degree + 1):
        baseline += float(params.get(f"c{degree}", 0.0)) * x**degree
    return baseline


def _evaluate_sine_baseline(wavenumber: np.ndarray, params: dict[str, float]) -> np.ndarray:
    x = _unit_axis(wavenumber)
    offset = float(params.get("offset", 0.0))
    amplitude = float(params.get("amplitude", 0.0))
    frequency = float(params.get("frequency", 1.0))
    phase = float(params.get("phase", 0.0))
    return offset + amplitude * np.sin(2.0 * math.pi * frequency * x + phase)


def _evaluate_random_smooth_baseline(
    wavenumber: np.ndarray,
    params: dict[str, float],
    seed: int | None,
) -> np.ndarray:
    if wavenumber.size == 0:
        return np.array([], dtype=float)

    offset = float(params.get("offset", 0.0))
    amplitude = float(params.get("amplitude", 0.0))
    anchor_count = max(2, int(params.get("anchor_count", 8)))
    effective_seed = int(params["seed"]) if "seed" in params else seed

    rng = np.random.default_rng(effective_seed)
    anchors_x = np.linspace(0.0, 1.0, anchor_count)
    anchors_y = rng.normal(loc=0.0, scale=amplitude, size=anchor_count)
    return offset + np.interp(_unit_axis(wavenumber), anchors_x, anchors_y)
