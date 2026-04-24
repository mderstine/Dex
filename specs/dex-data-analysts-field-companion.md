# Dex - The Data Analyst's Field Companion

## Status

Draft for human review. Do not generate beads from this spec until the planning approach is explicitly approved.

## Product vision

Dex is an AI-powered data analyst's field companion, inspired by the "Pokedex" as an adventurer's field companion. Dex helps users rapidly explore, connect, analyze, transform, and report on data from inside the Pi TUI.

Dex should feel like a practical terminal-native analyst partner rather than a code-generation product. It may write and run code internally when useful for analysis, but generated code is an implementation byproduct, not the user-facing feature.

## Goals

1. Define the initial product architecture for Dex as a Pi-native data analysis companion.
2. Identify and evaluate tooling that can bring the companion experience to life.
3. Establish DuckDB as the core local analytics engine for connection, wrangling, synthesis, and archival storage.
4. Incorporate officially supported DuckDB skills where available.
5. Use FastMCP, specifically MCP Apps from the latest FastMCP release, to return structured terminal-native results such as charts and tables.
6. Investigate and, where appropriate, integrate DuckDB MCP tooling for querying available MCP tools and data-related capabilities.
7. Define a "Field Notes" archival layer for analyst activity, observations, decisions, generated artifacts, and data provenance, likely backed by DuckDB.
8. Ensure Dex work itself follows the Purser workflow: plan -> execute -> review through Beads.

## User experience principles

- Dex runs through Pi TUI as the first-class host.
- The user asks analytical questions or gives exploration tasks in natural language.
- Dex connects to data sources, inspects schemas, profiles data, proposes analysis paths, and reports findings.
- Dex returns structured results directly in the terminal where possible:
  - tables
  - charts
  - summaries
  - field notes
  - recommendations
  - reproducible analysis traces
- Dex can generate code, SQL, notebooks, scripts, or intermediate files as needed, but the end user should primarily consume analysis results, not source code.
- Dex should preserve useful byproducts for auditability and reproducibility.

## Required capabilities

### 1. Pi-native companion integration

Dex must operate naturally inside Pi TUI.

Research and implementation should determine how Dex is best exposed through Pi, such as:

- Pi skills
- Pi prompt templates
- Pi extensions
- custom tools
- MCP integration
- a combination of the above

Acceptance criteria:

- A documented architecture recommendation exists for how Dex plugs into Pi.
- The recommendation explains why the chosen integration point is appropriate for an interactive data analysis companion.
- The recommendation identifies any Pi APIs, extension points, or prompt/skill conventions Dex should use.

### 2. DuckDB-centered analytics engine

DuckDB is the core data substrate for Dex.

Dex should use DuckDB for:

- local analytical querying
- connecting to supported external sources through DuckDB connectors/extensions
- data profiling and schema inspection
- transformations and intermediate analytical tables
- synthesized outputs
- persisted field notes and run metadata where appropriate

Acceptance criteria:

- The spec/architecture identifies the DuckDB Python package and CLI/runtime expectations.
- The design lists likely DuckDB extensions/connectors relevant to Dex.
- The design explains how Dex stores transient analysis data versus durable project artifacts.
- The design includes a safe default local storage location for DuckDB-backed Dex state.

### 3. Official DuckDB skills

Dex should incorporate officially supported DuckDB skills where available.

Acceptance criteria:

- Research identifies the current official DuckDB skill(s), their installation/use mechanism, and compatibility with Pi.
- The design documents whether these skills are used directly, wrapped, or adapted.
- If the official DuckDB skills are not immediately usable, the design explains the blocker and proposes a fallback.

### 4. FastMCP MCP Apps for structured terminal results

Dex should leverage the latest FastMCP release, especially MCP Apps, to provide structured results back to the terminal.

The target terminal environment is Kitty. Because Kitty supports rich terminal graphics capabilities, Dex should explore richer chart and graph experiences than plain text alone when generated artifacts are appropriate. The design should specifically investigate the best path for returning structured results via MCP Apps into Pi running in a Kitty terminal.

Structured outputs may include:

- tables
- rich charts and graphs suitable for Kitty terminal rendering
- result cards
- profiling summaries
- analysis plans
- provenance summaries
- field-note timelines

Acceptance criteria:

- Research identifies the relevant FastMCP MCP Apps APIs and current release behavior.
- The design proposes how Dex returns structured results to Pi TUI through MCP Apps.
- The design explicitly accounts for Pi running inside Kitty and evaluates Kitty-compatible rendering options for rich charts/graphs.
- At least one concrete example flow is specified, such as: user asks for a dataset profile -> Dex queries DuckDB -> Dex returns a structured table and chart/graph rendered appropriately in Kitty.
- The design distinguishes between structured terminal output and saved artifacts.

### 5. DuckDB MCP tooling exploration

Investigate DuckDB MCP tooling, including `duckdb-mcp`, as a way to query available MCP tools and interact with data tools.

Acceptance criteria:

- Research documents what `duckdb-mcp` provides and how it could assist Dex.
- The design states whether Dex should depend on `duckdb-mcp`, interoperate with it, or treat it as optional.
- The design identifies any risks around MCP tool discovery, security, local data access, or connector credentials.

### 6. Purser-driven development workflow

Work performed on Dex should use Purser's plan -> execute -> review workflow with Beads.

Acceptance criteria:

- `AGENTS.md` already explains that Purser is workflow tooling, not the product.
- Dex product work should be specified under `specs/` before bead generation.
- Bead generation must only happen after explicit human/director approval of the spec and planning approach.
- Implementation beads should be small, independently reviewable, and tied back to specs.

### 7. Field Notes archival layer

Dex should maintain Field Notes: durable records of activity, data observations, decisions, hypotheses, findings, warnings, and generated outputs.

