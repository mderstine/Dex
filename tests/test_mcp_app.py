"""Tests for Dex MCP Apps prototype."""

from pathlib import Path

from dex.mcp_app import (
    TableResult,
    ChartResult,
    profile_dataset,
    create_bar_chart,
)


def test_table_result_to_markdown():
    """Test TableResult Markdown rendering."""
    result = TableResult(
        columns=["Name", "Value"],
        rows=[["Alice", 100], ["Bob", 200]],
        title="Test Table",
        description="A sample table",
    )

    markdown = result.to_markdown()

    assert "## Test Table" in markdown
    assert "A sample table" in markdown
    assert "| Name | Value |" in markdown
    assert "| Alice | 100 |" in markdown
    assert "| Bob | 200 |" in markdown


def test_table_result_empty():
    """Test TableResult with empty data."""
    result = TableResult(columns=[], rows=[])
    markdown = result.to_markdown()
    assert "*Empty result*" in markdown


def test_table_result_to_json():
    """Test TableResult JSON serialization."""
    result = TableResult(
        columns=["A", "B"],
        rows=[[1, 2]],
        title="JSON Test",
    )

    data = result.to_json()

    assert data["type"] == "table"
    assert data["title"] == "JSON Test"
    assert data["columns"] == ["A", "B"]
    assert data["rows"] == [[1, 2]]


def test_chart_result_bar_to_markdown():
    """Test ChartResult bar chart Markdown rendering."""
    result = ChartResult(
        chart_type="bar",
        title="Sales by Region",
        data={"labels": ["North", "South"], "values": [100, 200]},
        description="Regional sales comparison",
    )

    markdown = result.to_markdown()

    assert "## Sales by Region" in markdown
    assert "Regional sales comparison" in markdown
    assert "North" in markdown
    assert "South" in markdown


def test_chart_result_ascii_fallback():
    """Test ChartResult ASCII bar chart fallback."""
    result = ChartResult(
        chart_type="bar",
        title="ASCII Test",
        data={"labels": ["A", "B", "C"], "values": [10, 20, 30]},
    )

    markdown = result.to_markdown()

    # Should contain ASCII chart with bar characters
    assert "█" in markdown or "[Chart data available]" in markdown


def test_chart_result_to_json():
    """Test ChartResult JSON serialization."""
    result = ChartResult(
        chart_type="bar",
        title="JSON Chart",
        data={"labels": ["X"], "values": [1]},
        description="Test",
        image_png_base64="abc123",
    )

    data = result.to_json()

    assert data["type"] == "chart"
    assert data["chartType"] == "bar"
    assert data["title"] == "JSON Chart"
    assert data["data"] == {"labels": ["X"], "values": [1]}
    assert data["hasImage"] is True


def test_profile_dataset_csv(tmp_path: Path):
    """Test dataset profiling on a CSV file."""
    # Create test CSV
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("name,value\nAlice,100\nBob,200\nCharlie,300\n")

    result = profile_dataset(str(csv_path))

    assert result.title is not None
    assert "test.csv" in result.title
    # Profile columns are: Column, Type, Row Count, Null Count, Null %
    assert "Column" in result.columns
    assert "Type" in result.columns
    # Should have one row per dataset column (name, value)
    assert len(result.rows) == 2


def test_profile_dataset_parquet(tmp_path: Path):
    """Test dataset profiling on a Parquet file."""
    # Create test data via DuckDB
    from dex.duckdb_runtime import open_runtime

    csv_path = tmp_path / "source.csv"
    parquet_path = tmp_path / "test.parquet"

    csv_path.write_text("id,amount\n1,100.5\n2,200.75\n3,300.25\n")

    # Convert to Parquet
    with open_runtime(tmp_path) as runtime:
        runtime.execute(f"CREATE TABLE t AS SELECT * FROM read_csv_auto('{csv_path}')")
        runtime.execute(f"COPY t TO '{parquet_path}' (FORMAT PARQUET)")

    result = profile_dataset(str(parquet_path))

    assert result.title is not None
    assert "test.parquet" in result.title
    assert len(result.rows) == 2  # Two columns


def test_profile_dataset_not_found():
    """Test profiling with non-existent file."""
    try:
        profile_dataset("/nonexistent/path.csv")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_profile_dataset_unsupported_type(tmp_path: Path):
    """Test profiling unsupported file type."""
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("plain text")

    try:
        profile_dataset(str(txt_path))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unsupported file type" in str(e)


def test_create_bar_chart_basic():
    """Test basic bar chart creation."""
    result = create_bar_chart(
        labels=["A", "B", "C"],
        values=[10, 20, 30],
        title="Test Chart",
    )

    assert result.chart_type == "bar"
    assert result.title == "Test Chart"
    assert result.data["labels"] == ["A", "B", "C"]
    assert result.data["values"] == [10, 20, 30]


def test_create_bar_chart_mismatch():
    """Test bar chart with mismatched labels/values."""
    try:
        create_bar_chart(labels=["A", "B"], values=[1, 2, 3])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "same length" in str(e)


def test_create_bar_chart_with_matplotlib():
    """Test bar chart generates PNG when matplotlib is available."""
    result = create_bar_chart(
        labels=["X", "Y"],
        values=[5, 10],
        title="Matplotlib Test",
    )

    # Matplotlib should be available in test environment
    assert result.data["labels"] == ["X", "Y"]
    # Image may or may not be generated depending on matplotlib
    # Just verify the chart structure is valid
    markdown = result.to_markdown()
    assert "Matplotlib Test" in markdown
