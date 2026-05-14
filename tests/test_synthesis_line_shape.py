import unittest

import numpy as np

from spectra_sim.synthesis.line_shape import gaussian_profile, lorentz_profile, pseudo_voigt_profile


class LineShapeTestCase(unittest.TestCase):
    def test_lorentz_profile_is_symmetric(self) -> None:
        wavenumber = np.array([-1.0, 0.0, 1.0])
        profile = lorentz_profile(wavenumber, center=0.0, gamma_hwhm=0.2)

        self.assertAlmostEqual(profile[0], profile[2])
        self.assertGreater(profile[1], profile[0])

    def test_gaussian_profile_area_is_close_to_one_on_wide_grid(self) -> None:
        wavenumber = np.linspace(-10.0, 10.0, 20001)
        profile = gaussian_profile(wavenumber, center=0.0, gaussian_hwhm=0.5)

        self.assertAlmostEqual(float(np.trapezoid(profile, wavenumber)), 1.0, places=3)

    def test_pseudo_voigt_profile_is_non_negative(self) -> None:
        wavenumber = np.linspace(-5.0, 5.0, 1001)
        profile = pseudo_voigt_profile(wavenumber, center=0.0, gaussian_hwhm=0.2, lorentz_hwhm=0.1)

        self.assertTrue(np.all(profile >= 0))


if __name__ == "__main__":
    unittest.main()

