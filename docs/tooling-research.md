# Dex Tooling Research

This document summarizes research on tooling options for Dex: DuckDB skills, FastMCP MCP Apps, DuckDB MCP tooling, and Kitty-compatible chart/graph rendering.

## 1. DuckDB Skills

### Official DuckDB Skills

**Research finding:** As of April 2026, there is **no officially sanctioned "DuckDB skill"** in the Agent Skills standard repositories (Anthropic skills, Pi skills). 

**What exists:**
- Community-created DuckDB skills may exist in personal repositories, but none are canonical
- DuckDB has extensive Python documentation and examples, but these are not packaged as Agent Skills

**Implications for Dex:**
- Dex cannot rely on an existing official DuckDB skill
- Dex should **create its own skill** (`SKILL.md`) that wraps DuckDB operations
- The skill should document DuckDB usage patterns specific to Dex's workflow (profiling, Field Notes, connectors)

**Fallback approach:**
- Since no official skill exists, Dex will define its own DuckDB integration patterns
- The `docs/architecture.md` document specifies the DuckDB Python package as the core dependency
- Helper scripts in the skill will handle DuckDB initialization, connection management, and Field Notes schema setup

**Recommendation:** Do not wait for or depend on an official DuckDB skill. Build Dex's skill around the DuckDB Python package directly.

---

## 2. FastMCP MCP Apps

### FastMCP Overview

**FastMCP** is a Python framework for building MCP (Model Context Protocol) servers and clients. It is the most popular MCP framework, powering ~70% of MCP servers across all languages.

**Current version:** FastMCP 3.2.x (as of April 2026)

**Key capabilities:**
- **Servers:** Expose tools, resources, and prompts to LLMs
- **Apps:** Render interactive UI components directly in the conversation (critical for Dex)
- **Clients:** Connect to any MCP server (local or remote)

### MCP Apps for Structured Terminal Output

**What are MCP Apps?** MCP Apps are a FastMCP feature that enables interactive UI components rendered directly in the MCP client's conversation. For Dex running in Pi TUI, this means:

- Tables with sorting/filtering
- Charts and graphs (via Kitty graphics protocol)
- Result cards and summaries
- Analysis plans and provenance summaries
- Field note timelines

**FastMCP server example:**
```python
from fastmcp import FastMCP

mcp = FastMCP(
    name="Dex",
    instructions="Data analyst companion for profiling datasets, running analytical queries, and maintaining field notes.",
    version="0.1.0"
)

@mcp.tool
def profile_dataset(path: str) -> dict:
    """Profile a dataset and return summary statistics."""
    # DuckDB logic here
    return {
        "row_count": 10234,
        "column_count": 15,
        "columns": [...],
        "statistics": {...}
    }

@mcp.tool
def query(sql: str, format: str = "markdown") -> str:
    """Execute a DuckDB query and return results."""
    # DuckDB execution here
    return results

if __name__ == "__main__":
    mcp.run()  # Auto-detects stdio vs HTTP based on environment
```

### FastMCP Client Integration

Pi can connect to FastMCP servers via:
- **stdio transport:** For local servers (recommended for Dex)
- **HTTP transport:** For remote servers (future consideration)

**Pi configuration (future):**
```json
{
  "mcpServers": {
    "dex": {
      "command": "uv",
      "args": ["--directory", "/path/to/dex", "run", "dex-mcp"]
    }
  }
}
```

Alternatively, Dex's Pi skill can start the MCP server as a subprocess and manage its lifecycle.

### MCP Apps and Kitty Terminal

FastMCP MCP Apps can emit terminal escape sequences, including the **Kitty graphics protocol** for inline images. This is critical for rendering charts without leaving the terminal.

**Example: Emitting a chart via Kitty graphics protocol:**
```python
import base64
from fastmcp import FastMCP

mcp = FastMCP("Dex")

@mcp.tool
def plot_null_percentages(table_name: str) -> str:
    """Generate a bar chart of null percentages and display inline."""
    # Generate chart with matplotlib
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    chart_bytes = buf.getvalue()
    
    # Base64-encode and emit Kitty escape sequence
    encoded = base64.b64encode(chart_bytes).decode('ascii')
    kitty_escape = f"\033_Gf=100;{encoded}\033\\"
    
    return f"Null percentages for {table_name}:\n\n{kitty_escape}"
```

