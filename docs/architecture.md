# Dex Architecture - Pi-Native Integration Model

## Executive Summary

Dex is an AI-powered data analyst's field companion that operates natively inside Pi TUI. This document recommends a **Pi Skill + CLI Tools architecture** for the initial implementation, with **Pi Extensions** as an optional evolution path for deeper integration. Dex uses a **DuckDB-centered analytics engine** for data processing, **repo-local DuckDB-backed Field Notes** for durable analysis records, and **Kitty graphics protocol** for structured terminal output.

**Critical clarification:** Pi does NOT have built-in MCP support. Per Pi's README: "No MCP. Build CLI tools with READMEs (see Skills), or build an extension that adds MCP support." Dex's initial architecture uses Pi Skills with CLI tools (the native path), not MCP.

## Recommended Architecture

### Primary Integration Point: Pi Skill + CLI Tools

**Recommendation:** Dex should integrate with Pi through a **Pi skill** that orchestrates analysis workflows. The skill invokes **CLI tools** (Python scripts) for DuckDB operations and structured output. For rich terminal graphics, CLI tools emit **Kitty graphics protocol** escape sequences directly.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Pi TUI                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Dex Pi Skill                               │   │
│  │  (orchestration via SKILL.md + CLI tools)               │   │
│  │  - /skill:dex command                                   │   │
│  │  - Helper scripts invoke DuckDB operations              │   │
│  │  - CLI tools emit Kitty escape sequences for charts     │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│   Dex CLI Tools (Python)                                        │
│   - duckdb_runtime.py: DuckDB queries, profiling               │
│   - field_notes.py: Append-only activity log                   │
│   - chart_render.py: Matplotlib + kitcat for Kitty graphics    │
│   - All tools output structured text + Kitty escape sequences  │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Integration Point Is Appropriate

A Pi skill with CLI tools is the optimal integration point for Dex because:

1. **Native Pi support** - Skills are first-class Pi capabilities. No extension development required. CLI tools are explicitly endorsed by Pi: "Build CLI tools with READMEs (see Skills)."

2. **Progressive disclosure matches data analysis workflows** - Skills load on-demand via `/skill:dex` or natural language triggers, keeping Pi's context lean until analysis is needed. Data analysis is inherently bursty: users ask questions, get results, then pause to interpret. Skills align with this rhythm.

3. **Natural language entry point** - Users invoke Dex through `/skill:dex` commands or by asking analytical questions that trigger the skill's description match. This feels like consulting a field companion, not running a tool.

4. **Self-contained workflows** - Skills include helper scripts, reference documentation, and setup instructions. Dex's complexity (DuckDB initialization, Field Notes schema, Kitty rendering) belongs in skill documentation.

5. **CLI tools are language-agnostic** - Dex core is Python; Pi is TypeScript. CLI tools bridge them via stdin/stdout. No MCP, no extension TypeScript required.

6. **Kitty graphics work without MCP** - CLI tools emit Kitty escape sequences directly. No MCP Apps needed. Matplotlib backends (kitcat, matplotlib-backend-kitty) handle protocol details.

7. **Zero Pi modification required** - Skills are discovered automatically from `~/.pi/agent/skills/` or `.pi/skills/`. Dex can be developed, tested, and distributed independently of Pi releases.

## Options Considered

### 1. Pi Skills (Recommended for Orchestration)

**What it is:** Skills are Markdown-based capability packages that Pi loads on-demand. A skill includes a `SKILL.md` with frontmatter (name, description) and instructions referencing helper scripts, assets, and reference docs.

**How Dex would use it:**
- `SKILL.md` describes when to invoke Dex (e.g., "Use when analyzing datasets, profiling data, or creating field notes")
- Helper scripts initialize DuckDB and manage Field Notes
- Reference docs cover DuckDB schema, CLI tool catalog, and Kitty rendering options

**Pros:**
- No Pi code changes required
- Discoverable via `/skill:dex` or natural language triggers
- Can include full setup instructions, scripts, and reference documentation
- Aligns with Agent Skills standard (Anthropic, Pi, Claude Code compatible)
- Progressive disclosure: only loads when needed

**Cons:**
- Relies on LLM reading the skill (not guaranteed without `/skill:dex` command)
- Less seamless than a always-available extension
- Skill commands (`/skill:dex`) are verbose compared to `/dex`

**Verdict:** **Recommended** for workflow orchestration. The cons are acceptable tradeoffs for zero Pi modification and standard compliance.

### 2. Pi Prompt Templates

