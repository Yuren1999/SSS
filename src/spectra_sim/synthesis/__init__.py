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

__all__ = [
    "LineShapeType",
    "SingleGasSynthesisResult",
    "build_wavenumber_grid",
    "concentration_to_fraction",
    "evaluate_line_shape",
    "gaussian_profile",
    "lorentz_profile",
    "number_density_cm3",
    "path_length_to_cm",
    "pressure_to_atm",
    "synthesize_single_gas_absorbance",
]