**FastMCP v3.x features relevant to Dex:**
- **Tag-based filtering:** Categorize tools (e.g., `tags={"profiling", "field-notes"}`)
- **Custom routes:** Add health checks or status endpoints when running in HTTP mode
- **Authentication:** Secure HTTP endpoints with bearer tokens or OAuth (future consideration)
- **Background tasks:** Run long analyses asynchronously while user continues working

### FastMCP Installation

```bash
uv add fastmcp
```

**Dependencies (FastMCP 3.2.x):**
- `mcp` (MCP Python SDK)
- `pydantic` (parameter validation)
- `httpx` (HTTP transport)
- `uvicorn` (HTTP server)
- `rich` (terminal formatting)

---

## 3. DuckDB MCP Tooling

### mcp-server-duckdb (ktanaka101)

**Repository:** https://github.com/ktanaka101/mcp-server-duckdb

**Description:** A standalone MCP server for DuckDB with a single `query` tool.

**Capabilities:**
- `query(sql: str)` - Execute any SQL query on a DuckDB database
- Read-only mode (`--readonly` flag)
- Configurable database path (`--db-path`)
- Connection reuse option (`--keep-connection`)

**Installation:**
```bash
uvx mcp-server-duckdb --db-path ~/data.duckdb
```

**Claude Desktop configuration:**
```json
{
  "mcpServers": {
    "duckdb": {
      "command": "uvx",
      "args": ["mcp-server-duckdb", "--db-path", "~/data.duckdb"]
    }
  }
}
```

**Verdict for Dex:** **Too limited.** The single-tool design is intentional (LLMs can generate any SQL), but Dex needs higher-level abstractions:
- Dataset profiling (not just raw SQL)
- Field Notes management (append-only activity log)
- Schema inspection and discovery
- Structured output formatting (tables, charts, not just text)

**Recommendation:** Do not depend on `mcp-server-duckdb`. Build Dex's own FastMCP server with domain-specific tools.

### duckdb_mcp Extension (teaguesterling)

**Repository:** https://github.com/teaguesterling/duckdb_mcp

**Description:** A DuckDB extension (C++) that provides MCP client and server capabilities from within DuckDB SQL.

**Capabilities:**

**Client mode:**
- Attach MCP servers: `ATTACH 'python3' AS server (TYPE mcp, ARGS '["path/to/server.py"]')`
- Query remote resources: `SELECT * FROM read_csv('mcp://server/file:///data.csv')`
- Execute remote tools: `SELECT mcp_call_tool('server', 'analyze', '{"dataset": "sales"}')`

**Server mode:**
- Start MCP server: `PRAGMA mcp_server_start('stdio')`
- Publish tables as resources: `SELECT mcp_publish_table('products', 'data://tables/products', 'json')`
- Publish custom tools: `PRAGMA mcp_publish_tool('search_products', 'Search products', 'SELECT * FROM products WHERE ...', '{...}', '["query"]')`

**Security framework:**
- `allowed_mcp_commands` - Allowlist for executable paths
- `allowed_mcp_urls` - Allowlist for URL prefixes
- `mcp_lock_servers` - Lock configuration to prevent runtime changes

**Verdict for Dex:** **Interesting but not the right fit.** This extension is designed for:
- Exposing DuckDB to external MCP clients (e.g., Claude Desktop)
- Querying external MCP resources from within DuckDB SQL

Dex needs the inverse: **Pi-to-DuckDB via MCP**, with high-level analysis tools. The extension's complexity (security frameworks, multi-transport support, C++ build requirements) is overkill for Dex's local-first use case.

**Recommendation:** Do not depend on `duckdb_mcp` extension. Use DuckDB Python package directly in a FastMCP server.

### Dex's MCP Tooling Strategy

Dex will build a **custom FastMCP server** with these tools:

