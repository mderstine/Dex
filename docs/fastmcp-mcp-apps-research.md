# FastMCP MCP Apps and Kitty Structured Output Research

## Executive Summary

This research evaluates FastMCP MCP Apps as a structured-output target for Dex, enabling Pi running in Kitty to display rich charts, tables, and interactive UIs. The research identifies integration paths, evaluates Pi extension/adapter options, and specifies concrete example flows for data analysis workflows.

**Key Finding**: FastMCP 3.0+ provides production-ready MCP Apps support with Prefab UI components, but Pi lacks native MCP server/App integration. The recommended integration path is a **project-local Pi extension (TypeScript) with MCP client adapter** that bridges FastMCP structured outputs to Pi TUI's custom tool rendering system, including Kitty-compatible image rendering via Pi's TUI components.

---

## 1. FastMCP MCP Apps APIs and Current Release Behavior

### FastMCP 3.0 Architecture (Released February 18, 2026)

FastMCP 3.0 represents a major architectural shift from "tool servers" to "Context Applications" with MCP Apps as a first-class target.

#### Core Primitives

1. **Providers**: Data sources for tools, resources, and prompts
   - `FileSystemProvider`: Discovers tools from directories with hot-reload
   - `OpenAPIProvider`: Wraps REST APIs as MCP tools
   - `ProxyProvider`: Proxies remote MCP servers
   - `SkillsProvider`: Delivers agent skills as resources

2. **Transforms**: Middleware for modifying components
   - `NamespaceTransform`: Adds prefixes to avoid name collisions
   - `FilterTransform`: Controls component visibility
   - `VisibilityFilter`: Enables/disables components per session

3. **Components**: Tools, prompts, resources exposed to AI agents

#### MCP Apps Support (Phase 1 - 3.0, Full in 3.1+)

FastMCP 3.0 includes spec-level MCP Apps compatibility:

- `ui://` resource scheme for UI metadata
- Typed UI metadata via `AppConfig`
- Extension negotiation with MCP clients
- Runtime detection of Apps-capable hosts

**Prefab UI Integration** (requires `fastmcp[apps]` extra):

```python
from prefab_ui.app import PrefabApp
from prefab_ui.components import Column, Heading
from prefab_ui.components.charts import BarChart, ChartSeries
from fastmcp import FastMCP

mcp = FastMCP("Dashboard")

@mcp.tool(app=True)
def revenue_chart(year: int) -> PrefabApp:
    """Show annual revenue as an interactive bar chart."""
    data = [
        {"quarter": "Q1", "revenue": 42000},
        {"quarter": "Q2", "revenue": 51000},
        {"quarter": "Q3", "revenue": 47000},
        {"quarter": "Q4", "revenue": 63000},
    ]
    
    with Column(gap=4, css_class="p-6") as view:
        Heading(f"{year} Revenue")
        BarChart(
            data=data,
            series=[ChartSeries(data_key="revenue", label="Revenue")],
            x_axis="quarter",
        )
    
    return PrefabApp(view=view)
```

#### Structured Output Support (6/18/2025 MCP Spec)

FastMCP automatically generates structured outputs from return type annotations:

```python
from dataclasses import dataclass

@dataclass
class UserProfile:
    name: str
    age: int
    email: str

@mcp.tool
def get_user_profile(user_id: str) -> UserProfile:
    """Get a user's profile information."""
    return UserProfile(name="Alice", age=30, email="alice@example.com")
```

**Automatic behavior**:
- Object-like results (`dict`, Pydantic models, dataclasses) → Always become structured content
- Non-object results (`int`, `str`, `list`) → Become structured content if return type annotation exists
- All results → Always become traditional content blocks for backward compatibility

**Output schema generation**:
- Primitive types wrapped under `"result"` key
- Complex types generate full JSON Schema
- Manual override via `output_schema` parameter

#### ToolResult for Full Control

```python
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

@mcp.tool
def advanced_tool() -> ToolResult:
    """Tool with full control over output."""
    return ToolResult(
        content=[TextContent(type="text", text="Human-readable summary")],
        structured_content={"data": "value", "count": 42},
        meta={"execution_time_ms": 145}
    )
```

---

## 2. Pi Extension/Adapter/Bridge Architecture for MCP Apps

### Problem Statement

Pi does not provide native MCP server/App integration. Dex requires a bridge to return FastMCP structured outputs (tables, charts, UIs) to Pi TUI running in Kitty.

