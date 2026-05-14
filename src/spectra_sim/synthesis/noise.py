"""Noise perturbation models for synthesized absorbance spectra."""

from __future__ import annotations

import numpy as np

from spectra_sim.exceptions import SynthesisError
from spectra_sim.models import NoiseConfig, NoiseType


def generate_noise(signal: np.ndarray, config: NoiseConfig) -> np.ndarray:
    """Generate additive noise for an absorbance-like signal."""
    if config.noise_type is NoiseType.NONE:
        return np.zeros_like(signal, dtype=float)

    params = dict(config.parameters)
    rng = np.random.default_rng(config.seed)

    if config.noise_type is NoiseType.GAUSSIAN:
        mean = float(params.get("mean", params.get("offset", 0.0)))
        std = _first_available(params, ("std", "sigma", "amplitude"), 0.0)
        return rng.normal(loc=mean, scale=std, size=signal.shape)

    if config.noise_type is NoiseType.UNIFORM:
        amplitude = float(params.get("amplitude", 0.0))
        return rng.uniform(low=-amplitude, high=amplitude, size=signal.shape)

    if config.noise_type is NoiseType.RELATIVE:
        ratio = _first_available(params, ("ratio", "relative_std", "sigma"), 0.0)
        scale = ratio * np.abs(signal)
        return rng.normal(loc=0.0, scale=scale, size=signal.shape)

    if config.noise_type is NoiseType.SPIKE:
        probability = float(params.get("probability", 0.0))
        amplitude = float(params.get("amplitude", 0.0))
        mask = rng.random(size=signal.shape) < probability
        spikes = rng.uniform(low=-amplitude, high=amplitude, size=signal.shape)
        return np.where(mask, spikes, 0.0)

    raise SynthesisError(f"Unsupported noise type: {config.noise_type}")


def _first_available(params: dict[str, float], names: tuple[str, ...], default: float) -> float:
    for name in names:
        if name in params:
            return float(params[name])
    return default
