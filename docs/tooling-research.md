# Dex Tooling Research

This document summarizes research on tooling options for Dex: DuckDB skills, CLI tools for structured output, DuckDB MCP tooling (future consideration), and Kitty-compatible chart/graph rendering.

## 1. DuckDB Skills

### Official DuckDB Skills

**Research finding (April 2026):** Official DuckDB skills **DO exist** and are maintained by the DuckDB team.

**Repository:** https://github.com/duckdb/duckdb-skills  
**Official Skills Page:** https://officialskills.sh/duckdb/skills  
**License:** MIT  
**Stars:** 391 (as of April 2026)  
**Last update:** April 2026

**Available skills (6 total):**

| Skill | Description |
|-------|-------------|
| `attach-db` | Attaches a DuckDB database file to the current session, explores schema, writes SQL state file |
| `duckdb-docs` | Searches DuckDB/DuckLake documentation and blog posts via full-text BM25 search |
| `install-duckdb` | Installs or updates DuckDB extensions from core registry or community repos |
| `query` | Runs SQL queries against DuckDB databases or files (CSV, Parquet); accepts raw SQL or natural language |
| `read-file` | Reads/explores data files (CSV, JSON, Parquet, Avro, Excel, spatial, etc.) using DuckDB |
| `read-memories` | Searches past Claude Code session logs using DuckDB for context recovery |

**Installation mechanism:**
```bash
# From GitHub (available now)
/plugin marketplace add duckdb/duckdb-skills
/plugin install duckdb-skills@duckdb-skills

# Or via npx skills add
npx skills add https://github.com/duckdb/duckdb-skills --skill query
```

**Skills are available as `/duckdb-skills:<skill-name>` in Claude Code sessions.**

---

### Compatibility with Pi

**Key finding:** The DuckDB skills follow the **Agent Skills standard** (SKILL.md format), which is the same standard Pi uses.

**Pi skill compatibility:**
- Pi supports skills in the Agent Skills standard (SKILL.md format)
- Pi skills are compatible with Claude Code and OpenAI Codex
- Pi loads skills from `~/.pi/agent/skills/` (global) or `.pi/skills/` (project-level)
- Skills are invoked via `/skill:name` syntax in Pi

**However, there are important considerations:**

1. **Claude Code-centric design:** The skills are designed primarily for Claude Code's `/plugin` and `/duckdb-skills:` syntax. Pi uses `/skill:` syntax.

2. **DuckDB CLI dependency:** The skills invoke the **DuckDB CLI** (`duckdb` command) directly, not the DuckDB Python package. This means:
   - Users must have `duckdb` CLI installed
   - Skills use DuckDB's "Friendly SQL" dialect
   - Session state is managed via `state.sql` files

3. **Session state management:** The skills share a `state.sql` file per project containing ATTACH/USE/LOAD statements. This is append-only and idempotent.

4. **Platform support:** Tested on macOS and Linux. Windows not fully supported.

---

### Design Decision for Dex

**Decision:** Dex should **NOT use the official DuckDB skills directly** in the initial milestone, but should **interoperate with their patterns** and potentially **adapt them in the future**.

**Rationale:**

| Criterion | Official DuckDB Skills | Dex's Needs |
|-----------|----------------------|-------------|
| **Target host** | Claude Code (`/duckdb-skills:` syntax) | Pi TUI (`/skill:dex` syntax) |
| **DuckDB interface** | DuckDB CLI | DuckDB Python package (for Field Notes, programmatic control) |
| **Output format** | Text/SQL results | Structured tables + Kitty inline charts |
| **Persistence** | `state.sql` for session state | `.dex/field_notes.duckdb` for Field Notes |
| **Abstraction level** | Raw SQL + file reading | Domain-specific: profiling, Field Notes, provenance, analysis workflows |
| **Session memory** | `read-memories` searches Claude Code logs | Dex needs its own Field Notes activity log |

**Why not use directly:**
1. **Syntax mismatch:** Dex needs Pi-native `/skill:dex` integration, not Claude Code's `/duckdb-skills:`
2. **Field Notes requirement:** Dex needs append-only Field Notes with DuckDB, which the official skills don't provide
3. **Structured output:** Dex needs Kitty-compatible charts/graphs, not just text/SQL results
4. **Domain-specific workflows:** Dex needs profiling, schema inspection, and analysis recommendations—not just SQL execution

