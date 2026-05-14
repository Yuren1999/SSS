import logging
import tempfile
import unittest
from pathlib import Path

from spectra_sim.config.logging_config import configure_logging


class LoggingConfigTestCase(unittest.TestCase):
    def test_configure_logging_creates_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                log_file = configure_logging(Path(temp_dir), level=logging.DEBUG)

                self.assertTrue(log_file.exists())
                self.assertEqual(log_file.name, "spectra_simulator.log")
            finally:
                # Windows 下 FileHandler 会持有文件句柄，测试结束前需要显式释放。
                logging.shutdown()


if __name__ == "__main__":
    unittest.main()