**What it is:** Markdown templates that expand into full prompts via `/name` commands (e.g., `/review` expands a code review template).

**How Dex would use it:** A `/dex-profile` template could provide a standard data profiling workflow; `/dex-compare` for dataset comparison.

**Pros:**
- Extremely lightweight: just Markdown files
- Fast expansion: no script execution required
- Good for repetitive analysis patterns

**Cons:**
- Static content only: cannot initialize DuckDB, start CLI tools, or run queries
- No dynamic behavior: cannot adapt to dataset schema or user context
- Limited to prompt text: cannot produce structured output or render charts

**Verdict:** **Not recommended as primary integration.** Could supplement the skill with quick templates (e.g., `/dex-summary`), but templates alone cannot deliver Dex's core capabilities.

### 3. Pi Extensions

**What it is:** TypeScript modules that extend Pi's behavior by subscribing to lifecycle events, registering custom tools, adding commands, and rendering custom UI components.

**How Dex would use it:**
- Register a `/dex` command for direct invocation
- Subscribe to `input` events to detect analytical queries
- Register custom tools for DuckDB operations
- Use `ctx.ui.custom()` for interactive result displays

**Pros:**
- Deep Pi integration: can intercept input, modify context, render custom UI
- Always available: no need to load a skill first
- Can register custom tools callable by the LLM
- Custom UI components for rich interactions

**Cons:**
- Requires TypeScript development and Pi extension API knowledge
- Extensions run with full system permissions (security concern for data analysis)
- Tightly coupled to Pi internals: breaking changes in Pi could break Dex
- More complex distribution: users must install extensions manually or via settings

**Verdict:** **Viable alternative** if deeper Pi integration is needed later. For the initial milestone, skills provide sufficient integration with less complexity and risk.

### 4. Custom Tools (via Pi Extensions)

**What it is:** Tools registered by extensions that the LLM can call directly (e.g., `dex_query`, `dex_profile`, `dex_field_note`).

**How Dex would use it:**
- Register tools for DuckDB queries, schema inspection, Field Notes management
- Tools execute Python code via `pi.exec()` or invoke CLI tools
- Results rendered via custom renderers

**Pros:**
- LLM can invoke tools directly without user commands
- Fine-grained control: separate tools for profiling, querying, note-taking
- Can stream progress updates during long-running analyses

**Cons:**
- Requires an extension to register tools (cannot be standalone)
- Tool registration is TypeScript-only: no Python-native path
- Each tool needs schema definition, error handling, rendering logic

**Verdict:** **Recommended as a complement to skills** for deeper Pi integration. For the initial milestone, CLI tools provide similar functionality without extension complexity.

### 5. MCP Integration (Requires Pi Extension)

**What it is:** Model Context Protocol (MCP) is a standard for exposing tools, resources, and prompts to LLMs. FastMCP is a Python framework for building MCP servers.

**Critical constraint:** Per Pi's README: **"No MCP. Build CLI tools with READMEs (see Skills), or build an extension that adds MCP support."** Pi does NOT have built-in MCP client support.

**How Dex could use it (future, with extension):**
- Build a Pi extension that adds MCP client support
- Run a FastMCP server exposing DuckDB query tools, Field Notes resources, and analysis prompts
- The extension connects Pi to the MCP server
- Structured results (tables, charts) returned via extension custom UI or Kitty escape sequences from CLI

**Pros:**
- Language-agnostic: Dex core is Python; Pi is TypeScript; MCP bridges them
- FastMCP has rich tooling and MCP Apps for interactive UI
- Standard protocol: works with Claude Desktop, other MCP clients
- Clean separation: DuckDB logic stays in Python MCP server

**Cons:**
- **Requires building a Pi extension first** (TypeScript development, Pi extension API knowledge)
- Requires running a separate server process (stdio or HTTP transport)
- MCP configuration needed in Pi settings or extension code
- Slightly higher latency than native Pi tools

**Verdict:** **Not recommended for initial milestone.** MCP requires an extension that does not yet exist. The initial architecture uses Pi Skills + CLI tools (native path). MCP integration is a future evolution path if deeper Pi integration is needed.

### 6. Combination Approach (Recommended for Initial Milestone)

**Architecture:**
```
User asks analytical question in Pi TUI
           │
           ▼
┌─────────────────────────┐
│  Pi Skill: /skill:dex   │  ← Orchestrates workflow
│  - Interprets intent    │
│  - Invokes CLI tools    │
│  - CLI tools emit Kitty │
│    escape sequences     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Dex CLI Tools (Python) │  ← Executes analysis
│  - duckdb_runtime.py    │
│  - field_notes.py       │
│  - chart_render.py      │
│  - All output to stdout │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  DuckDB Python          │  ← Analytics engine
│  - Queries              │
│  - Connectors           │
│  - Field Notes store    │
└─────────────────────────┘
```