**Critical Architecture Correction**: Pi extensions are **TypeScript modules**, not Python code. They are auto-discovered from `.pi/extensions/` (project-local) or `~/.pi/agent/extensions/` (global). Custom tools are registered via `pi.registerTool()` with optional `renderCall` and `renderResult` functions for TUI rendering.

### Evaluated Integration Paths

#### Option 1: Project-Local Pi Extension with MCP Client Adapter (RECOMMENDED)

**Architecture**:
```
┌─────────────────┐     ┌──────────────────────────┐     ┌─────────────────┐
│   Pi TUI Host   │────▶│  Dex Pi Extension        │────▶│  FastMCP Server │
│  (Kitty term)   │◀────│  (TypeScript, .pi/ext/)  │◀────│  (Dex Backend)  │
└─────────────────┘     └──────────────────────────┘     └─────────────────┘
                                │
                                ▼
                      ┌──────────────────────────┐
                      │  Pi TUI Custom Renderer  │
                      │  (Image component for    │
                      │   Kitty-compatible PNG)  │
                      └──────────────────────────┘
```

**Implementation**:
- Create `.pi/extensions/dex-mcp-adapter.ts` (TypeScript, NOT Python)
- Implement MCP client using `fastmcp.Client` or low-level MCP SDK via Node.js
- Register custom Pi tool via `pi.registerTool()` with `renderResult` for structured outputs
- Use Pi TUI's `Image` component for Kitty-compatible chart rendering (PNG bytes via base64)

**Pi Extension Example** (TypeScript):

```typescript
// .pi/extensions/dex-mcp-adapter.ts
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { Text, Image, Box, VStack } from "@mariozechner/pi-tui";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";

export default function (pi: ExtensionAPI) {
  let mcpClient: Client | null = null;

  pi.on("session_start", async () => {
    // Initialize MCP client to Dex FastMCP server
    mcpClient = new Client({
      name: "dex-pi-adapter",
      version: "1.0.0",
    });
    
    // Connect to local FastMCP server (stdio or SSE transport)
    const transport = /* ... configure transport ... */;
    await mcpClient.connect(transport);
  });

  pi.registerTool({
    name: "dex_profile_dataset",
    label: "Dex Profile Dataset",
    description: "Profile a dataset using Dex's DuckDB backend",
    parameters: Type.Object({
      path: Type.String({ description: "Path to dataset (CSV, Parquet, etc.)" }),
    }),
    async execute(_toolCallId, params) {
      if (!mcpClient) {
        throw new Error("MCP client not initialized");
      }

      // Call FastMCP tool on Dex backend
      const result = await mcpClient.callTool({
        name: "profile_dataset",
        arguments: { path: params.path },
      });

      // Return structured result with details for rendering
      return {
        content: [{ type: "text", text: `Profiled ${params.path}` }],
        details: {
          profile: result.structured_content,
          chartBytes: result.details?.chartBytes, // PNG bytes as base64
        },
      };
    },
    renderResult(result, _options, theme) {
      const details = result.details as { profile?: any; chartBytes?: string } | undefined;
      if (!details) {
        return new Text("No details", 0, 0);
      }

      const lines: string[] = [];
      
      // Render profile summary as text
      if (details.profile) {
        lines.push(theme.fg("toolTitle", `Dataset: ${details.profile.path}`));
        lines.push(theme.fg("text", `Rows: ${details.profile.row_count}`));
        lines.push(theme.fg("text", `Columns: ${details.profile.column_count}`));
      }

      // Render chart using Pi TUI Image component (Kitty-compatible)
      if (details.chartBytes) {
        const imageComponent = new Image(
          Buffer.from(details.chartBytes, 'base64'),
          'image/png',
          { maxWidth: 80, maxHeight: 24 }
        );
        return new VStack([
          new Text(lines.join('\n'), 0, 0),
          imageComponent,
        ]);
      }

      return new Text(lines.join('\n'), 0, 0);
    },
  });
}
```

**Pros**:
- Uses Pi's supported extension architecture (TypeScript modules)
- Leverages Pi TUI's built-in `Image` component for Kitty graphics
- Full control over MCP Apps integration behavior
- Can evolve independently of Pi core
- Aligns with Pi extension architecture and auto-discovery

