"""Line-shape functions used by line-by-line synthesis."""

from __future__ import annotations

from enum import Enum

import numpy as np

MIN_HALF_WIDTH = 1.0e-12


class LineShapeType(str, Enum):
    """Supported P4 line-shape models."""

    LORENTZ = "lorentz"
    GAUSSIAN = "gaussian"
    PSEUDO_VOIGT = "pseudo_voigt"


def lorentz_profile(wavenumber: np.ndarray, center: float, gamma_hwhm: float) -> np.ndarray:
    """Return a normalized Lorentz profile."""
    gamma = max(float(gamma_hwhm), MIN_HALF_WIDTH)
    offset = wavenumber - center
    # Lorentz 线型面积归一化为 1，保证谱线强度只通过 line_intensity 控制总吸收面积。
    return (gamma / np.pi) / (offset * offset + gamma * gamma)


def gaussian_profile(wavenumber: np.ndarray, center: float, gaussian_hwhm: float) -> np.ndarray:
    """Return a normalized Gaussian profile."""
    hwhm = max(float(gaussian_hwhm), MIN_HALF_WIDTH)
    sigma = hwhm / np.sqrt(2.0 * np.log(2.0))
    offset = wavenumber - center
    return np.exp(-0.5 * (offset / sigma) ** 2) / (sigma * np.sqrt(2.0 * np.pi))


def pseudo_voigt_profile(
    wavenumber: np.ndarray,
    center: float,
    gaussian_hwhm: float,
    lorentz_hwhm: float,
) -> np.ndarray:
    """Return a normalized pseudo-Voigt profile."""
    gaussian_fwhm = max(2.0 * gaussian_hwhm, MIN_HALF_WIDTH)
    lorentz_fwhm = max(2.0 * lorentz_hwhm, MIN_HALF_WIDTH)

    # 采用常用 pseudo-Voigt FWHM/eta 近似，避免 P4 阶段强依赖 scipy.special.wofz。
    combined_fwhm = (
        gaussian_fwhm**5
        + 2.69269 * gaussian_fwhm**4 * lorentz_fwhm
        + 2.42843 * gaussian_fwhm**3 * lorentz_fwhm**2
        + 4.47163 * gaussian_fwhm**2 * lorentz_fwhm**3
        + 0.07842 * gaussian_fwhm * lorentz_fwhm**4
        + lorentz_fwhm**5
    ) ** 0.2
    ratio = lorentz_fwhm / combined_fwhm
    eta = 1.36603 * ratio - 0.47719 * ratio**2 + 0.11116 * ratio**3
    eta = float(np.clip(eta, 0.0, 1.0))

    combined_hwhm = combined_fwhm / 2.0
    return eta * lorentz_profile(wavenumber, center, combined_hwhm) + (1.0 - eta) * gaussian_profile(
        wavenumber,
        center,
        combined_hwhm,
    )


def evaluate_line_shape(
    line_shape: LineShapeType,
    wavenumber: np.ndarray,
    center: float,
    gaussian_hwhm: float,
    lorentz_hwhm: float,
) -> np.ndarray:
    """Evaluate one normalized line-shape function."""
    if line_shape is LineShapeType.LORENTZ:
        return lorentz_profile(wavenumber, center, lorentz_hwhm)
    if line_shape is LineShapeType.GAUSSIAN:
        return gaussian_profile(wavenumber, center, gaussian_hwhm)
    return pseudo_voigt_profile(wavenumber, center, gaussian_hwhm, lorentz_hwhm)