**Why this combination:**
- Skills handle user intent and workflow orchestration (Pi-native)
- CLI tools execute Python code and emit structured output (language-agnostic)
- DuckDB stays in Python where its ecosystem lives
- Kitty graphics work via escape sequences from CLI (no MCP needed)
- Each layer can evolve independently

**Future evolution path:** If deeper Pi integration is needed (custom tools, input interception, custom UI rendering), build a Pi extension that:
- Registers custom Dex tools (`dex_query`, `dex_profile`)
- Optionally adds MCP client support (if MCP is desired)
- Uses `ctx.ui.custom()` for interactive displays

## Pi APIs, Extension Points, and Conventions

### Pi Skills API

Dex will use the **Agent Skills standard** that Pi implements:

**SKILL.md frontmatter:**
```yaml
---
name: dex
description: Data analyst companion for profiling datasets, running analytical queries, and maintaining field notes. Use when exploring data, creating summaries, or tracking analysis observations.
---
```

**Skill invocation:**
- `/skill:dex` - Load and execute the skill
- `/skill:dex profile dataset.csv` - Load skill with arguments
- Natural language triggers (if LLM reads skill description)

**Skill structure:**
```
dex/
├── SKILL.md                 # Frontmatter + instructions
├── scripts/
│   ├── init_duckdb.sh       # Initialize DuckDB and Field Notes schema
│   ├── profile_dataset.py   # CLI tool: profile a dataset
│   ├── query_duckdb.py      # CLI tool: execute DuckDB query
│   └── add_field_note.py    # CLI tool: append to Field Notes
├── references/
│   ├── duckdb-schema.md     # Field Notes schema documentation
│   └── cli-tools.md         # Catalog of available CLI tools
└── assets/
    └── field-notes-template.sql  # Initial Field Notes DDL
```

### Pi Extension APIs (Future Consideration)

If Dex evolves to require an extension, these APIs would be relevant:

**Custom tools:**
```typescript
pi.registerTool({
  name: "dex_query",
  description: "Execute a DuckDB query and return structured results",
  parameters: Type.Object({
    sql: Type.String({ description: "SQL query to execute" }),
    format: Type.Optional(Type.Union([Type.Literal("table"), Type.Literal("chart"), Type.Literal("markdown")]))
  }),
  async execute(toolCallId, params, signal, onUpdate, ctx) {
    // Call MCP server or execute DuckDB directly
  }
});
```

**Input event interception:**
```typescript
pi.on("input", async (event, ctx) => {
  // Detect analytical queries like "profile this dataset" or "show me sales trends"
  if (isAnalyticalQuery(event.text)) {
    // Could auto-invoke Dex workflow
  }
});
```

**Custom UI rendering:**
```typescript
pi.registerMessageRenderer("dex-results", (message, theme) => {
  // Render tables, charts, field notes with custom formatting
  // Could integrate Kitty graphics protocol for inline charts
});
```

### Pi Prompt Template Conventions (Supplementary)

Dex could provide prompt templates for common analysis patterns:

**`.pi/prompts/dex-profile.md`:**
```markdown
---
description: Profile a dataset and return summary statistics
argument-hint: "<dataset-path>"
---
Profile the dataset at $1. Return:
- Row count and column count
- Column names, types, and null percentages
- Basic statistics for numeric columns (min, max, mean, stddev)
- Sample of first 5 rows
Store observations in Field Notes.
```

**Usage:** `/dex-profile sales.csv`

## DuckDB Integration Strategy

### DuckDB as Core Analytics Engine

Dex uses DuckDB for:
- **Local analytical queries** - Fast SQL on CSV, Parquet, JSON files
- **External connectors** - Attach remote databases via DuckDB extensions (Postgres, MySQL, SQLite, etc.)
- **Data profiling** - Schema inspection, statistics computation
- **Intermediate tables** - Transformations and derived datasets
- **Field Notes storage** - Append-only activity log in DuckDB tables

### Transient vs. Durable Data

Dex distinguishes between transient analysis data and durable project artifacts:

**Transient analysis data** (not persisted):
- In-memory DuckDB sessions for exploratory queries
- Temporary tables created during analysis sessions (e.g., `CREATE TEMP TABLE intermediate_results AS ...`)
- Scratch work, intermediate transformations, and working datasets
- Session state that is discarded when the CLI tool exits

