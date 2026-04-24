# Dex - Data Analyst's Field Companion

Dex is an AI-powered data analyst's field companion that runs inside Pi TUI. It helps users rapidly explore, analyze, and report on data using DuckDB as the core analytics engine.

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Pi TUI (for skill integration)
- Kitty terminal (optional, for inline chart rendering)

### Installation

```bash
# Clone and install
git clone <repo-url>
cd dex
uv sync

# Verify installation
uv run python -m dex --help
```

### Developer Setup

```bash
# Install with dev dependencies
uv sync --all-groups

# Run validation gates
uv run ruff check . && uv run ruff format --check .
uv run ty check
uv run pytest -x --tb=short
```

## User-Facing Workflow in Pi TUI

### Using the Dex Skill

Dex provides a Pi Skill for natural language data analysis. The skill is located at `.pi/skills/dex/`.

**To use Dex in Pi:**

1. Load the skill: `/skill:dex`
2. Ask analytical questions or give exploration tasks

**Example session:**

```
User: Profile the sales data in data/sales.csv

Dex: [Profiles dataset, shows table with columns/types/null counts]

User: Show me sales by region as a chart

Dex: [Generates bar chart rendered inline in Kitty terminal]
```

### Available Commands

The Dex skill provides helper scripts in `.pi/skills/dex/scripts/`:

| Script | Purpose |
|--------|---------|
| `profile.sh <path>` | Profile a dataset |
| `query.sh "<sql>"` | Execute DuckDB SQL |
| `record_note.sh --type <type> --body <text>` | Record Field Notes |

### CLI Tools

Direct CLI access via Python module:

```bash
# Profile a dataset
uv run python -m dex.mcp_app profile data/sales.csv --format markdown

# Create a bar chart
uv run python -m dex.mcp_app chart --labels A B C --values 10 20 30 --format kitty

# Run example analysis
uv run python -m examples.titanic_analysis
```

## State Storage

### Default Location

Dex stores state in the workspace root:

```
.dex/
├── field_notes.duckdb    # Append-only activity log
├── artifacts/            # Generated charts, exports
│   └── YYYY-MM-DD/
└── cache/                # Schema profiles, metadata
```

**Storage model:** Repo-local `.dex/` for project-specific Field Notes and analysis artifacts. User-level storage (e.g., `~/.local/share/dex/`) is reserved for non-sensitive preferences only.

### Field Notes

Field Notes are durable, append-only records of analysis activity:

- **Activity logs:** Session start/end, workflow steps
- **Observations:** Dataset characteristics, schema discoveries
- **Findings:** Analytical conclusions, patterns detected
- **Decisions:** Analysis choices and rationale
- **Warnings:** Data quality issues, anomalies
- **Artifact references:** Links to generated charts, exports

**Author attribution:** All notes are marked as `human`, `ai`, or `system` authored.

### Querying Field Notes

```python
from dex.field_notes import FieldNotesStore

with FieldNotesStore.open() as store:
    # Get timeline for a session
    timeline = store.get_timeline(session_id="my-session")
    
    # Get dataset summary
    summary = store.get_dataset_summary("data/sales.csv")
    
    # Export to CSV
    store.export_timeline_csv("field-notes-export.csv")
```

### Export and Archive

```bash
# Copy Field Notes database
cp .dex/field_notes.duckdb field-notes-backup-$(date +%Y%m%d).duckdb

# Archive full Dex state
tar -czf dex-archive-$(date +%Y%m%d).tar.gz .dex/
```

**Privacy warning:** Before sharing exports, review for sensitive dataset names, paths, or analysis results. Dex does NOT store credentials or secrets in Field Notes.

## Validation Commands

Dex uses these validation gates (configured in `.purser.toml`):

```bash
# Linting and formatting
uv run ruff check . && uv run ruff format --check .

# Type checking
uv run ty check

# Testing
uv run pytest -x --tb=short
```

## Architecture Overview

Dex uses a **Pi Skill + CLI Tools** architecture:

1. **Pi Skill** (`.pi/skills/dex/`): Orchestrates workflows via SKILL.md and helper scripts
2. **CLI Tools** (`src/dex/`): Python modules for DuckDB operations and structured output
3. **DuckDB Runtime** (`src/dex/duckdb_runtime.py`): Local analytics engine
4. **Field Notes** (`src/dex/field_notes.py`): Append-only activity archival
5. **MCP Apps** (`src/dex/mcp_app.py`): Structured table/chart output (FastMCP compatible)

**Kitty rendering:** Charts are rendered via matplotlib with Kitty graphics protocol escape sequences for inline terminal display.

## Example Analysis

Run the included Titanic analysis example:

```bash
uv run python -m examples.titanic_analysis
```

This demonstrates:
- Dataset profiling
- Analytical queries (survival rates by class/gender)
- Chart generation
- Field Notes recording
- Structured terminal output

## Privacy Boundaries

**Dex must NOT store in Field Notes:**
- API keys, passwords, access tokens
- Credential-bearing connection strings
- Raw sensitive data dumps
- Full result sets containing PII

**Dex MAY store:**
- Sanitized URIs (e.g., `s3://bucket/key` without credentials)
- Schema summaries and statistics
- Query text and execution metadata
- Paths to local artifacts

See `docs/privacy-boundaries.md` for detailed privacy and export guidelines.

## Documentation

- `docs/architecture.md` - Pi-native integration model
- `docs/tooling-research.md` - DuckDB skills, MCP tooling, Kitty rendering
- `docs/field-notes-design.md` - Field Notes schema and usage
- `docs/privacy-boundaries.md` - Data privacy and export boundaries
- `docs/fastmcp-mcp-apps-research.md` - MCP Apps integration research

## Non-Goals

Dex is not:
- A full production data platform
- A GUI application outside the terminal
- A code-generation product (generated code is a byproduct)
- A secret/credential store

## License

MIT