**Cons**:
- Requires implementing MCP client logic in TypeScript/Node.js
- Must handle MCP protocol state management
- Additional maintenance burden

**Estimated Effort**: 2-3 days for minimal viable implementation

#### Option 2: Custom Pi Tools with Direct FastMCP Python API (HYBRID)

**Architecture**:
```
┌─────────────────┐     ┌──────────────────────────┐
│   Pi TUI Host   │────▶│  Pi Extension (TS)       │
│  (Kitty term)   │◀────│  + Custom Tool Renderer  │
└─────────────────┘     └──────────────────────────┘
                                │
                                ▼
                      ┌──────────────────────────┐
                      │  Dex Python Backend      │
                      │  (via subprocess/CLI)    │
                      └──────────────────────────┘
```

**Implementation**:
- Pi extension (TypeScript) invokes Dex CLI via `pi.exec()`
- Dex CLI wraps FastMCP Python tools
- Parse JSON output and render via Pi TUI components

**Pros**:
- Keeps Dex backend in Python (DuckDB, FastMCP native)
- Simpler than full MCP client implementation
- Direct integration with Pi tool system

**Cons**:
- Process spawning overhead
- Loses interactive/progress reporting capabilities
- More complex state management for multi-step workflows

**Estimated Effort**: 1-2 days for minimal viable implementation

#### Option 3: CLI-to-Extension Bridge via JSON (SIMPLEST MVP)

**Architecture**:
```
┌─────────────────┐     ┌──────────────────────────┐     ┌─────────────────┐
│   Pi TUI Host   │────▶│  Pi Extension (TS)       │────▶│  Dex CLI        │
│  (Kitty term)   │◀────│  (CLI Invoker + Render)  │◀────│  (FastMCP Host) │
└─────────────────┘     └──────────────────────────┘     └─────────────────┘
```

**Implementation**:
- Expose Dex as CLI via `uv run dex profile <path> --json`
- Pi extension invokes CLI via `pi.exec()`
- Parse JSON output and render using Pi TUI `Image` component

**Pi Extension Example**:

```typescript
// .pi/extensions/dex-cli-bridge.ts
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { Text, Image, VStack } from "@mariozechner/pi-tui";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "dex_profile",
    label: "Dex Profile",
    description: "Profile a dataset using Dex CLI",
    parameters: Type.Object({
      path: Type.String({ description: "Path to dataset" }),
    }),
    async execute(_toolCallId, params, signal) {
      // Invoke Dex CLI
      const result = await pi.exec(
        "uv",
        ["run", "dex", "profile", params.path, "--json"],
        { signal }
      );

      if (result.code !== 0) {
        throw new Error(`Dex CLI failed: ${result.stderr}`);
      }

      const profile = JSON.parse(result.stdout);

      return {
        content: [{ type: "text", text: `Profiled ${params.path}` }],
        details: {
          profile,
          chartPath: profile.chart_path, // Path to saved PNG
        },
      };
    },
    renderResult(result, _options, theme) {
      const details = result.details as { profile?: any; chartPath?: string } | undefined;
      if (!details || !details.profile) {
        return new Text("No profile data", 0, 0);
      }

      const lines = [
        theme.fg("toolTitle", `Dataset: ${details.profile.path}`),
        theme.fg("text", `Rows: ${details.profile.row_count}`),
        theme.fg("text", `Columns: ${details.profile.column_count}`),
      ];

      // Render chart from file using Pi TUI Image component
      if (details.chartPath) {
        const fs = await import("node:fs/promises");
        const chartBytes = await fs.readFile(details.chartPath);
        const imageComponent = new Image(
          chartBytes,
          'image/png',
          { maxWidth: 80, maxHeight: 24 }
        );
        return new VStack([
          new Text(lines.join('\n'), 0, 0),
          imageComponent,
        ]);
      }

      return new Text(lines.join('\n'), 0, 0);
    },
  });
}
```

**Pros**:
- Leverages FastMCP CLI tooling
- Clean separation between Pi (TypeScript) and Dex (Python)
- Easy to test independently
- Uses Pi TUI's supported `Image` component for Kitty rendering

**Cons**:
- Process spawning overhead
- Loses interactive/progress reporting capabilities

**Estimated Effort**: 1 day for minimal viable implementation

---

## 3. Kitty-Compatible Rendering Options via Pi TUI

### Pi TUI Image Component