**Durable project artifacts** (persisted to `.dex/`):
- Field Notes database (`.dex/field_notes.duckdb`) - append-only activity log
- Generated outputs (`.dex/artifacts/`) - charts, exported query results, profiling summaries
- Cached schema profiles (`.dex/cache/`) - reusable metadata for known datasets
- Analysis traces and provenance records

**Default behavior:**
- CLI tools run in ephemeral DuckDB sessions unless explicitly configured otherwise
- Only Field Notes and user-requested artifacts are persisted by default
- Transient data is lost when the tool exits; users must explicitly save results to artifacts
- Field Notes capture metadata about transient operations (e.g., "Queried sales by region at 2026-04-24T14:30:00Z") without storing the full intermediate data

### DuckDB Python Package

Dex depends on:
- `duckdb` - Core Python package (CLI and embedded runtime)
- DuckDB extensions: `httpfs`, `postgres_scanner`, `mysql_scanner`, `sqlite_scanner`, `json`, `parquet`

**Installation:**
```bash
uv add duckdb
```

**Runtime expectations:**
- DuckDB runs embedded in CLI tool processes (invoked by skill scripts)
- Field Notes database stored in `.dex/field_notes.duckdb` (repo-local by default)
- Connections opened/closed per tool invocation (no long-lived connections unless `--keep-connection` flag)

### DuckDB Extensions/Connectors

Initial priority:
1. **Core** - CSV, Parquet, JSON readers (built-in)
2. **HTTPFS** - Read from S3, HTTPS URLs
3. **Postgres scanner** - Attach live Postgres databases
4. **SQLite scanner** - Migrate/analyze SQLite databases

Future consideration:
- MySQL scanner
- SQL Server scanner
- Iceberg/Delta Lake connectors

### Storage Strategy: Repo-Local `.dex/`

**Recommendation:** Use repo-local `.dex/` directory for Field Notes and analysis artifacts.

**Rationale:**
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

**Field Notes schema (first-pass):** See `docs/field-notes-design.md` for the detailed event/source/artifact schema. The architectural minimum is an append-only event log in `.dex/field_notes.duckdb` with author attribution, source/provenance references, generated artifact links, and correction/supersession events.

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

## Kitty Graphics Protocol for Chart Rendering

### Kitty Graphics Protocol

Kitty supports inline image rendering via escape sequences. Dex CLI tools emit these escape sequences directly to render charts in the terminal.

**Example: Emit Kitty graphics protocol escape sequence from a CLI tool:**
```python
# Example: Emit Kitty graphics protocol escape sequence
def render_chart_inline(chart_bytes: bytes):
    # Base64-encode PNG chart
    encoded = base64.b64encode(chart_bytes).decode('ascii')
    # Emit escape sequence: ESC_G f=100 (PNG format); <payload> ESC\
    print(f"\033_Gf=100;{encoded}\033\\")
```

**Matplotlib backends for Kitty:**
- **kitcat** - Matplotlib backend for Kitty and iTerm2 graphics protocols (recommended)
- **matplotlib-backend-kitty** - Matplotlib backend specifically for Kitty

**Usage:**
```python
import matplotlib
matplotlib.use('kitcat')  # or 'kitty' for matplotlib-backend-kitty
import matplotlib.pyplot as plt

# Create chart
plt.plot([1, 2, 3, 4])
plt.show()  # Renders inline via Kitty protocol
```

### Example Flow: Dataset Profile (CLI Tools Approach)

```
User: /skill:dex profile sales.csv

Dex Skill:
1. Invokes profile_dataset.py CLI tool with path="sales.csv"

CLI Tool (profile_dataset.py):
1. Loads sales.csv into DuckDB
2. Computes statistics (row count, column stats, null percentages)
3. Generates summary table (Markdown format to stdout)
4. Creates bar chart of null percentages (PNG via matplotlib/kitcat)
5. Emits Kitty escape sequence for inline chart
6. Adds Field Note entry: "Profiled sales.csv: 10K rows, 15 columns"

Pi TUI displays:
┌─────────────────────────────────────┐
│ Dataset: sales.csv                  │
│ Rows: 10,234 | Columns: 15          │
├─────────────────────────────────────┤
│ Column    │ Type    │ Null % │ ... │
│───────────┼─────────┼────────┼─────│
│ id        │ INTEGER │ 0.0%   │ ... │
│ amount    │ DOUBLE  │ 0.1%   │ ... │
│ ...       │ ...     │ ...    │ ... │
└─────────────────────────────────────┘

[Inline bar chart: null percentages by column]
( Rendered via Kitty graphics protocol escape sequences )

✓ Field Note added: "Profiled sales.csv"
```

