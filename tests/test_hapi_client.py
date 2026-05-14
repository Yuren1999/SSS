import unittest
from pathlib import Path

from spectra_sim.hitran import DEFAULT_LOCAL_ISOTOPOLOGUE_ID, HapiLineDownloader
from spectra_sim.models import GasSpec, WavenumberRange


class FakeHapiModule:
    def __init__(self) -> None:
        self.db_path = None
        self.fetch_args = None
        self.columns = {
            "nu": [6100.0],
            "sw": [1.0],
            "gamma_air": [0.1],
            "gamma_self": [0.01],
            "elower": [10.0],
            "n_air": [0.7],
            "delta_air": [0.0],
        }

    def db_begin(self, db_path):
        self.db_path = db_path

    def fetch(self, *args):
        self.fetch_args = args

    def getColumn(self, table_name, column_name):
        return self.columns[column_name]


class HapiLineDownloaderTestCase(unittest.TestCase):
    def test_download_lines_calls_hapi_fetch_and_converts_columns(self) -> None:
        fake_hapi = FakeHapiModule()
        downloader = HapiLineDownloader(Path("hapi-cache"), hapi_module=fake_hapi)

        records = downloader.download_lines(GasSpec("CO2", 2), WavenumberRange(6000.0, 6500.0))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].wavenumber, 6100.0)
        self.assertEqual(fake_hapi.fetch_args[1], 2)
        self.assertEqual(fake_hapi.fetch_args[2], DEFAULT_LOCAL_ISOTOPOLOGUE_ID)
        self.assertEqual(fake_hapi.fetch_args[3], 6000.0)
        self.assertEqual(fake_hapi.fetch_args[4], 6500.0)


if __name__ == "__main__":
    unittest.main()