**Why not wrap:**
1. The skills are designed for Claude Code's plugin system, which Pi doesn't use
2. Wrapping would require adapting the SKILL.md files and scripts for Pi's skill loading
3. The DuckDB CLI dependency is less flexible than the DuckDB Python package for Dex's needs

**Why not adapt (yet):**
1. Initial milestone should focus on Dex's core value: Field Notes + Pi-native workflow
2. The official skills can serve as **reference implementation** for DuckDB usage patterns
3. Dex can revisit adaptation after validating the core workflow

**Recommended approach:**
- **Build Dex's own Pi skill** around the DuckDB Python package
- **Use official DuckDB skills as reference** for:
  - DuckDB "Friendly SQL" idioms (FROM-first, GROUP BY ALL, direct file access)
  - Session state patterns (append-only, idempotent)
  - Error handling and documentation lookup patterns
- **Consider future interoperability:**
  - If Dex proves valuable, the official skills could be adapted for Pi
  - Dex CLI tools could be exposed as MCP servers that Claude Code's DuckDB skills could invoke

---

### Fallback Approach

**Since the official DuckDB skills are not immediately usable for Dex's Pi-native workflow:**

1. **Dex will create its own Pi skill** (`SKILL.md`) with:
   - `/skill:dex` command prefix
   - DuckDB Python package as the core dependency
   - Field Notes integration
   - Kitty-compatible structured output

2. **Dex will document DuckDB usage patterns** specific to its workflow:
   - Dataset profiling patterns
   - Field Notes schema and append-only behavior
   - Connector initialization (local files first)
   - Error recovery and documentation lookup

3. **Dex will preserve the option to interoperate later:**
   - If users want Claude Code integration, Dex CLI tools could be exposed via MCP
   - The official DuckDB skills could invoke Dex tools for domain-specific operations

---

## 2. CLI Tools for Structured Output

### Clarification: Pi Does Not Have Built-in MCP Support

Per Pi's README: **"No MCP. Build CLI tools with READMEs (see Skills), or build an extension that adds MCP support."**

**This means:**
- Pi does NOT have built-in MCP client support
- Dex cannot use FastMCP MCP Apps directly without building a Pi extension first
- The initial architecture uses **CLI tools** invoked by Pi skills (the native path)
- MCP integration is a future evolution path requiring a Pi extension

---

## 3. DuckDB MCP Tooling

This section documents research on DuckDB MCP tooling, including `duckdb-mcp` and related projects, and evaluates whether Dex should depend on, interoperate with, or treat them as optional.

### 3.1 mcp-server-duckdb (ktanaka101)

**Repository:** https://github.com/ktanaka101/mcp-server-duckdb  
**PyPI:** https://pypi.org/project/mcp-server-duckdb/  
**Latest release:** v1.1.0 (May 2025)  
**Stars:** 172

**What it provides:**

A standalone MCP server for DuckDB with a minimal, intentional design:

| Component | Status |
|-----------|--------|
| Tools | Single `query(sql: str)` tool - executes any valid DuckDB SQL |
| Resources | None implemented |
| Prompts | None implemented |
| Transport | stdio (for Claude Desktop integration) |
| Configuration | `--db-path` (required), `--readonly` (optional), `--keep-connection` (optional) |

**Key features:**
- **Single-tool design:** Intentionally provides only `query()` - the authors argue modern LLMs can generate appropriate SQL for any operation without needing specialized endpoints
- **Read-only mode:** `--readonly` flag opens DuckDB with `read_only=True`, preventing any write operations (CREATE, INSERT, UPDATE, DELETE)
- **Auto-creation:** Database file and parent directories are created automatically if they don't exist (unless `--readonly` is set)
- **Connection reuse:** `--keep-connection` reuses a single DuckDB connection for the server lifetime (faster queries, but may hold exclusive lock)

**How it could assist Dex:**
- Could provide a ready-made MCP server for DuckDB if Dex evolves to use MCP
- Read-only mode aligns with Dex's need to prevent accidental mutations during analysis
- Minimal design means less complexity to understand

**Verdict for Dex:** **Too limited for Dex's needs.** The single-tool design is intentional but Dex requires higher-level abstractions:
- Dataset profiling (not just raw SQL execution)
- Field Notes management (append-only activity log)
- Schema inspection and discovery
- Structured output formatting (tables, charts, not just text results)
- Provenance tracking and artifact linking

**Recommendation:** **Do not depend on `mcp-server-duckdb`.** Build Dex's own CLI tools with domain-specific operations that match the data analyst workflow.