Pi provides a built-in `Image` component in `@mariozechner/pi-tui` that handles Kitty graphics protocol automatically:

```typescript
import { Image } from "@mariozechner/pi-tui";

// From bytes (PNG, JPEG, etc.)
const imageComponent = new Image(
  buffer,           // Node.js Buffer with image bytes
  'image/png',      // MIME type
  { maxWidth: 80, maxHeight: 24 }  // Optional size constraints
);
```

**Key Features**:
- Automatically emits Kitty graphics protocol APC escape sequences
- Handles chunked transfer for large images
- Respects terminal capabilities (falls back gracefully)
- Integrates with Pi TUI layout system (Box, VStack, HStack, etc.)

### Chart Generation in Dex (Python Backend)

Dex should generate charts using Python libraries and return PNG bytes to the Pi extension:

#### Recommended: `matplotlib` → PNG bytes

```python
# src/dex/visualization.py
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import io
import base64

def generate_histogram(data: list[float], title: str = "") -> bytes:
    """Generate histogram and return PNG bytes."""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.hist(data, bins=30, edgecolor='black')
    ax.set_title(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Frequency")
    
    # Render to bytes
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig)
    
    return buf.read()

def generate_bar_chart(categories: list[str], values: list[float], title: str = "") -> bytes:
    """Generate bar chart and return PNG bytes."""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar(categories, values)
    ax.set_title(title)
    ax.set_xlabel("Category")
    ax.set_ylabel("Count")
    plt.xticks(rotation=45)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig)
    
    return buf.read()
```

#### Alternative: `plotnine` for Grammar of Graphics

```python
from plotnine import ggplot, aes, geom_histogram, geom_bar
import pandas as pd
import io

def generate_histogram_plotnine(data: pd.DataFrame, column: str, title: str = "") -> bytes:
    """Generate histogram using plotnine grammar of graphics."""
    plot = (
        ggplot(data, aes(x=column))
        + geom_histogram(bins=30, fill="steelblue", color="black")
        + ggplot2.labs(title=title, x=column, y="Frequency")
    )
    
    buf = io.BytesIO()
    plot.save(buf, format='png', dpi=100, verbose=False)
    buf.seek(0)
    
    return buf.read()
```

### Rendering Flow: Dex Backend → Pi Extension → Kitty

```
1. Dex Python Backend (FastMCP tool)
   - Generate chart using matplotlib/plotnine
   - Return PNG bytes (base64-encoded) in structured_content or details

2. Pi Extension (TypeScript, .pi/extensions/)
   - Receive structured result via MCP client or CLI
   - Decode base64 PNG bytes to Node.js Buffer

3. Pi TUI Custom Renderer
   - Create Image component: new Image(buffer, 'image/png', options)
   - Return VStack/HStack with text + image components

4. Kitty Terminal
   - Pi TUI emits Kitty graphics protocol APC sequences
   - Kitty renders inline image under/over text
```

---

## 4. Concrete Example Flow: Dataset Profile → Structured Table + Chart

### Scenario

User asks: "Profile the sales_data.csv dataset"

### End-to-End Flow (Recommended Architecture)

```
1. User Input (Pi TUI)
   "Profile the sales_data.csv dataset"

2. Pi Extension (TypeScript, .pi/extensions/dex-mcp-adapter.ts)
   - Custom tool: dex_profile_dataset(path: string)
   - MCP client calls Dex FastMCP server

3. Dex FastMCP Server (Python, src/dex/mcp_server.py)
   @mcp.tool
   def profile_dataset(path: str) -> DatasetProfile:
       conn = duckdb.connect()
       
       # Compute statistics via DuckDB
       row_count = conn.execute(
           f"SELECT COUNT(*) FROM read_csv_auto('{path}')"
       ).fetchone()[0]
       
       # Get column stats
       columns = [...]  # List of ColumnProfile
       
       # Generate histogram for numeric columns
       chart_bytes = generate_histogram(data, title="Distribution")
       
       return DatasetProfile(
           path=path,
           row_count=row_count,
           column_count=len(columns),
           columns=columns,
           chart_bytes=base64.b64encode(chart_bytes).decode('utf-8')
       )

4. Pi Extension (Renderer)
   - Receive structured result with profile + chart_bytes
   - Decode base64 to Buffer
   - Render via Pi TUI components:
     return new VStack([
       new Text(profileSummary, 0, 0),
       new Image(chartBuffer, 'image/png', { maxWidth: 80, maxHeight: 24 }),
     ]);

5. User Sees (Pi TUI in Kitty)
   - Formatted text with column stats
   - Inline histogram rendered via Kitty graphics protocol
   - All within Pi TUI layout system
```

