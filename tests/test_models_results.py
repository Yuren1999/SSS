import unittest

from spectra_sim.exceptions import ValidationError
from spectra_sim.models import SpectrumLabels, SpectrumRecord


class ResultModelsTestCase(unittest.TestCase):
    def test_labels_reject_absent_variable_with_nonzero_concentration(self) -> None:
        with self.assertRaises(ValidationError):
            SpectrumLabels(variable_presence={"CH4": 0}, variable_concentrations={"CH4": 2.0})

    def test_spectrum_record_requires_matching_lengths(self) -> None:
        with self.assertRaises(ValidationError):
            SpectrumRecord(
                sample_id="sample-1",
                wavenumber=(6000.0, 6000.1),
                clean_absorbance=(0.1,),
            )

    def test_spectrum_record_accepts_consistent_components(self) -> None:
        record = SpectrumRecord(
            sample_id="sample-1",
            wavenumber=(6000.0, 6000.1),
            clean_absorbance=(0.1, 0.2),
            final_absorbance=(0.11, 0.21),
        )

        self.assertEqual(len(record.wavenumber), 2)
        self.assertEqual(record.final_absorbance, (0.11, 0.21))


if __name__ == "__main__":
    unittest.main()

