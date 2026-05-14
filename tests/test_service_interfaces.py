import unittest

from spectra_sim.models import CoverageResult, GasSpec, WavenumberRange
from spectra_sim.services import LineDatabaseService, LocalLineDatabaseService
from spectra_sim.database import LineDatabaseRepository


class FakeLineDatabaseService:
    def list_gases(self):
        return [GasSpec("CO2", 2)]

    def get_coverage(self, gas_name):
        return [WavenumberRange(6000.0, 6500.0)]

    def check_coverage(self, gas_names, requested_range):
        return [
            CoverageResult(
                gas_name=gas_name,
                requested_range=requested_range,
                is_covered=True,
            )
            for gas_name in gas_names
        ]

    def search_lines(self, gas_name, requested_range):
        raise NotImplementedError


class ServiceInterfacesTestCase(unittest.TestCase):
    def test_database_service_protocol_accepts_matching_object(self) -> None:
        service = FakeLineDatabaseService()

        self.assertIsInstance(service, LineDatabaseService)

    def test_local_database_service_implements_protocol(self) -> None:
        service = LocalLineDatabaseService(LineDatabaseRepository("unused.sqlite"))

        self.assertIsInstance(service, LineDatabaseService)


if __name__ == "__main__":
    unittest.main()