## DuckDB MCP Tooling Exploration

### duckdb-mcp (ktanaka101/mcp-server-duckdb)

**What it is:** A standalone MCP server for DuckDB with a single `query` tool.

**Capabilities:**
- `query(sql: str)` - Execute any SQL query
- Read-only mode option
- Configurable database path

**Verdict:** **Too limited for Dex.** Single-tool design is intentional (LLMs can generate any SQL), but Dex needs higher-level tools (profiling, Field Notes, schema inspection) that wrap SQL. Dex should build its own CLI tools rather than wrapping this one.

### duckdb_mcp (teaguesterling/duckdb_mcp)

**What it is:** A DuckDB extension (C++) that provides MCP client and server capabilities from within DuckDB SQL.

**Capabilities:**
- **Client mode:** Attach MCP servers and query their resources via SQL
- **Server mode:** Expose DuckDB tables as MCP resources
- Custom tool publishing: `mcp_publish_tool(name, description, sql_template, ...)`
- Security framework: allowlists for commands and URLs

**Verdict:** **Interesting but not the right fit.** This extension is designed for DuckDB-to-MCP integration (e.g., exposing DuckDB to Claude Desktop). Dex needs the inverse: Pi-to-DuckDB via CLI tools. The extension's complexity (security frameworks, multi-transport support) is overkill for Dex's local-first use case.

### Dex's Approach (CLI Tools)

Dex will build **Python CLI tools** that:
- Wrap DuckDB Python package (not the duckdb_mcp extension)
- Expose high-level operations (profiling, Field Notes, schema inspection) via CLI commands
- Emit Kitty graphics protocol escape sequences for inline chart rendering
- Run as subprocesses invoked by the Pi skill scripts
- Output structured text (Markdown tables, summaries) to stdout

**Risks:**
- **Local data access:** DuckDB runs locally with user's permissions; no sandboxing beyond user's own account
- **Connector credentials:** External database connectors (Postgres, etc.) require credentials; these should be managed via environment variables or DuckDB secrets, not stored in Field Notes

**Future evolution (with Pi extension):** If deeper integration is needed, Dex could build a Pi extension that adds MCP client support and runs a FastMCP server. This is not part of the initial milestone.

## Validation and Gates

### Recommended Validation Commands

Dex is a Python + uv project. Recommended gates:

```bash
# Linting and formatting
uv run ruff check . && uv run ruff format --check .

# Type checking
uv run ty check

# Testing
uv run pytest -x --tb=short
```

These are configured in `.purser.toml` and supported by dev dependencies in `pyproject.toml`.

### Research Review Packet

Human reviewers should review these documents together before approving implementation:

- `docs/architecture.md` - Pi-native integration, DuckDB runtime/storage, first end-to-end flow, validation, non-goals
- `docs/tooling-research.md` - DuckDB skills, DuckDB MCP tooling, Kitty rendering, Field Notes storage options, end-to-end flow
- `docs/fastmcp-mcp-apps-research.md` - future MCP Apps/Pi extension bridge target for structured results
- `docs/field-notes-design.md` - detailed Field Notes schema, append flow, queries, export/archive behavior
- `docs/privacy-boundaries.md` - Field Notes privacy, export, connector credential, and local data access boundaries

Validation for the research milestone is human review plus the real Python/uv gates listed above.

## Non-Goals (Preserved from Spec)

- Do not build a full production data platform
- Do not implement every DuckDB connector
- Do not create a GUI outside the terminal/Pi TUI experience
- Do not make generated code the primary user-facing artifact
- Do not bypass Purser/Beads for Dex product work
- Do not store secrets or credentials in Field Notes
- Do not configure Beads shared/server/global mode

## Next Steps

1. **Human approval** - Review the research packet and resolve `dex-2uc` before implementation begins.
2. **Implementation beads** - Execute the existing small, independently reviewable beads for:
   - Initial Python package structure (`pyproject.toml`, `src/dex/`)
   - Minimal DuckDB runtime
   - DuckDB-backed Field Notes prototype
   - Minimal Pi-facing workflow
   - MCP Apps/structured-output prototype
   - Example end-to-end flow with public dataset
   - Setup and user documentation
3. **Validation** - Keep `.purser.toml` aligned with the real Python/uv gates as code is added.
