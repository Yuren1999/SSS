"""Local spectral line database package."""

from spectra_sim.database.coverage import covers_range, merge_ranges, missing_ranges
from spectra_sim.database.repository import LineDatabaseRepository
from spectra_sim.database.schema import SCHEMA_VERSION, connect_database, database_connection, initialize_database

__all__ = [
    "LineDatabaseRepository",
    "SCHEMA_VERSION",
    "connect_database",
    "database_connection",
    "covers_range",
    "initialize_database",
    "merge_ranges",
    "missing_ranges",
]
