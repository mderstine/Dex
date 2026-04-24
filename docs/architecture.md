# Dex Architecture - Pi-Native Integration Model

## Executive Summary

Dex is an AI-powered data analyst's field companion that operates natively inside Pi TUI. This document recommends a **hybrid integration architecture** combining **Pi skills** for workflow orchestration, **FastMCP MCP Apps** for structured terminal output, and a **DuckDB-centered analytics engine** for data processing.

## Recommended Architecture

### Primary Integration Point: Pi Skills + FastMCP MCP Apps

**Recommendation:** Dex should integrate with Pi through a **Pi skill** that orchestrates analysis workflows, combined with **FastMCP MCP Apps** for returning structured results (tables, charts, summaries) to the terminal.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Pi TUI                                 │
│  ┌─────────────────┐         ┌─────────────────────────────┐   │
│  │   Dex Skill     │         │   FastMCP MCP App Server    │   │
│  │  (orchestration │◄───────►│   (structured output)       │   │
│  │   & workflow)   │         │   - tables                  │   │
│  └────────┬────────┘         │   - charts (Kitty protocol) │   │
│           │                  │   - field notes             │   │
│           │                  └──────────────┬──────────────┘   │
│           │                                 │                   │
└───────────┼─────────────────────────────────┼───────────────────┘
            │                                 │
            ▼                                 ▼
┌────────────────────────┐         ┌─────────────────────────────┐
│   DuckDB Python         │         │   Kitty Terminal           │
│   (analytics engine)    │         │   (rich graphics via       │
│   - local queries       │         │    graphics protocol)      │
│   - connectors          │         └─────────────────────────────┘
│   - field notes store   │
└────────────────────────┘
```

### Why This Integration Point Is Appropriate

A Pi skill is the optimal integration point for Dex because:

1. **Progressive disclosure matches data analysis workflows** - Skills load on-demand via `/skill:dex` or natural language triggers, keeping Pi's context lean until analysis is needed. Data analysis is inherently bursty: users ask questions, get results, then pause to interpret. Skills align with this rhythm.

2. **Natural language entry point** - Users can invoke Dex through `/skill:dex` commands or by asking analytical questions that trigger the skill's description match. This feels like consulting a field companion, not running a tool.

3. **Self-contained workflows** - Skills can include helper scripts, reference documentation, and setup instructions. Dex's complexity (DuckDB initialization, MCP server lifecycle, Field Notes schema) belongs in skill documentation, not Pi's core.

4. **No Pi modification required** - Skills are discovered automatically from `~/.pi/agent/skills/` or `.pi/skills/`. Dex can be developed, tested, and distributed independently of Pi releases.

5. **Complements MCP Apps** - Skills handle orchestration and user intent interpretation. MCP Apps handle structured output rendering. This separation keeps concerns clean: the skill decides _what_ analysis to run; the MCP App decides _how_ to present results.

FastMCP MCP Apps are recommended for structured output because:

1. **Interactive terminal UI** - MCP Apps (FastMCP v3.x) can render interactive components directly in the conversation, not just static text. This is critical for data exploration where users need to drill into tables, toggle chart views, or inspect field notes.

2. **Kitty graphics protocol support** - MCP Apps can emit the escape sequences needed for inline chart rendering via Kitty's graphics protocol. This enables pixel-perfect plots without leaving the terminal.

3. **Structured data preservation** - Unlike plain text, MCP Apps preserve data structure (types, relationships) that users may want to reference in follow-up queries or export to Field Notes.

4. **Bidirectional communication** - MCP Apps can receive user input (filter selections, parameter adjustments) and update displays dynamically. This is essential for iterative analysis.

## Options Considered

### 1. Pi Skills (Recommended for Orchestration)

**What it is:** Skills are Markdown-based capability packages that Pi loads on-demand. A skill includes a `SKILL.md` with frontmatter (name, description) and instructions referencing helper scripts, assets, and reference docs.

**How Dex would use it:**
- `SKILL.md` describes when to invoke Dex (e.g., "Use when analyzing datasets, profiling data, or creating field notes")
- Helper scripts initialize DuckDB, start the MCP server, and manage Field Notes
- Reference docs cover DuckDB schema, MCP tool catalog, and Kitty rendering options

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
- Static content only: cannot initialize DuckDB, start MCP servers, or run queries
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
- Tools execute Python code via `pi.exec()` or call the MCP server
- Results rendered via custom renderers

**Pros:**
- LLM can invoke tools directly without user commands
- Fine-grained control: separate tools for profiling, querying, note-taking
- Can stream progress updates during long-running analyses

**Cons:**
- Requires an extension to register tools (cannot be standalone)
- Tool registration is TypeScript-only: no Python-native path
- Each tool needs schema definition, error handling, rendering logic

**Verdict:** **Recommended as a complement to skills** once an extension exists. For the initial milestone, MCP tools (via FastMCP) provide similar functionality without Pi extension complexity.

### 5. MCP Integration (Recommended for Structured Output)

**What it is:** Model Context Protocol (MCP) is a standard for exposing tools, resources, and prompts to LLMs. FastMCP is a Python framework for building MCP servers.

**How Dex would use it:**
- Run a FastMCP server exposing DuckDB query tools, Field Notes resources, and analysis prompts
- Pi connects to the MCP server (via skill scripts or extension)
- Structured results (tables, charts) returned via MCP Apps

**Pros:**
- Language-agnostic: Dex core is Python; Pi is TypeScript; MCP bridges them
- FastMCP MCP Apps support interactive terminal UI and Kitty graphics
- Standard protocol: works with Claude Desktop, other MCP clients
- Clean separation: DuckDB logic stays in Python MCP server

**Cons:**
- Requires running a separate server process (stdio or HTTP transport)
- MCP configuration needed in Pi settings or skill scripts
- Slightly higher latency than native Pi tools

**Verdict:** **Recommended** for structured output and DuckDB tooling. MCP is the cleanest way to expose Python-based analytics to Pi without embedding a Python runtime in Pi.

### 6. Combination Approach (Recommended)

**Architecture:**
```
User asks analytical question in Pi TUI
           │
           ▼
