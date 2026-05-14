"""Spectrum synthesis calculation package."""

from spectra_sim.synthesis.grid import build_wavenumber_grid
from spectra_sim.synthesis.line_shape import LineShapeType, evaluate_line_shape, gaussian_profile, lorentz_profile
from spectra_sim.synthesis.absorbance import (
    SingleGasSynthesisResult,
    concentration_to_fraction,
    number_density_cm3,
    path_length_to_cm,
    pressure_to_atm,
    synthesize_single_gas_absorbance,
)
from spectra_sim.synthesis.baseline import evaluate_baseline
from spectra_sim.synthesis.mixture import (
    MixtureSynthesisResult,
    combine_component_absorbances,
    synthesize_mixture_absorbance,
)
from spectra_sim.synthesis.noise import generate_noise

__all__ = [
    "LineShapeType",
    "MixtureSynthesisResult",
    "SingleGasSynthesisResult",
    "build_wavenumber_grid",
    "combine_component_absorbances",
    "concentration_to_fraction",
    "evaluate_line_shape",
    "evaluate_baseline",
    "gaussian_profile",
    "generate_noise",
    "lorentz_profile",
    "number_density_cm3",
    "path_length_to_cm",
    "pressure_to_atm",
    "synthesize_mixture_absorbance",
    "synthesize_single_gas_absorbance",
]