---

### 3.2 duckdb_mcp Extension (teaguesterling)

**Repository:** https://github.com/teaguesterling/duckdb_mcp  
**Documentation:** https://duckdb-mcp.readthedocs.io/  
**Latest release:** v2.1.0 (March 2026)  
**Stars:** 44  
**Language:** C++ (DuckDB extension)

**What it provides:**

A DuckDB extension that provides **bidirectional MCP integration** from within DuckDB SQL:

**MCP Client Capabilities** (DuckDB can connect to external MCP servers):
- Connect to MCP servers using stdio, TCP, or WebSocket transports
- Access remote resources via `mcp://` URI scheme with standard DuckDB functions:
  - `read_csv('mcp://server/file:///data.csv')`
  - `read_parquet('mcp://server/uri')`
  - `read_json('mcp://server/api://endpoint')`
- Execute remote tools: `mcp_call_tool('server', 'tool_name', '{"arg": "value"}')`
- Discover resources: `mcp_list_resources('server')`

**MCP Server Capabilities** (DuckDB can expose itself as an MCP server):
- Start MCP server: `mcp_server_start('stdio')` or `mcp_server_start('http', 'localhost', 8080, '{...}')`
- Publish tables as resources: `mcp_publish_table('products', 'data://tables/products', 'json')`
- Publish dynamic queries: `mcp_publish_query(sql, uri, format, interval)`
- Publish execution tools with typed parameter binding: `mcp_publish_execution_tool(...)`
- State introspection: `mcp_tools()`, `mcp_resources()`, `mcp_server_config()`

**Security Framework:**
| Setting | Description |
|---------|-------------|
| `allowed_mcp_commands` | Colon-delimited list of executable paths allowed for MCP servers |
| `allowed_mcp_urls` | Space-delimited list of URL prefixes allowed for MCP servers |
| `mcp_disable_serving` | Disable MCP server functionality entirely (client-only mode) |
| `mcp_lock_servers` | Lock MCP server configuration to prevent runtime changes |
| `mcp_log_file`, `mcp_log_level` | Logging configuration |

**Verdict for Dex:** **Interesting but not the right fit.** This extension is designed for:
- Exposing DuckDB to external MCP clients (e.g., Claude Desktop)
- Querying external MCP resources from within DuckDB SQL

Dex needs the **inverse**: **Pi-to-DuckDB via CLI tools**, with high-level analysis tools tailored to the data analyst workflow. The extension's complexity (security frameworks, multi-transport support, C++ build requirements) is overkill for Dex's local-first use case.

**Recommendation:** **Do not depend on `duckdb_mcp` extension.** Use DuckDB Python package directly in CLI tools.

---

### 3.3 Other DuckDB MCP Servers

**duckdb-mcp-server (mustafahasankhan)**  
**Repository:** https://github.com/mustafahasankhan/duckdb-mcp-server  
**PyPI:** https://pypi.org/project/duckdb-mcp-server/  

Provides more tools than ktanaka101's implementation:
- `query` - Execute any SQL query
- `analyze_schema` - Describe columns and types of a file or table
- `analyze_data` - Row count, numeric stats, date ranges, top categorical values
- `suggest_visualizations` - Suggest chart types and ready-to-run SQL queries
- `create_session` - Create or reset a session for cross-call context tracking

Also provides built-in XML documentation resources:
- `duckdb-ref://friendly-sql` - DuckDB SQL extensions reference
- `duckdb-ref://data-import` - Loading CSV, Parquet, JSON, S3/GCS data
- `duckdb-ref://visualization` - Chart patterns and query templates

**Verdict:** More feature-rich than ktanaka101's, but still **not aligned with Dex's needs**. The analysis tools are generic, not tailored to Dex's Field Notes workflow or Pi-native integration.

**Recommendation:** **Treat as optional reference only.** Do not depend on it.

---

### 3.4 DuckDB MCP Tooling Design Decision

**Decision:** Dex should **NOT depend on any DuckDB MCP tooling** in the initial milestone.

**Rationale:**

| Criterion | DuckDB MCP Tooling | Dex's Needs |
|-----------|-------------------|-------------|
| **Integration model** | MCP server for external clients (Claude Desktop, etc.) | Pi-native CLI tools invoked by skills |
| **Abstraction level** | Raw SQL or generic analysis | Domain-specific: profiling, Field Notes, provenance |
| **Output format** | Text/JSON results | Structured tables + Kitty inline charts |
| **Persistence** | Not designed for Field Notes | Append-only Field Notes with DuckDB |
| **Security model** | Allowlists for commands/URLs | Local-first, repo-scoped, no external connectors initially |
| **Build complexity** | C++ extension or separate server | Pure Python CLI tools |