┌─────────────────────────┐
│  Pi Skill: /skill:dex   │  ← Orchestrates workflow
│  - Interprets intent    │
│  - Starts MCP server    │
│  - Invokes MCP tools    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  FastMCP MCP Server     │  ← Executes analysis
│  - DuckDB tools         │
│  - Field Notes tools    │
│  - MCP Apps for output  │
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

**Why combine:**
- Skills handle user intent and workflow orchestration (Pi-native)
- MCP handles Python execution and structured output (language-agnostic)
- DuckDB stays in Python where its ecosystem lives
- Each layer can evolve independently

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
│   ├── start_mcp_server.sh  # Launch FastMCP server
│   └── query.sh             # Execute DuckDB query via MCP
├── references/
│   ├── duckdb-schema.md     # Field Notes schema documentation
│   └── mcp-tools.md         # Catalog of available MCP tools
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

### DuckDB Python Package

Dex depends on:
- `duckdb` - Core Python package (CLI and embedded runtime)
- DuckDB extensions: `httpfs`, `postgres_scanner`, `mysql_scanner`, `sqlite_scanner`, `json`, `parquet`

**Installation:**
```bash
uv add duckdb
```

**Runtime expectations:**
- DuckDB runs embedded in the FastMCP server process
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

**Field Notes schema (first-pass):**
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

## FastMCP MCP Apps for Structured Terminal Results

### FastMCP Overview

FastMCP is a Python framework for building MCP servers. Dex will use FastMCP v3.x to expose:

**Tools:**
- `query(sql: str, format: str = "markdown")` - Execute DuckDB query
- `profile_dataset(path: str)` - Profile a dataset (row count, schema, statistics)
- `list_tables()` - List all tables in current DuckDB database
- `describe_table(table: str)` - Get schema for a table
- `add_field_note(content: str, note_type: str, dataset: Optional[str])` - Append to Field Notes
- `list_field_notes(limit: int = 20, note_type: Optional[str])` - Query Field Notes

**Resources:**
- `field-notes://recent` - Recent Field Notes entries
- `field-notes://dataset/{path}` - Notes associated with a specific dataset

**Prompts:**
- `analyze-dataset(dataset_path: str)` - Prompt template for dataset analysis workflow

### MCP Apps for Kitty Terminal Rendering

FastMCP MCP Apps can render structured output directly in Pi TUI running inside Kitty.

**Kitty Graphics Protocol:**
Kitty supports inline image rendering via escape sequences. Dex can use this for charts:

