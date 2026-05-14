"""Mixed-gas absorbance synthesis helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from spectra_sim.exceptions import SynthesisError
from spectra_sim.models import BaselineConfig, NoiseConfig
from spectra_sim.synthesis.baseline import evaluate_baseline
from spectra_sim.synthesis.noise import generate_noise


@dataclass(frozen=True)
class MixtureSynthesisResult:
    """Arrays produced after combining clean spectra with perturbations."""

    wavenumber: np.ndarray
    clean_absorbance: np.ndarray
    baseline: np.ndarray
    noise: np.ndarray
    final_absorbance: np.ndarray
    transmittance: np.ndarray


def synthesize_mixture_absorbance(
    wavenumber: np.ndarray,
    component_absorbances: Sequence[np.ndarray],
    baseline_config: BaselineConfig,
    noise_config: NoiseConfig,
) -> MixtureSynthesisResult:
    """Combine single-gas absorbance arrays and add baseline/noise components."""
    clean_absorbance = combine_component_absorbances(wavenumber, component_absorbances)
    baseline = evaluate_baseline(wavenumber, baseline_config, seed=noise_config.seed)
    noise = generate_noise(clean_absorbance + baseline, noise_config)
    final_absorbance = clean_absorbance + baseline + noise
    transmittance = np.exp(-clean_absorbance)
    return MixtureSynthesisResult(
        wavenumber=wavenumber,
        clean_absorbance=clean_absorbance,
        baseline=baseline,
        noise=noise,
        final_absorbance=final_absorbance,
        transmittance=transmittance,
    )


def combine_component_absorbances(
    wavenumber: np.ndarray,
    component_absorbances: Sequence[np.ndarray],
) -> np.ndarray:
    """Return the clean mixed absorbance as the sum of component absorbances."""
    clean_absorbance = np.zeros_like(wavenumber, dtype=float)
    for absorbance in component_absorbances:
        if absorbance.shape != wavenumber.shape:
            raise SynthesisError("Component absorbance length must match the wavenumber grid")
        clean_absorbance += absorbance
    return clean_absorbance