Field Notes should support:

- chronological activity logs
- dataset observations
- schema/profile summaries
- analysis decisions and rationale
- generated query references
- source/provenance metadata
- links or paths to saved artifacts
- human-authored notes
- AI-authored notes clearly identified as such

DuckDB is the preferred storage backend because it is core to Dex.

Field Notes should be append-only by default. Corrections, superseding observations, or retractions should be represented as new note events rather than destructive edits, unless the user explicitly requests compaction or deletion.

### Dex state storage options

The initial research spike should compare these storage models before implementation:

#### Repo-local `.dex/`

Pros:

- Easy to inspect, archive, and reason about alongside the project being analyzed.
- Good fit for project-specific Field Notes, cached profiles, generated artifacts, and reproducibility metadata.
- Makes it clear which Dex state belongs to the current repository or analysis workspace.
- Simple default for local developer workflows.

Cons:

- Can accidentally capture sensitive data if ignore rules or export boundaries are unclear.
- Less convenient for cross-project memory, shared connector metadata, or global user preferences.
- May create large local files if analysis artifacts are not managed carefully.

#### User-level Dex storage

Examples: `~/.local/share/dex/`, `~/.dex/`, or another platform-appropriate user data directory.

Pros:

- Better for user preferences, reusable connection profiles, global caches, and cross-project history.
- Keeps product repos cleaner.
- Can support a consistent Dex identity across many projects.

Cons:

- Harder to audit or hand off with a specific project.
- More risk of cross-project data leakage if boundaries are not designed carefully.
- Less obvious to users where Field Notes and artifacts live.

#### Hybrid storage

Use repo-local `.dex/` for project/workspace-specific Field Notes and artifacts, plus user-level storage for preferences, reusable safe metadata, and optional shared caches.

Pros:

- Best separation between project-specific analytical evidence and user-level Dex configuration.
- Supports reproducibility without losing convenience.
- Allows sensitive project artifacts to stay local to the repo/workspace while user preferences persist globally.

Cons:

- More complex to implement and document.
- Requires clear rules for what belongs in each layer.
- Requires careful export, cleanup, and privacy behavior.

Initial default recommendation to validate during research: use repo-local `.dex/` for Field Notes and analysis artifacts, with user-level storage reserved for non-sensitive preferences and reusable configuration.

Acceptance criteria:

- The design proposes a DuckDB schema for Field Notes or a first-pass schema outline.
- The design defines where the Field Notes database lives by default, with explicit rationale for repo-local, user-level, or hybrid storage.
- The design explains how notes are appended during analysis sessions.
- The design explains how users can query, summarize, export, or archive Field Notes.
- The design distinguishes Field Notes from Purser/Beads workflow metadata.

## Proposed initial deliverables

The first implementation milestone should be a research spike. The research spike should produce enough evidence to choose the initial architecture before larger implementation work begins.

Likely deliverables include:

1. Research spike covering Dex's Pi-native integration model, DuckDB skills, FastMCP MCP Apps, DuckDB MCP tooling, Kitty rendering options, and Field Notes storage choices.
2. Architecture document for Dex's Pi-native integration model.
3. Tooling research summary covering DuckDB skills, FastMCP MCP Apps, DuckDB MCP tooling, and Kitty-compatible chart/graph rendering.
4. Initial Python package structure for Dex.
5. DuckDB-backed Field Notes prototype.
6. Minimal Pi-facing Dex workflow prompt or skill.
7. Minimal FastMCP/MCP Apps prototype returning structured table/chart-like output.
8. Example end-to-end analysis flow using downloaded public example data.
9. Documentation for local developer setup and user-facing Dex workflow.

## Candidate files and areas

Likely files or directories to create or update:

- `README.md`
- `pyproject.toml`
- `src/dex/`
- `src/dex/field_notes.py`
- `src/dex/duckdb_runtime.py`
- `src/dex/mcp_app.py`
- `src/dex/pi_integration/`
- `examples/`
- `docs/architecture.md`
- `docs/tooling-research.md`
- `tests/`
- `.purser.toml` if real validation commands are added

Exact file layout should be refined during planning.

## Validation expectations

The repo currently has no real lint, type-check, or test commands configured. Part of the approved implementation plan should decide whether to add validation tooling.

Recommended validation direction for a Python + uv repo:

- `uv run ruff check . && uv run ruff format --check .`
- `uv run ty check`
- `uv run pytest -x --tb=short`

Acceptance criteria before substantial implementation work:

- If these tools are added to `pyproject.toml`, `.purser.toml` gates must be updated to match the real commands.
- If validation tooling is deferred, implementation beads must define honest manual validation commands.

## Non-goals for the initial spec

- Do not build a full production data platform.
- Do not implement every DuckDB connector.
- Do not create a GUI outside the terminal/Pi TUI experience.
- Do not make generated code the primary user-facing artifact.
- Do not bypass Purser/Beads for Dex product work.
- Do not store secrets or credentials in Field Notes.
- Do not configure Beads shared/server/global mode.
- Do not generate beads from this draft until human approval is given.

## Open questions and current decisions

1. First milestone: research spike.
2. Dex state storage: compare repo-local `.dex/`, user-level storage, and hybrid storage during the research spike. Initial default recommendation to validate is repo-local `.dex/` for Field Notes and analysis artifacts, with user-level storage reserved for non-sensitive preferences and reusable configuration.
3. Initial data source priority: local files first.
4. Field Notes mutability: append-only by default.
5. Structured chart/graph formats for Pi running in Kitty: research before deciding. The team is not yet confident which option will work best.
6. Exploratory research/planning model: use `gpt-5.5`.
7. Initial example data: use downloaded public examples to keep the product lightweight.