```python
# Example: Emit Kitty graphics protocol escape sequence
def render_chart_inline(chart_bytes: bytes):
    # Base64-encode PNG chart
    encoded = base64.b64encode(chart_bytes).decode('ascii')
    # Emit escape sequence: ESC_G f=100 (PNG format); <payload> ESC\
    print(f"\033_Gf=100;{encoded}\033\\")
```

**MCP App UI components:**
- Tables with sorting/filtering
- Charts rendered via Kitty graphics protocol
- Field notes timeline with filtering by type
- Analysis summaries with expandable sections

### Example Flow: Dataset Profile

```
User: /skill:dex profile sales.csv

Dex Skill:
1. Starts FastMCP MCP server (stdio transport)
2. Invokes profile_dataset tool with path="sales.csv"

FastMCP Server:
1. Loads sales.csv into DuckDB
2. Computes statistics (row count, column stats, null percentages)
3. Generates summary table (Markdown format)
4. Creates bar chart of null percentages (PNG via matplotlib/kitcat)
5. Emits MCP App response with:
   - Structured table component
   - Inline chart via Kitty graphics protocol
   - Field Note entry: "Profiled sales.csv: 10K rows, 15 columns"

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

✓ Field Note added: "Profiled sales.csv"
```

## DuckDB MCP Tooling Exploration

### duckdb-mcp (ktanaka101/mcp-server-duckdb)

**What it is:** A standalone MCP server for DuckDB with a single `query` tool.

**Capabilities:**
- `query(sql: str)` - Execute any SQL query
- Read-only mode option
- Configurable database path

**Verdict:** **Too limited for Dex.** Single-tool design is intentional (LLMs can generate any SQL), but Dex needs higher-level tools (profiling, Field Notes, schema inspection) that wrap SQL. Dex should build its own FastMCP server rather than wrapping this one.

### duckdb_mcp (teaguesterling/duckdb_mcp)

**What it is:** A DuckDB extension (C++) that provides MCP client and server capabilities from within DuckDB SQL.

**Capabilities:**
- **Client mode:** Attach MCP servers and query their resources via SQL
- **Server mode:** Expose DuckDB tables as MCP resources
- Custom tool publishing: `mcp_publish_tool(name, description, sql_template, ...)`
- Security framework: allowlists for commands and URLs

**Verdict:** **Interesting but not the right fit.** This extension is designed for DuckDB-to-MCP integration (e.g., exposing DuckDB to Claude Desktop). Dex needs the inverse: Pi-to-DuckDB via MCP. The extension's complexity (security frameworks, multi-transport support) is overkill for Dex's local-first use case.

### Dex's Approach

Dex will build a **custom FastMCP server** in Python that:
- Wraps DuckDB Python package (not the duckdb_mcp extension)
- Exposes high-level tools (profiling, Field Notes, schema inspection)
- Uses MCP Apps for structured output
- Runs locally via stdio transport (no network exposure)

**Risks:**
- **MCP tool discovery:** Dex controls tool registration, so no security risk from unknown tools
- **Local data access:** DuckDB runs locally with user's permissions; no sandboxing beyond user's own account
- **Connector credentials:** External database connectors (Postgres, etc.) require credentials; these should be managed via environment variables or DuckDB secrets, not stored in Field Notes

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

These should be added to `pyproject.toml` and `.purser.toml` when implementation begins.

### Manual Validation (Initial Milestone)

For this research-only bead, validation is:
- Human review of this architecture document
- Confirmation that the recommended approach aligns with the spec's goals
- Approval to proceed with implementation beads

## Non-Goals (Preserved from Spec)

- Do not build a full production data platform
- Do not implement every DuckDB connector
- Do not create a GUI outside the terminal/Pi TUI experience
- Do not make generated code the primary user-facing artifact
- Do not bypass Purser/Beads for Dex product work
- Do not store secrets or credentials in Field Notes
- Do not configure Beads shared/server/global mode

## Next Steps

1. **Human approval** - Review and approve this architecture before generating implementation beads
2. **Implementation beads** - Create small, independently reviewable beads for:
   - Initial Python package structure (`pyproject.toml`, `src/dex/`)
   - DuckDB-backed Field Notes prototype
   - Minimal FastMCP server with profile_dataset tool
   - Pi skill for Dex orchestration
   - Example end-to-end flow with public dataset
3. **Documentation** - Expand `docs/tooling-research.md` with detailed MCP Apps and Kitty rendering research
