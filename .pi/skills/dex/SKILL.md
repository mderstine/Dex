---
name: dex
description: Data analyst companion for profiling datasets, running analytical queries, creating field notes, and generating structured analysis results. Use when exploring data, creating summaries, tracking analysis observations, or generating charts and tables.
---

# Dex - Data Analyst's Field Companion

Dex is an AI-powered data analyst's field companion that runs inside Pi TUI. It helps users rapidly explore, connect, analyze, transform, and report on data.

## When to Use Dex

Invoke Dex when the user needs to:

- Profile a dataset (CSV, Parquet, JSON) to understand its structure
- Run analytical queries on local files
- Create durable Field Notes to record observations, decisions, and findings
- Generate structured output (tables, charts, summaries) in the terminal
- Track analysis provenance and reproducibility

## Available Commands

Dex provides CLI tools that can be invoked from this skill:

### Profile a Dataset

```bash
cd <workspace-root>
uv run python -m dex.mcp_app profile <dataset-path> --format markdown
```

This will:
- Load the dataset into DuckDB
- Compute schema information (columns, types)
- Calculate row counts and null percentages
- Return a structured Markdown table

### Create a Bar Chart

```bash
cd <workspace-root>
uv run python -m dex.mcp_app chart --labels A B C --values 10 20 30 --title "My Chart" --format kitty
```

This will:
- Generate a bar chart using matplotlib
- Emit Kitty graphics protocol escape sequences for inline rendering
- Return Markdown with ASCII fallback

### Run DuckDB Queries Directly

```bash
cd <workspace-root>
uv run python -c "
from dex.duckdb_runtime import open_runtime
with open_runtime() as rt:
    result = rt.query_all('SELECT * FROM read_csv_auto(\"data/file.csv\") LIMIT 10')
    for row in result:
        print(row)
"
```

### Record Field Notes

```bash
cd <workspace-root>
uv run python -c "
from dex.field_notes import FieldNotesStore
with FieldNotesStore.open() as store:
    event_id = store.append_event(
        event_type='finding',
        body='Q4 shows 40% of annual revenue',
        author_type='ai',
        dataset_ref='data/sales.csv',
        metadata={'quarter': 'Q4', 'revenue_share': 0.40}
    )
    print(f'Field Note created: {event_id}')
"
```

## Workflow

### 1. Initial Dataset Exploration

When a user provides a dataset path:

1. Verify the file exists and is a supported format (CSV, Parquet, JSON)
2. Profile the dataset using `dex profile`
3. Record an activity Field Note
4. Present the profile results as a Markdown table

### 2. Analysis and Querying

For analytical questions:

1. Formulate appropriate DuckDB SQL queries
2. Execute via the DuckDB runtime
3. Present results as structured tables
4. Record observations as Field Notes

### 3. Generating Insights

For findings and recommendations:

1. Analyze query results for patterns
2. Generate charts where appropriate (use `dex chart` with `--format kitty`)
3. Record findings as Field Notes with `author_type='ai'`
4. Provide actionable recommendations

### 4. Session Documentation

At session boundaries:

1. Record session start/end as Field Notes
2. Link related notes by session_id
3. Export Field Notes timeline if requested
4. Preserve reproducibility information

## Storage Locations

Dex stores state in the workspace root:

```
.dex/
├── field_notes.duckdb    # Append-only activity log
├── artifacts/            # Generated charts, exports
│   └── YYYY-MM-DD/
└── cache/                # Schema profiles, metadata
```

**Privacy boundary:** Dex does NOT store secrets, credentials, or raw sensitive data in Field Notes. Connector credentials should be managed via environment variables or DuckDB secrets.

## Example Session

```
User: Profile the sales data in data/sales.csv

Dex:
1. Runs: uv run python -m dex.mcp_app profile data/sales.csv --format markdown
2. Records Field Note: "Profiled sales.csv" (author_type='ai')
3. Displays: Markdown table with columns, types, row count, null percentages
4. Asks: "Would you like me to analyze any specific patterns or generate charts?"

User: Show me sales by region as a chart

Dex:
1. Queries DuckDB for regional sales aggregates
2. Runs: uv run python -m dex.mcp_app chart --labels North South East West --values 100 200 150 180 --title "Sales by Region" --format kitty
3. Records Field Note: "Generated regional sales chart" (author_type='ai', artifact_ref='.dex/artifacts/...')
4. Displays: Chart rendered inline via Kitty graphics protocol
```

## References

- `docs/architecture.md` - Pi-native integration model
- `docs/field-notes-design.md` - Field Notes schema and usage
- `docs/privacy-boundaries.md` - Data privacy and export boundaries
- `src/dex/` - Source code for CLI tools and runtime