| Tool | Description |
|------|-------------|
| `profile_dataset(path: str)` | Profile a dataset (row count, schema, statistics, null percentages) |
| `query(sql: str, format: str)` | Execute DuckDB query with formatted output (table, markdown, chart) |
| `list_tables()` | List all tables in current DuckDB database |
| `describe_table(table: str)` | Get schema for a specific table |
| `add_field_note(content: str, note_type: str, dataset: Optional[str])` | Append to Field Notes |
| `list_field_notes(limit: int, note_type: Optional[str])` | Query Field Notes |
| `export_results(query: str, path: str, format: str)` | Export query results to file |

**Rationale:**
- Higher-level than raw SQL: `profile_dataset` abstracts the profiling logic
- Structured output: Tools return typed data, not just text
- Field Notes integration: Dedicated tools for activity logging
- Extensible: New tools can be added without changing the core architecture

---

## 4. Kitty-Compatible Chart/Graph Rendering

### Kitty Graphics Protocol

**Specification:** https://sw.kovidgoyal.net/kitty/graphics-protocol/

**Overview:** The Kitty graphics protocol allows terminal applications to render arbitrary pixel graphics inline with text. This is critical for Dex to display charts without leaving the terminal.

**Key features:**
- **Inline images:** PNG, RGB, RGBA formats supported
- **Pixel-perfect positioning:** Place graphics at specific cell coordinates
- **Z-index support:** Render graphics under or over text
- **Animation support:** Frame-based animations with timing control
- **Transmission options:** Direct (base64), file, shared memory, temporary file

**Escape sequence format:**
```
ESC_G <control-data> ; <payload> ESC\
```

**Example: Display PNG inline:**
```bash
# Base64-encoded PNG
encoded=$(base64 -w0 chart.png)
# Emit escape sequence: f=100 means PNG format
printf '\033_Gf=100;%s\033\\' "$encoded"
```

### Python Libraries for Kitty Graphics

#### term-image
**Repository:** https://github.com/AnonymouX47/term-image

**Description:** Python library and CLI for displaying images in the terminal using Kitty graphics protocol.

**Features:**
- Display images inline
- Browse image directories
- Resize and crop
- Works over SSH

**Verdict:** Good for displaying pre-generated images. Dex may use this for exporting charts, but needs inline generation.

#### pixcat
**Repository:** https://github.com/xyproto/pixcat

**Description:** CLI and Python library wrapping the Kitty graphics protocol.

**Features:**
- Simple API for displaying images
- Supports multiple transmission modes
- Works with PIL/Pillow images

**Verdict:** Lightweight option for Dex to emit charts.

#### matplotlib-backend-kitty
**Repository:** https://github.com/jktr/matplotlib-backend-kitty

**Description:** Matplotlib backend for direct plotting in Kitty terminal.

**Usage:**
```python
import matplotlib
matplotlib.use('kitty')
import matplotlib.pyplot as plt

plt.plot([1, 2, 3, 4])
plt.show()  # Displays inline via Kitty protocol
```

**Verdict:** **Strong candidate** for Dex chart generation. Matplotlib is mature, widely used, and the backend handles Kitty protocol details.

#### kitcat
**Repository:** https://github.com/mil-ad/kitcat

**Description:** Matplotlib backend for Kitty and iTerm2 graphics protocols.

**Features:**
- Works with Kitty, iTerm2, WezTerm, VSCode terminal, Ghostty, tmux (with `allow-passthrough on`)
- Simpler than matplotlib-backend-kitty
- Works over SSH

**Usage:**
```python
import matplotlib
matplotlib.use('kitcat')
import matplotlib.pyplot as plt

plt.plot([1, 2, 3, 4])
plt.show()
```

**Verdict:** **Strong candidate** for Dex. Broader terminal support than matplotlib-backend-kitty.

#### termplt
**Repository:** https://github.com/EdCarney/termplt

**Description:** Rust library for rendering 2D plots directly in Kitty-compatible terminals.

**Features:**
- Generic numeric types (i32, f32, f64, etc.)
- Multiple series overlay
- Marker styles (circles, squares)
- Line drawing
- Axes and grid lines
- Bitmap text for labels