### Implementation Sketch

**Dex FastMCP Server (Python)**:

```python
# src/dex/mcp_server.py
from fastmcp import FastMCP
from dataclasses import dataclass
from typing import List
import duckdb
import base64
from dex.visualization import generate_histogram

mcp = FastMCP("Dex")

@dataclass
class ColumnProfile:
    name: str
    dtype: str
    null_count: int
    unique_count: int
    mean: float | None
    std: float | None

@dataclass
class DatasetProfile:
    path: str
    row_count: int
    column_count: int
    columns: List[ColumnProfile]
    chart_bytes: str  # base64-encoded PNG

@mcp.tool
def profile_dataset(path: str) -> DatasetProfile:
    """Profile a dataset and return structured statistics."""
    conn = duckdb.connect()
    
    # Get row count
    row_count = conn.execute(
        f"SELECT COUNT(*) FROM read_csv_auto('{path}')"
    ).fetchone()[0]
    
    # Get column stats
    columns = []
    for col in conn.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{path}')").fetchall():
        col_name = col[0]
        col_type = col[1]
        
        stats = conn.execute(f"""
            SELECT 
                COUNT(*) - COUNT({col_name}) as nulls,
                COUNT(DISTINCT {col_name}) as uniques,
                AVG({col_name}) as mean,
                STDDEV({col_name}) as std
            FROM read_csv_auto('{path}')
        """).fetchone()
        
        columns.append(ColumnProfile(
            name=col_name,
            dtype=col_type,
            null_count=stats[0],
            unique_count=stats[1],
            mean=float(stats[2]) if stats[2] else None,
            std=float(stats[3]) if stats[3] else None
        ))
    
    # Generate histogram for first numeric column
    numeric_cols = [c for c in columns if c.dtype in ('BIGINT', 'DOUBLE', 'FLOAT')]
    chart_bytes = ""
    if numeric_cols:
        data = conn.execute(f"""
            SELECT {numeric_cols[0].name} 
            FROM read_csv_auto('{path}') 
            WHERE {numeric_cols[0].name} IS NOT NULL
        """).fetchdf()[numeric_cols[0].name].tolist()
        
        png_bytes = generate_histogram(data, title=f"Distribution: {numeric_cols[0].name}")
        chart_bytes = base64.b64encode(png_bytes).decode('utf-8')
    
    return DatasetProfile(
        path=path,
        row_count=row_count,
        column_count=len(columns),
        columns=columns,
        chart_bytes=chart_bytes
    )
```

**Pi Extension (TypeScript)**:

```typescript
// .pi/extensions/dex-mcp-adapter.ts
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { Text, Image, VStack } from "@mariozechner/pi-tui";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

interface DatasetProfile {
  path: string;
  row_count: number;
  column_count: number;
  columns: Array<{
    name: string;
    dtype: string;
    null_count: number;
    unique_count: number;
    mean: number | null;
    std: number | null;
  }>;
  chart_bytes: string;  // base64-encoded PNG
}

export default function (pi: ExtensionAPI) {
  let mcpClient: Client | null = null;

  pi.on("session_start", async () => {
    // Initialize MCP client to Dex FastMCP server
    mcpClient = new Client({
      name: "dex-pi-adapter",
      version: "1.0.0",
    });

    const transport = new StdioClientTransport({
      command: "uv",
      args: ["run", "python", "-m", "dex.mcp_server"],
    });

    await mcpClient.connect(transport);
  });

  pi.registerTool({
    name: "dex_profile_dataset",
    label: "Dex Profile Dataset",
    description: "Profile a dataset using Dex's DuckDB backend",
    parameters: Type.Object({
      path: Type.String({ description: "Path to dataset (CSV, Parquet, etc.)" }),
    }),
    async execute(_toolCallId, params, signal) {
      if (!mcpClient) {
        throw new Error("MCP client not initialized");
      }

      const result = await mcpClient.callTool({
        name: "profile_dataset",
        arguments: { path: params.path },
      }, undefined, signal);

      return {
        content: [{ type: "text", text: `Profiled ${params.path}` }],
        details: result.structured_content as DatasetProfile,
      };
    },
    renderResult(result, _options, theme) {
      const profile = result.details as DatasetProfile | undefined;
      if (!profile) {
        return new Text("No profile data", 0, 0);
      }

      const lines = [
        theme.fg("toolTitle", `Dataset: ${profile.path}`),
        theme.fg("text", `Rows: ${profile.row_count}`),
        theme.fg("text", `Columns: ${profile.column_count}`),
        "",
        theme.fg("muted", "Columns:"),
        ...profile.columns.map(col =>
          theme.fg("text", `  ${col.name} (${col.dtype}): nulls=${col.null_count}, unique=${col.unique_count}`)
        ),
      ];

      // Render chart using Pi TUI Image component (Kitty-compatible)
      if (profile.chart_bytes) {
        const chartBuffer = Buffer.from(profile.chart_bytes, 'base64');
        const imageComponent = new Image(
          chartBuffer,
          'image/png',
          { maxWidth: 80, maxHeight: 24 }
        );
        return new VStack([
          new Text(lines.join('\n'), 0, 0),
          imageComponent,
        ]);
      }

      return new Text(lines.join('\n'), 0, 0);
    },
  });
}
```