**Future interoperability path:**

If Dex evolves to require MCP integration:
1. Build a Pi extension that adds MCP client support (Pi does not have built-in MCP)
2. Dex could run a FastMCP server exposing domain-specific tools
3. The Pi extension would connect Pi to the MCP server
4. At that point, Dex could **interoperate** with DuckDB MCP servers if needed, but would still maintain its own higher-level tooling

**Current stance:** **Treat DuckDB MCP tooling as optional future consideration, not a dependency.**

---

### 3.5 Security and Risk Analysis

This section identifies risks around MCP tool discovery, security, local data access, and connector credentials that Dex must consider.

#### Risk 1: MCP Tool Discovery and Trust Boundaries

**Risk:** MCP servers advertise tools dynamically. If Dex were to discover and invoke arbitrary MCP tools:
- Tools could be misnamed or misleading (e.g., `read_data` that actually exfiltrates)
- Tool schemas could change between invocations
- No guarantee of tool behavior without auditing source code

**Mitigation in DuckDB MCP tooling:**
- `duckdb_mcp` extension provides `mcp_tools()` introspection to list all published tools
- Tools are explicitly published via `mcp_publish_tool()` or `mcp_publish_execution_tool()`
- Standalone servers (ktanaka101, mustafahasankhan) have fixed, auditable tool sets

**Dex stance:** **Do not rely on dynamic MCP tool discovery.** Dex will define its own fixed set of CLI tools with explicit, versioned interfaces. If MCP interoperability is added later, Dex should maintain an allowlist of trusted MCP servers and tools.

---

#### Risk 2: Local Data Access and Path Traversal

**Risk:** MCP servers that accept file paths could be exploited for path traversal:
- `read_csv('../../../etc/passwd')` could access sensitive system files
- Database paths could point to unintended locations
- Symlinks could redirect to unexpected data sources

**Mitigation in DuckDB MCP tooling:**
- `duckdb_mcp` extension has `allowed_mcp_commands` setting (colon-delimited list of allowed executable paths)
- Standalone servers rely on the user to configure `--db-path` correctly
- No built-in path sandboxing in most implementations

**Dex stance:** **Dex must implement its own path validation.** Since Dex uses CLI tools directly (not MCP), Dex can:
- Validate that dataset paths are within the current working directory or explicitly allowed directories
- Resolve symlinks and verify the target is safe to access
- Maintain a list of allowed data source prefixes (e.g., `./data/`, `/tmp/dex/`)
- Never access paths outside the project workspace without explicit user confirmation

---

#### Risk 3: Connector Credentials and Secret Management

**Risk:** DuckDB connectors (S3, MotherDuck, PostgreSQL, etc.) require credentials. MCP servers that expose these connectors could leak credentials:
- Credentials passed via environment variables could be logged
- Credentials embedded in MCP server configs could be committed to version control
- MCP tool arguments could include credentials in plaintext
- Field Notes could accidentally persist credential metadata

**How DuckDB MCP tooling handles credentials:**
| Implementation | Credential Handling |
|----------------|--------------------|
| ktanaka101/mcp-server-duckdb | AWS credentials from env vars or `--s3-profile`; no credential storage |
| mustafahasankhan/duckdb-mcp-server | `--creds-from-env` flag; explicit env var passthrough in MCP config |
| duckdb_mcp extension | Credentials managed by DuckDB's native credential chain; `allowed_mcp_commands` can restrict which executables can be run |

**Dex stance:** **Dex must NOT store secrets or credentials in Field Notes.** This is explicitly stated in the spec non-goals. Dex will:
- Rely on DuckDB's native credential chain (AWS credentials file, environment variables)
- Never persist credentials in `.dex/field_notes.duckdb`
- Never include credentials in Field Notes metadata or artifact paths
- Document that connector credentials must be managed externally (e.g., `~/.aws/credentials`, environment variables)
- If Field Notes reference external data sources, store only the **path/URI**, never credentials

---

#### Risk 4: MCP Server Command Injection

**Risk:** MCP servers that spawn subprocesses or execute arbitrary commands could be exploited:
- `duckdb_mcp` extension allows connecting to MCP servers via `ATTACH 'python3' AS server (TYPE mcp, ARGS '["path/to/server.py"]')`
- If the command path is user-controllable, an attacker could inject arbitrary commands
- Even with allowlists, compromised allowlisted executables could be dangerous