**CLI usage:**
```bash
termplt --data "(1,1),(2,4),(3,9),(4,16)"
```

**Verdict:** Interesting but adds Rust dependency to a Python project. Matplotlib backends are simpler for Dex.

### Recommended Approach for Dex

**Primary:** Use **kitcat** or **matplotlib-backend-kitty** for chart generation.

**Rationale:**
- Matplotlib is mature and well-documented
- Backend handles Kitty protocol escape sequences
- Supports all common chart types (bar, line, scatter, histogram, etc.)
- Easy to integrate with DuckDB query results

**Example Dex chart generation:**
```python
import matplotlib
matplotlib.use('kitcat')
import matplotlib.pyplot as plt
import duckdb
import io

def plot_null_percentages(table_name: str) -> str:
    # Query DuckDB for null percentages
    conn = duckdb.connect()
    results = conn.execute(f"""
        SELECT column_name, 
               AVG(CASE WHEN {table_name}.column_name IS NULL THEN 1.0 ELSE 0.0 END) * 100 as null_pct
        FROM {table_name}
        GROUP BY column_name
    """).fetchall()
    
    columns = [r[0] for r in results]
    null_pcts = [r[1] for r in results]
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(columns, null_pcts)
    ax.set_ylabel('Null Percentage')
    ax.set_title(f'Null Percentages: {table_name}')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Render to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # Emit via Kitty protocol (kitcat handles this)
    plt.show()
    
    return f"Chart displayed for {table_name}"
```

**Fallback:** If kitcat/matplotlib-backend-kitty have issues, use **pixcat** or direct escape sequence emission.

### Terminal Compatibility

**Tested terminals (kitcat):**
| Terminal | Supported | Notes |
|----------|-----------|-------|
| Kitty | ✅ | Primary target |
| iTerm2 | ✅ | macOS |
| VSCode | ✅ | Requires `terminal.integrated.enableImages` |
| WezTerm | ✅ | |
| Ghostty | ✅ | |
| tmux | ✅ | Requires `allow-passthrough on` |
| Warp | ✅ | |
| Alacritty | ❌ | No graphics protocol support |
| Terminal.app | ❌ | No graphics protocol support |

**Dex target:** Kitty (as specified in the spec). Fallback to text-based tables for unsupported terminals.

---

## 5. Field Notes Storage Options

### Research Summary

The spec identifies three storage models for Field Notes:

1. **Repo-local `.dex/`** - Project-specific Field Notes alongside the codebase
2. **User-level storage** (`~/.local/share/dex/`, `~/.dex/`) - Cross-project preferences and caches
3. **Hybrid** - Repo-local for project artifacts, user-level for preferences

### Recommendation

**Primary:** Use **repo-local `.dex/`** for Field Notes and analysis artifacts.

**Rationale (from architecture.md):**
- Easy to inspect, archive, and reason about alongside the project being analyzed
- Good fit for project-specific Field Notes, cached profiles, generated artifacts
- Makes it clear which Dex state belongs to the current repository or analysis workspace
- Simple default for local developer workflows

**Structure:**
```
.dex/
├── field_notes.duckdb      # DuckDB database for Field Notes
├── artifacts/              # Generated outputs (charts, exports)
│   └── 2026-04-24/
│       ├── profile-sales.png
│       └── query-results.csv
└── cache/                  # Cached schema profiles, connection metadata
    └── sales.csv.schema.json
```

**Future consideration:** Hybrid model if users need cross-project preferences or global caches.

### Field Notes Schema

**First-pass schema:**
```sql
CREATE TABLE field_notes (
    id INTEGER PRIMARY KEY DEFAULT nextval('field_notes_id_seq'),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    note_type VARCHAR NOT NULL,  -- 'observation', 'decision', 'finding', 'warning', 'hypothesis'
    author_type VARCHAR NOT NULL,  -- 'human' or 'ai'
    content TEXT NOT NULL,
    dataset_path VARCHAR,  -- Optional: associated dataset
    query_text TEXT,       -- Optional: SQL query that produced this note
    artifact_path VARCHAR, -- Optional: path to generated artifact
    metadata JSON          -- Flexible metadata (superseded_by, related_to, etc.)
);

CREATE INDEX field_notes_timestamp_idx ON field_notes(timestamp DESC);
CREATE INDEX field_notes_type_idx ON field_notes(note_type);
CREATE INDEX field_notes_dataset_idx ON field_notes(dataset_path);
```

