"""Minimal DuckDB runtime for Dex local analysis state."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

DEFAULT_STATE_DIR = ".dex"
DEFAULT_DATABASE_NAME = "dex.duckdb"
TRANSIENT_TABLE_PREFIX = "dex_temp_"


@dataclass(frozen=True)
class DexPaths:
    """Resolved paths for Dex's repo-local durable state."""

    workspace: Path
    state_dir: Path
    database_path: Path
    artifacts_dir: Path
    cache_dir: Path

    @classmethod
    def for_workspace(cls, workspace: str | Path = ".") -> "DexPaths":
        root = Path(workspace).expanduser().resolve()
        state_dir = root / DEFAULT_STATE_DIR
        return cls(
            workspace=root,
            state_dir=state_dir,
            database_path=state_dir / DEFAULT_DATABASE_NAME,
            artifacts_dir=state_dir / "artifacts",
            cache_dir=state_dir / "cache",
        )

    def ensure(self) -> None:
        """Create durable Dex directories without writing credentials or data sources."""

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


class DuckDBRuntime:
    """Small wrapper around a repo-local DuckDB connection.

    Durable Dex state lives in `.dex/dex.duckdb`. Transient analysis scratch
    objects should be created as DuckDB temporary tables with the `dex_temp_`
    prefix; durable artifacts should be written as explicit files under
    `.dex/artifacts/` by higher-level code.
    """

    def __init__(self, paths: DexPaths, *, read_only: bool = False) -> None:
        self.paths = paths
        self.read_only = read_only
        if not read_only:
            self.paths.ensure()
        self._connection = duckdb.connect(str(paths.database_path), read_only=read_only)

    @classmethod
    def open(
        cls,
        workspace: str | Path = ".",
        *,
        read_only: bool = False,
    ) -> "DuckDBRuntime":
        """Open Dex's DuckDB state for a workspace."""

        return cls(DexPaths.for_workspace(workspace), read_only=read_only)

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Expose the underlying connection for advanced callers."""

        return self._connection

    def execute(
        self,
        sql: str,
        parameters: Sequence[Any] | dict[str, Any] | None = None,
    ) -> duckdb.DuckDBPyConnection:
        """Execute SQL against the local DuckDB database.

        The runtime does not accept or persist credentials. Callers must keep
        connector credentials in external systems such as environment variables,
        DuckDB's credential chain, or system credential stores.
        """

        if parameters is None:
            return self._connection.execute(sql)
        return self._connection.execute(sql, parameters)

    def query_all(
        self,
        sql: str,
        parameters: Sequence[Any] | dict[str, Any] | None = None,
    ) -> list[tuple[Any, ...]]:
        """Execute a query and return all rows as tuples."""

        return self.execute(sql, parameters).fetchall()

    def create_transient_table(self, name: str, query: str) -> None:
        """Create a temporary analysis table with Dex's transient prefix."""

        safe_name = _validate_identifier(name)
        self.execute(
            f"CREATE OR REPLACE TEMP TABLE {TRANSIENT_TABLE_PREFIX}{safe_name} AS {query}"
        )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "DuckDBRuntime":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def open_runtime(
    workspace: str | Path = ".",
    *,
    read_only: bool = False,
) -> DuckDBRuntime:
    """Convenience function for opening Dex's runtime."""

    return DuckDBRuntime.open(workspace, read_only=read_only)


def runtime_paths(workspace: str | Path = ".") -> DexPaths:
    """Return Dex's durable state paths for a workspace without creating them."""

    return DexPaths.for_workspace(workspace)


def _validate_identifier(identifier: str) -> str:
    if not identifier:
        msg = "identifier must not be empty"
        raise ValueError(msg)
    if not identifier.replace("_", "").isalnum() or identifier[0].isdigit():
        msg = f"unsafe DuckDB identifier: {identifier!r}"
        raise ValueError(msg)
    return identifier
