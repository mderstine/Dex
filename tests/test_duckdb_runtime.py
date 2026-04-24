from pathlib import Path

from dex.duckdb_runtime import open_runtime, runtime_paths


def test_runtime_paths_use_repo_local_dex_directory(tmp_path: Path):
    paths = runtime_paths(tmp_path)

    assert paths.workspace == tmp_path.resolve()
    assert paths.state_dir == tmp_path / ".dex"
    assert paths.database_path == tmp_path / ".dex" / "dex.duckdb"
    assert paths.artifacts_dir == tmp_path / ".dex" / "artifacts"
    assert paths.cache_dir == tmp_path / ".dex" / "cache"


def test_runtime_creates_database_and_runs_query(tmp_path: Path):
    with open_runtime(tmp_path) as runtime:
        assert runtime.paths.database_path.exists()
        assert runtime.query_all("SELECT 1 + 1") == [(2,)]


def test_runtime_keeps_transient_tables_out_of_durable_catalog(tmp_path: Path):
    with open_runtime(tmp_path) as runtime:
        runtime.create_transient_table("sample", "SELECT 42 AS value")
        assert runtime.query_all("SELECT value FROM dex_temp_sample") == [(42,)]

    with open_runtime(tmp_path) as runtime:
        durable_tables = runtime.query_all(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        )

    assert durable_tables == []
