import sqlite3
import tempfile
import unittest
from pathlib import Path

from spectra_sim.database.schema import SCHEMA_VERSION, initialize_database


class DatabaseSchemaTestCase(unittest.TestCase):
    def test_initialize_database_creates_core_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "lines.sqlite"

            initialize_database(db_path)

            connection = sqlite3.connect(db_path)
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                version = connection.execute(
                    "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
                ).fetchone()[0]
            finally:
                connection.close()

            self.assertIn("gas_catalog", tables)
            self.assertIn("line_coverage", tables)
            self.assertIn("spectral_lines", tables)
            self.assertIn("download_tasks", tables)
            self.assertEqual(version, SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
