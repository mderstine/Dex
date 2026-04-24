"""Minimal FastMCP MCP Apps prototype for Dex structured output.

This module provides:
1. A minimal FastMCP server with structured table/chart output tools
2. CLI tools for Kitty-compatible terminal rendering (primary Pi path)
3. Bridge architecture documentation for future Pi extension integration

Note: Pi does NOT have native MCP support. The primary integration path
is Pi Skill + CLI Tools. MCP Apps require a Pi extension bridge.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

# FastMCP is optional; provide fallback if not installed
try:
    from fastmcp import FastMCP  # type: ignore[import-not-found]

    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False

from .duckdb_runtime import open_runtime


@dataclass
class TableResult:
    """Structured table result for terminal or MCP Apps rendering."""

    columns: list[str]
    rows: list[list[Any]]
    title: str | None = None
    description: str | None = None

    def to_markdown(self) -> str:
        """Render as Markdown table."""
        if not self.columns:
            return "*Empty result*"

        # Header
        header = "| " + " | ".join(str(c) for c in self.columns) + " |"
        separator = "| " + " | ".join("---" for _ in self.columns) + " |"

        # Rows
        row_lines = []
        for row in self.rows:
            row_lines.append("| " + " | ".join(str(v) for v in row) + " |")

        lines = []
        if self.title:
            lines.append(f"## {self.title}")
        if self.description:
            lines.append(self.description)
            lines.append("")
        lines.append(header)
        lines.append(separator)
        lines.extend(row_lines)

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """Serialize for MCP Apps structuredContent."""
        return {
            "type": "table",
            "title": self.title,
            "description": self.description,
            "columns": self.columns,
            "rows": self.rows,
        }


@dataclass
class ChartResult:
    """Structured chart result for terminal or MCP Apps rendering."""

    chart_type: Literal["bar", "line", "scatter"]
    title: str
    data: dict[str, Any]
    description: str | None = None
    image_png_base64: str | None = None

    def to_markdown(self) -> str:
        """Render as Markdown with ASCII fallback or image placeholder."""
        lines = []
        if self.title:
            lines.append(f"## {self.title}")
        if self.description:
            lines.append(self.description)
            lines.append("")

        if self.image_png_base64:
            # For terminals that support inline images (Kitty), emit escape sequence
            # For Markdown, show placeholder
            lines.append(
                "![Chart](data:image/png;base64,{})".format(
                    self.image_png_base64[:100] + "..."
                )
            )
            lines.append("")
            lines.append("*Chart rendered above if terminal supports inline images*")
        else:
            # ASCII fallback
            lines.append("```")
            lines.append(
                self._ascii_bar_chart()
                if self.chart_type == "bar"
                else "[Chart data available]"
            )
            lines.append("```")

        return "\n".join(lines)

    def _ascii_bar_chart(self) -> str:
        """Simple ASCII bar chart fallback."""
        if self.chart_type != "bar":
            return "[ASCII bar chart not implemented for this chart type]"

        labels = self.data.get("labels", [])
        values = self.data.get("values", [])

        if not labels or not values:
            return "[No data]"

        max_val = max(values) if values else 1
        max_width = 40

        lines = []
        for label, val in zip(labels, values):
            bar_len = int((val / max_val) * max_width) if max_val > 0 else 0
            bar = "█" * bar_len
            lines.append(f"{label:>15} |{bar} {val}")

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """Serialize for MCP Apps structuredContent."""
        return {
            "type": "chart",
            "chartType": self.chart_type,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "hasImage": self.image_png_base64 is not None,
        }


def profile_dataset(dataset_path: str) -> TableResult:
    """Profile a dataset and return structured table result.

    Args:
        dataset_path: Path to local file (CSV, Parquet, JSON).

    Returns:
        TableResult with column statistics.
    """
    with open_runtime() as runtime:
        # Load dataset into DuckDB
        path = Path(dataset_path).resolve()
        if not path.exists():
            msg = f"Dataset not found: {dataset_path}"
            raise FileNotFoundError(msg)

        suffix = path.suffix.lower()
        if suffix == ".csv":
            table_name = "profile_data"
            runtime.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{path}')"
            )
        elif suffix == ".parquet":
            table_name = "profile_data"
            runtime.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM parquet_scan('{path}')"
            )
        elif suffix == ".json":
            table_name = "profile_data"
            runtime.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_json_auto('{path}')"
            )
        else:
            msg = f"Unsupported file type: {suffix}"
            raise ValueError(msg)

        # Get column info via DESCRIBE
        describe_result = runtime.query_all(f"DESCRIBE {table_name}")
        columns = [row[0] for row in describe_result]

        # Get row count
        row_count = runtime.query_all(f"SELECT COUNT(*) FROM {table_name}")[0][0]

        # Get null counts per column
        null_counts = {}
        for col in columns:
            result = runtime.query_all(
                f'SELECT COUNT(*) FROM {table_name} WHERE "{col}" IS NULL'
            )
            null_counts[col] = result[0][0]

        # Build profile table
        profile_columns = ["Column", "Type", "Row Count", "Null Count", "Null %"]
        profile_rows = []

        for col in columns:
            col_type = describe_result[columns.index(col)][1]
            null_count = null_counts[col]
            null_pct = (
                f"{(null_count / row_count * 100):.1f}%" if row_count > 0 else "N/A"
            )
            profile_rows.append([col, col_type, row_count, null_count, null_pct])

        return TableResult(
            columns=profile_columns,
            rows=profile_rows,
            title=f"Dataset Profile: {path.name}",
            description=f"Path: {path}",
        )


def create_bar_chart(
    labels: list[str], values: list[int], title: str = "Bar Chart"
) -> ChartResult:
    """Create a bar chart result.

    Args:
        labels: Category labels.
        values: Numeric values for each category.
        title: Chart title.

    Returns:
        ChartResult with chart data.
    """
    if len(labels) != len(values):
        msg = "labels and values must have same length"
        raise ValueError(msg)

    # Generate PNG chart using matplotlib (if available)
    image_base64 = None
    try:
        import matplotlib  # type: ignore[import-not-found]

        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt  # type: ignore[import-not-found]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(range(len(labels)), values)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title(title)
        ax.set_ylabel("Value")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)

        image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    except ImportError:
        # Matplotlib not available; no image
        pass

    return ChartResult(
        chart_type="bar",
        title=title,
        data={"labels": labels, "values": values},
        description=f"Bar chart with {len(labels)} categories",
        image_png_base64=image_base64,
    )


def emit_kitty_image(image_base64: str) -> None:
    """Emit Kitty graphics protocol escape sequence for inline image.

    Args:
        image_base64: Base64-encoded PNG image data.
    """
    # Kitty graphics protocol: ESC _ G f=100 (PNG); <base64> ESC \\
    # Using the more compatible format
    sys.stdout.write("\033_Gf=100;")
    sys.stdout.write(image_base64)
    sys.stdout.write("\033\\")
    sys.stdout.flush()


# FastMCP server (optional, for MCP Apps integration)
if FASTMCP_AVAILABLE:
    mcp = FastMCP("Dex")

    @mcp.tool()
    def dex_profile(dataset_path: str) -> dict[str, Any]:
        """Profile a dataset and return structured results.

        Args:
            dataset_path: Path to local CSV, Parquet, or JSON file.

        Returns:
            Structured table result as JSON.
        """
        result = profile_dataset(dataset_path)
        return result.to_json()

    @mcp.tool()
    def dex_bar_chart(
        labels: list[str], values: list[int], title: str = "Bar Chart"
    ) -> dict[str, Any]:
        """Create a bar chart from data.

        Args:
            labels: Category labels.
            values: Numeric values.
            title: Chart title.

        Returns:
            Structured chart result as JSON.
        """
        result = create_bar_chart(labels, values, title)
        return result.to_json()


def main() -> None:
    """CLI entry point for Dex MCP Apps tools."""
    parser = argparse.ArgumentParser(
        prog="dex", description="Dex data analysis CLI tools"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Profile a dataset")
    profile_parser.add_argument("dataset_path", help="Path to dataset file")
    profile_parser.add_argument(
        "--format",
        choices=["markdown", "json", "kitty"],
        default="markdown",
        help="Output format",
    )

    # Chart command
    chart_parser = subparsers.add_parser("chart", help="Create a bar chart")
    chart_parser.add_argument(
        "--labels", nargs="+", required=True, help="Category labels"
    )
    chart_parser.add_argument(
        "--values", type=int, nargs="+", required=True, help="Numeric values"
    )
    chart_parser.add_argument("--title", default="Bar Chart", help="Chart title")
    chart_parser.add_argument(
        "--format",
        choices=["markdown", "json", "kitty"],
        default="markdown",
        help="Output format",
    )

    args = parser.parse_args()

    if args.command == "profile":
        result = profile_dataset(args.dataset_path)

        if args.format == "json":
            print(json.dumps(result.to_json(), indent=2))
        elif args.format == "kitty":
            print(result.to_markdown())
        else:
            print(result.to_markdown())

    elif args.command == "chart":
        result = create_bar_chart(args.labels, args.values, args.title)

        if args.format == "json":
            print(json.dumps(result.to_json(), indent=2))
        elif args.format == "kitty":
            print(result.to_markdown())
            if result.image_png_base64:
                emit_kitty_image(result.image_png_base64)
        else:
            print(result.to_markdown())


if __name__ == "__main__":
    main()
