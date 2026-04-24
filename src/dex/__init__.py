"""Dex: a Pi-native data analyst field companion."""

__all__ = ["__version__", "open_runtime", "FieldNotesStore"]

__version__ = "0.1.0"

from .duckdb_runtime import open_runtime
from .field_notes import FieldNotesStore
