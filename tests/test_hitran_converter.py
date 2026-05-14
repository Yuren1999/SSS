import unittest

from spectra_sim.exceptions import DownloadError
from spectra_sim.hitran import convert_hapi_columns


class HapiConverterTestCase(unittest.TestCase):
    def test_convert_hapi_columns_to_line_records(self) -> None:
        records = convert_hapi_columns(
            "CO2",
            {
                "nu": [6100.0, 6200.0],
                "sw": [1.0, 2.0],
                "gamma_air": [0.1, 0.2],
                "gamma_self": [0.01, 0.02],
                "elower": [10.0, 20.0],
                "n_air": [0.7, 0.8],
                "delta_air": [0.0, -0.001],
            },
        )

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].gas_name, "CO2")
        self.assertEqual(records[1].wavenumber, 6200.0)

    def test_convert_hapi_columns_rejects_missing_field(self) -> None:
        with self.assertRaises(DownloadError):
            convert_hapi_columns("CO2", {"nu": [6100.0]})


if __name__ == "__main__":
    unittest.main()