**Mitigation in DuckDB MCP tooling:**
- `duckdb_mcp` has `allowed_mcp_commands` setting (executable paths only, no arguments)
- `mcp_lock_servers` prevents runtime changes to server configuration
- Standalone servers don't spawn subprocesses (they only run DuckDB)

**Dex stance:** **Dex CLI tools will not spawn arbitrary subprocesses.** Dex will:
- Execute only its own bundled CLI tools (via `uv run dex-*`)
- Not expose a mechanism for users to specify arbitrary commands to execute
- If Dex ever integrates with MCP, maintain a strict allowlist of MCP server executables

---

#### Risk 5: Data Exfiltration via MCP Resources

**Risk:** MCP servers that publish resources could inadvertently expose sensitive data:
- `mcp_publish_table()` could publish tables containing PII or secrets
- Resources are accessible to any MCP client that connects
- No built-in access control or authentication in most implementations

**Mitigation in DuckDB MCP tooling:**
- `duckdb_mcp` HTTP transport supports `auth_token` configuration
- Resources are explicitly published (opt-in, not automatic)
- Standalone servers don't publish resources (only execute queries)

**Dex stance:** **Dex Field Notes are repo-local and not exposed via MCP.** Dex will:
- Keep Field Notes in `.dex/field_notes.duckdb` (repo-local, not served)
- Not publish Field Notes as MCP resources
- If Dex ever exposes data via MCP, require explicit user opt-in for each published resource
- Document that `.dex/` should be added to `.gitignore` if it contains sensitive project data

---

#### Risk 6: Read-Only Enforcement Gaps

**Risk:** Analysis workflows should often be read-only, but enforcement may have gaps:
- `--readonly` mode in ktanaka101's server uses DuckDB's native `read_only=True`
- However, some DuckDB operations (e.g., TEMP table creation) may still work in read-only mode
- LLMs could generate SQL that bypasses intended restrictions

**Mitigation in DuckDB MCP tooling:**
- ktanaka101's server: `--readonly` opens DuckDB with `read_only=True`
- `duckdb_mcp` extension: read-only enforcement in query, export, and describe tools (v2.0+)
- No guarantee that all edge cases are covered

**Dex stance:** **Dex will implement defense-in-depth for read-only operations.** Dex will:
- Use DuckDB's `read_only=True` for analysis-only sessions
- Validate SQL statements before execution when in read-only mode (reject CREATE, INSERT, UPDATE, DELETE, DROP)
- Clearly distinguish read-only analysis tools from write-capable tools (e.g., Field Notes append operations)
- Log all executed queries to Field Notes for auditability

---

### 3.6 Security Summary for Dex

| Risk Area | DuckDB MCP Tooling Approach | Dex's Approach |
|-----------|----------------------------|----------------|
| **Tool discovery** | Introspection via `mcp_tools()` | Fixed CLI tool set; no dynamic discovery |
| **Path traversal** | Allowlists (`allowed_mcp_commands`) | Path validation in CLI tools; workspace scoping |
| **Credentials** | Env vars, credential chain | Never store in Field Notes; external management |
| **Command injection** | `allowed_mcp_commands`, `mcp_lock_servers` | No arbitrary subprocess spawning |
| **Data exfiltration** | Opt-in resource publishing, HTTP auth | Repo-local Field Notes; no MCP exposure |
| **Read-only enforcement** | `--readonly` flag, DuckDB native protection | Defense-in-depth: DB flag + SQL validation |

**Overall verdict:** DuckDB MCP tooling has reasonable security features for its intended use case (exposing DuckDB to MCP clients like Claude Desktop). However, **Dex's architecture (Pi-native CLI tools) does not require MCP security mechanisms** in the initial milestone. Dex will implement its own simpler, more direct security controls appropriate for local-first, repo-scoped analysis.

**If Dex evolves to use MCP:** Dex should adopt relevant security patterns from `duckdb_mcp` (allowlists, lock-down settings, explicit resource publishing) but must still maintain Dex-specific controls for Field Notes privacy and credential handling.

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

**Verdict:** **Recommended for Dex.** Broader terminal support than matplotlib-backend-kitty.

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

#### pixcat
**Repository:** https://github.com/xyproto/pixcat

**Description:** CLI and Python library wrapping the Kitty graphics protocol.