---

## 5. Structured Terminal Output vs Saved Artifacts

### Distinction

**Structured Terminal Output**:
- Transient, displayed inline in Pi TUI
- Rendered via Pi TUI components (Text, Image, VStack, etc.)
- Not persisted unless explicitly saved by user
- Examples: inline charts (via Image component), formatted tables, summary cards

**Saved Artifacts**:
- Persisted to disk (`.dex/` or user-level storage)
- Referenced by Field Notes
- Reproducible and shareable
- Examples: PNG files, CSV exports, SQL scripts, analysis traces

### Implementation Strategy

```python
# src/dex/tools/profiling.py
from fastmcp.tools.tool import ToolResult
from pathlib import Path
import base64

@mcp.tool
def profile_with_artifacts(path: str, save_charts: bool = False) -> ToolResult:
    """Profile dataset with optional artifact saving."""
    profile = profile_dataset(path)
    
    # Structured content for programmatic use
    structured = {
        "profile": profile.__dict__,
        "chart_bytes": profile.chart_bytes,  # base64 PNG for inline rendering
        "chart_paths": []
    }
    
    # Content blocks for display
    content = [render_profile_summary(profile)]
    
    # Optionally save charts as artifacts
    if save_charts:
        artifact_dir = Path(".dex/artifacts")
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        chart_path = artifact_dir / f"profile_histogram.png"
        chart_path.write_bytes(base64.b64decode(profile.chart_bytes))
        structured["chart_paths"].append(str(chart_path))
        
        content.append(f"\nChart saved to: {chart_path}")
    
    return ToolResult(
        content=content,
        structured_content=structured,
        meta={"artifact_dir": str(artifact_dir) if save_charts else None}
    )
```

### Field Notes Integration

```python
# src/dex/field_notes.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import duckdb

@dataclass
class FieldNote:
    id: str
    timestamp: datetime
    note_type: str  # 'observation', 'decision', 'finding', 'warning'
    content: str
    artifact_paths: List[str] = field(default_factory=list)
    dataset_path: str | None = None
    ai_generated: bool = True

class FieldNotes:
    def __init__(self, db_path: str = ".dex/field_notes.duckdb"):
        self.db = duckdb.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS field_notes (
                id VARCHAR PRIMARY KEY,
                timestamp TIMESTAMP,
                note_type VARCHAR,
                content TEXT,
                artifact_paths VARCHAR[],
                dataset_path VARCHAR,
                ai_generated BOOLEAN
            )
        """)
    
    def append(self, note: FieldNote):
        self.db.execute("""
            INSERT INTO field_notes VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            note.id, note.timestamp, note.note_type,
            note.content, note.artifact_paths,
            note.dataset_path, note.ai_generated
        ])
    
    def query_by_dataset(self, dataset_path: str) -> List[FieldNote]:
        results = self.db.execute("""
            SELECT * FROM field_notes 
            WHERE dataset_path = ? 
            ORDER BY timestamp DESC
        """, [dataset_path]).fetchall()
        return [self._row_to_note(r) for r in results]
```

---

## 6. Integration Recommendations for Dex

