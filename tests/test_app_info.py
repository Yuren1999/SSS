import unittest

from spectra_sim.models import AppInfo


class AppInfoTestCase(unittest.TestCase):
    def test_default_app_info(self) -> None:
        app_info = AppInfo.default()

        self.assertEqual(app_info.name, "吸收光谱数据模拟软件")
        self.assertEqual(app_info.version, "0.1.0")
        self.assertEqual(app_info.organization, "SSS")


if __name__ == "__main__":
    unittest.main()