**Features:**
- Simple API for displaying images
- Supports multiple transmission modes
- Works with PIL/Pillow images

**Verdict:** Lightweight option for Dex to emit charts.

#### term-image
**Repository:** https://github.com/AnonymouX47/term-image

**Description:** Python library and CLI for displaying images in the terminal using Kitty graphics protocol.

**Verdict:** Good for displaying pre-generated images. Dex may use this for exporting charts, but needs inline generation.

### Recommended Approach for Dex

**Primary:** Use **kitcat** for chart generation.

**Rationale:**
- Matplotlib is mature and well-documented
- Backend handles Kitty protocol escape sequences
- Supports all common chart types (bar, line, scatter, histogram, etc.)
- Easy to integrate with DuckDB query results
- Broader terminal compatibility than matplotlib-backend-kitty

**Example Dex chart generation in CLI tool:**
```python
import matplotlib
matplotlib.use('kitcat')
import matplotlib.pyplot as plt
import duckdb
import io
import base64

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
    
    # Render to buffer and emit via Kitty protocol
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode('ascii')
    kitty_escape = f"\033_Gf=100;{encoded}\033\\"
    print(kitty_escape)
    
    return f"Chart displayed for {table_name}"
```

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
3. Invoke `profile_dataset.py` CLI tool

**CLI tool execution:**
1. Load `sales.csv` into DuckDB
2. Compute statistics:
   - Row count: 10,234
   - Column count: 15
   - Column types and null percentages
   - Numeric column statistics (min, max, mean, stddev)
3. Generate structured output:
   - Markdown table for schema (stdout)
   - Bar chart for null percentages (Kitty escape sequence to stdout)
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
( Rendered via Kitty graphics protocol escape sequences )

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
| **Structured Output** | CLI Tools + Kitty | Native Pi path, no extension required, Kitty escape sequences work directly |
| **DuckDB** | DuckDB Python package | Direct control, no C++ extension complexity, Field Notes support |
| **Chart Rendering** | kitcat (matplotlib backend) | Mature, Kitty protocol support, works over SSH |
| **Field Notes Storage** | Repo-local `.dex/field_notes.duckdb` | Project-specific, easy to archive, clear ownership; see `docs/field-notes-design.md` and `docs/privacy-boundaries.md` |

### Official DuckDB Skills Status

**Finding:** Official DuckDB skills **exist** (https://github.com/duckdb/duckdb-skills) but are **not directly usable** for Dex's Pi-native workflow.

**Decision:** Build Dex's own Pi skill around DuckDB Python package; use official skills as reference for DuckDB patterns.

### Do Not Depend On (Initial Milestone)

- **Official DuckDB skills (direct use)** - Claude Code-centric, DuckDB CLI-based, no Field Notes support
- **mcp-server-duckdb** - Too limited (single `query` tool)
- **duckdb_mcp extension** - Wrong direction (DuckDB-to-MCP, not Pi-to-DuckDB)
- **FastMCP MCP Apps** - Requires Pi extension (not built yet)

### Future Evolution Path

If deeper integration is needed:
1. **Adapt official DuckDB skills for Pi** - Rewrite SKILL.md for Pi syntax, use DuckDB Python instead of CLI
2. **Build a Pi extension that adds MCP client support** - Pi has no built-in MCP
3. **Run FastMCP server for DuckDB tooling** - Expose Dex CLI tools via MCP
4. **Extension connects Pi to MCP server** - Enable MCP Apps for interactive UI components

**This is NOT part of the initial milestone.**

### Review Packet and Next Steps

Human reviewers should review this document together with:

- `docs/architecture.md` for the consolidated Pi-native and DuckDB-centered architecture
- `docs/fastmcp-mcp-apps-research.md` for the future MCP Apps/Pi extension bridge path
- `docs/field-notes-design.md` for the Field Notes schema and append-only archival design
- `docs/privacy-boundaries.md` for export, credential, and local data access boundaries

Then:

1. **Human approval** - Resolve `dex-2uc` before implementation begins.
2. **Package structure** - Create `src/dex/` under the existing uv/Python validation gates.
3. **Field Notes prototype** - Implement DuckDB schema and append-only behavior.
4. **CLI tools** - Build minimal tools (`profile_dataset.py`, `query_duckdb.py`).
5. **Pi skill** - Create `SKILL.md` with orchestration scripts.
6. **End-to-end example** - Test with public data while preserving the non-goals and privacy boundaries.