### Recommended Architecture

**Phase 1 (MVP)**:
1. Implement Dex as FastMCP server with structured outputs (Python)
2. Create minimal Pi extension (TypeScript) with MCP client adapter using stdio transport
3. Use Pi TUI's `Image` component for Kitty graphics rendering (PNG bytes)
4. Support tables (text) and charts (PNG via Image component)

**Phase 2**:
1. Add Prefab UI Apps for interactive dashboards (if Pi TUI supports custom interactive components)
2. Implement Field Notes archival layer with DuckDB
3. Add artifact saving and provenance tracking
4. Support advanced Pi TUI layouts (VStack, HStack, Box) for richer presentations

**Phase 3**:
1. Integrate DuckDB MCP tooling (`duckdb-mcp`) if available
2. Add official DuckDB skills if compatible with Pi
3. Implement advanced Kitty features via Pi TUI Image component options
4. Support cross-project Field Notes via user-level storage

### File Structure

```
.pi/extensions/
└── dex-mcp-adapter.ts       # Pi extension (TypeScript, auto-discovered)

src/dex/
├── __init__.py
├── mcp_server.py            # FastMCP server definition
├── tools/
│   ├── __init__.py
│   ├── profiling.py         # Dataset profiling tools
│   ├── querying.py          # DuckDB query tools
│   └── visualization.py     # Chart generation (matplotlib → PNG bytes)
├── field_notes.py           # Field Notes archival layer
└── duckdb_runtime.py        # DuckDB connection management

.dex/
├── field_notes.duckdb       # Repo-local Field Notes
└── artifacts/               # Saved charts, exports, etc.
```

### Validation and Next Steps

1. **Create FastMCP server prototype** with 2-3 profiling tools (Python)
2. **Implement Pi extension skeleton** (TypeScript) with MCP client via stdio transport
3. **Test Pi TUI Image rendering** with sample PNG bytes in Kitty
4. **Document example workflows** for user validation
5. **Gather feedback** before expanding implementation scope

---

## 7. Risks and Open Questions

### Risks

1. **Pi Extension Complexity**: Pi extension API may have undocumented limitations for MCP client integration
2. **MCP SDK for Node.js**: `@modelcontextprotocol/sdk` npm package maturity and stability
3. **FastMCP Version Drift**: FastMCP 3.x is rapidly evolving; API changes expected
4. **Performance**: Large datasets may cause slow rendering or memory issues
5. **Image Size**: Large PNG charts may exceed Pi TUI or Kitty transfer limits

### Open Questions

1. **MCP Transport**: What is the most reliable transport for Pi ↔ Dex communication? (stdio, SSE, WebSocket)
2. **DuckDB Skills**: Are official DuckDB skills compatible with Pi's skill system?
3. **Authentication**: How should Dex handle credentials for external data sources?
4. **Fallback Rendering**: What is the fallback for non-Kitty terminals? (ASCII charts, text-only)

### Clarification Notes

- **Pi Extension API**: Pi extensions are TypeScript modules in `.pi/extensions/` or `~/.pi/agent/extensions/`, NOT Python code
- **Custom Rendering**: Use `pi.registerTool()` with `renderResult` returning Pi TUI components (`Text`, `Image`, `VStack`, etc.)
- **Kitty Rendering**: Pi TUI's `Image` component handles Kitty graphics protocol automatically; do NOT emit escape sequences directly from Python
- **DuckDB MCP Tooling**: `duckdb-mcp` exists but compatibility with Dex architecture needs evaluation
- **Terminal Capability Detection**: Should implement fallback for non-Kitty terminals (text-only rendering)

---

## References

- FastMCP 3.0 Documentation: https://gofastmcp.com/
- FastMCP Apps: https://gofastmcp.com/apps/overview
- Pi Extensions Documentation: `/home/md/.nvm/versions/node/v22.17.0/lib/node_modules/@mariozechner/pi-coding-agent/docs/extensions.md`
- Pi TUI Components: `/home/md/.nvm/versions/node/v22.17.0/lib/node_modules/@mariozechner/pi-coding-agent/docs/tui.md`
- Kitty Graphics Protocol: https://sw.kovidgoyal.net/kitty/graphics-protocol/
- MCP Specification: https://modelcontextprotocol.io/
- Model Context Protocol SDK (Node.js): https://github.com/modelcontextprotocol/typescript-sdk