**Append-only behavior:**
- New notes are always INSERTed, never UPDATEd or DELETEd
- Corrections/addendums are new notes with `metadata: {"supersedes": [previous_id]}`
- Compaction (hard deletes) is a manual, explicit operation

---

## 6. Example End-to-End Flow

### Scenario: User profiles a sales dataset

**User input in Pi TUI:**
```
/skill:dex profile sales.csv
```

**Dex skill workflow:**
1. Parse arguments: `path="sales.csv"`, `action="profile"`
2. Initialize DuckDB (create `.dex/field_notes.duckdb` if needed)
3. Start FastMCP server (stdio transport)
4. Invoke `profile_dataset` tool via MCP

**FastMCP server execution:**
1. Load `sales.csv` into DuckDB
2. Compute statistics:
   - Row count: 10,234
   - Column count: 15
   - Column types and null percentages
   - Numeric column statistics (min, max, mean, stddev)
3. Generate structured output:
   - Markdown table for schema
   - Bar chart for null percentages (via kitcat/Kitty protocol)
4. Add Field Note: "Profiled sales.csv: 10K rows, 15 columns"

**Pi TUI display:**
```
┌─────────────────────────────────────┐
│ Dataset: sales.csv                  │
│ Rows: 10,234 | Columns: 15          │
├─────────────────────────────────────┤
│ Column    │ Type    │ Null % │ ... │
│───────────┼─────────┼────────┼─────│
│ id        │ INTEGER │ 0.0%   │ ... │
│ amount    │ DOUBLE  │ 0.1%   │ ... │
│ date      │ DATE    │ 0.0%   │ ... │
│ region    │ VARCHAR │ 2.3%   │ ... │
│ ...       │ ...     │ ...    │ ... │
└─────────────────────────────────────┘

[Inline bar chart: null percentages by column]
( Rendered via Kitty graphics protocol )

✓ Field Note added: "Profiled sales.csv at 2026-04-24T14:30:00Z"
```

**Follow-up query:**
```
/skill:dex query "SELECT region, SUM(amount) as total FROM sales GROUP BY region ORDER BY total DESC"
```

**Result:**
```
┌─────────────────────────────────────┐
│ Region      │ Total                 │
│─────────────┼───────────────────────│
│ North       │ $1,234,567.89         │
│ South       │ $987,654.32           │
│ East        │ $876,543.21           │
│ West        │ $765,432.10           │
└─────────────────────────────────────┘

✓ Field Note added: "Queried sales by region"
```

---

## 7. Summary and Recommendations

### Tooling Stack

| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| **Pi Integration** | Pi Skill | No Pi modification required, progressive disclosure, standard-compliant |
| **MCP Framework** | FastMCP 3.x | Python-native, MCP Apps for structured output, Kitty graphics support |
| **DuckDB** | DuckDB Python package | Direct control, no C++ extension complexity |
| **Chart Rendering** | kitcat (matplotlib backend) | Mature, Kitty protocol support, works over SSH |
| **Field Notes Storage** | Repo-local `.dex/` | Project-specific, easy to archive, clear ownership |

### Do Not Depend On

- **mcp-server-duckdb** - Too limited (single `query` tool)
- **duckdb_mcp extension** - Wrong direction (DuckDB-to-MCP, not Pi-to-DuckDB)
- **Official DuckDB skill** - Does not exist; Dex will define its own patterns

### Next Steps

1. **Human approval** - Review this research and `docs/architecture.md`
2. **Package structure** - Create `src/dex/` with `pyproject.toml`
3. **Field Notes prototype** - Implement DuckDB schema and append-only behavior
4. **FastMCP server** - Build minimal server with `profile_dataset` tool
5. **Pi skill** - Create `SKILL.md` with orchestration scripts
6. **End-to-end example** - Test with public dataset (e.g., NYC taxi data, Kaggle sample)
