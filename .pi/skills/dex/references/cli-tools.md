# Dex CLI Tools Reference

## Module Entry Points

### `python -m dex.mcp_app`

Main CLI tool for structured output generation.

#### Commands

**`profile <dataset-path> [--format FORMAT]`**

Profile a dataset and return structured results.

- `dataset-path`: Path to CSV, Parquet, or JSON file
- `--format`: Output format (`markdown`, `json`, `kitty`)

Example:
```bash
uv run python -m dex.mcp_app profile data/sales.csv --format markdown
```

**`chart --labels LABELS... --values VALUES... [--title TITLE] [--format FORMAT]`**

Create a bar chart from data.

- `--labels`: Space-separated category labels
- `--values`: Space-separated integer values
- `--title`: Chart title (default: "Bar Chart")
- `--format`: Output format (`markdown`, `json`, `kitty`)

Example:
```bash
uv run python -m dex.mcp_app chart --labels North South East --values 100 200 150 --title "Regional Sales" --format kitty
```

### `python -m dex.duckdb_runtime`

DuckDB runtime module (no CLI, import as library).

```python
from dex.duckdb_runtime import open_runtime

with open_runtime() as rt:
    result = rt.query_all("SELECT 1 + 1")
    print(result)
```

### `python -m dex.field_notes`

Field Notes module (no CLI, import as library).

```python
from dex.field_notes import FieldNotesStore

with FieldNotesStore.open() as store:
    event_id = store.append_event(
        event_type="finding",
        body="Q4 shows peak sales",
        author_type="ai"
    )
```

## Helper Scripts

The skill includes helper scripts in `scripts/`:

- `profile.sh` - Wrapper for dataset profiling
- `query.sh` - Execute DuckDB SQL queries
- `record_note.sh` - Record Field Notes from shell

## Output Formats

| Format   | Use Case                              |
|----------|---------------------------------------|
| markdown | Display in Pi TUI chat                |
| json     | Machine-readable, for further processing |
| kitty    | Terminal with Kitty graphics protocol |

## Kitty Graphics Protocol

When using `--format kitty`, chart output includes:

1. Markdown text description
2. Kitty escape sequence for inline PNG rendering
3. The PNG is base64-encoded and emitted as: `\033_Gf=100;<base64>\033\\`

This renders inline images in Kitty terminal and compatible terminals (iTerm2).
