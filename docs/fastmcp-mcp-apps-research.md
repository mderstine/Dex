# FastMCP MCP Apps and Kitty Structured Output Research

## Executive Summary

Dex should keep **FastMCP MCP Apps as a core product target**, but Pi does not currently provide native MCP server/App integration. The correct initial target is therefore not "Pi natively renders MCP Apps"; it is a **project-local Pi extension bridge** that connects Dex's Python/FastMCP backend to Pi's supported TypeScript extension and TUI rendering APIs.

Recommended direction:

```text
Pi TUI in Kitty
  -> project-local Pi extension: .pi/extensions/dex-mcp-adapter.ts
    -> pi.registerTool() custom Dex tools
    -> renderResult() / registerMessageRenderer() / ctx.ui.custom() for UI
    -> MCP client or CLI bridge to Dex FastMCP server
      -> DuckDB-backed Dex analysis tools
      -> FastMCP MCP Apps / Prefab UI structured content
```

The bridge must translate MCP Apps outputs into Pi-supported TUI components. For rich images/charts in Kitty, the first-class Pi TUI path is the documented `Image` component from `@mariozechner/pi-tui`, not backend-emitted raw terminal escape sequences.

## Source facts used by this research

### Pi facts

From Pi extension/TUI docs:

- Pi extensions are **TypeScript modules**.
- Project-local extensions are auto-discovered from `.pi/extensions/*.ts` or `.pi/extensions/*/index.ts`.
- Extensions can register tools with `pi.registerTool()`.
- Tools can customize display with `renderCall` and `renderResult`.
- Extensions can register message renderers with `pi.registerMessageRenderer()`.
- Extensions can show custom UI with `ctx.ui.custom()`.
- Extension tools can run commands through `pi.exec()`.
- Pi TUI provides an `Image` component that renders images in supported terminals including Kitty.
- The documented `Image` constructor shape is:

```typescript
const image = new Image(
  base64Data,   // base64-encoded image
  "image/png",  // MIME type
  theme,        // ImageTheme
  { maxWidthCells: 80, maxHeightCells: 24 }
);
```

Relevant Pi APIs for Dex:

- `.pi/extensions/dex-mcp-adapter.ts`
- `pi.registerTool({ ... })`
- custom tool `renderResult(result, options, theme, context)`
- `pi.registerMessageRenderer(customType, renderer)`
- `ctx.ui.custom()` for larger interactive views
- `pi.exec(command, args, options)` for CLI bridges
- `Image` from `@mariozechner/pi-tui` for Kitty-compatible image rendering
- `Text`, `Box`, and `Container` from `@mariozechner/pi-tui` for layout

### FastMCP MCP Apps facts

Source-backed current-release notes:

- GitHub release `PrefectHQ/fastmcp` `v3.2.0: Show Don't Tool`, published `2026-03-30T20:25:20Z`, states: "FastMCP 3.2 is the Apps release" and that tools can return interactive UIs — charts, dashboards, forms, maps — rendered inside the conversation.
- That same `v3.2.0` release identifies `FastMCPApp` as a new provider class for interactive MCP applications, separating model-visible entry points (`@app.ui()`) from UI-callable backend tools (`@app.tool()`), and says FastMCP handles MCP Apps protocol machinery: renderer resources, CSP configuration, and structured content serialization.
- The current FastMCP releases page marks `v3.2.4: Patch Me If You Can` as latest, published around `2026-04-14`, so implementation should pin and verify the exact installed `fastmcp` version before coding.
- FastMCP App Architecture docs state the pipeline exactly: `Python components -> JSON tree -> structuredContent -> Renderer iframe -> Host UI`.
- FastMCP App Architecture docs state that `app=True` expands into `AppConfig`, sets `meta["ui"]`, links the tool to a `resourceUri`, and triggers registration of the shared Prefab renderer resource.
- FastMCP App Architecture docs identify the shared renderer URI as `ui://prefab/renderer.html` with MIME type `text/html;profile=mcp-app`.
- FastMCP App Architecture docs state that the renderer is a sandboxed iframe using `postMessage` and the `@modelcontextprotocol/ext-apps` AppBridge for host communication.
- FastMCP Prefab UI docs state that the simplest use is `@mcp.tool(app=True)` returning `PrefabApp` or Prefab components, with examples using `PrefabApp`, `Column`, `Heading`, `BarChart`, and `ChartSeries`.
- FastMCP Prefab UI docs state that `PrefabAppConfig()` with no arguments is equivalent to `app=True`, auto-sets the renderer URI, and merges renderer CSP with user CSP.
- FastMCP Python SDK docs mark `fastmcp.server.apps` as deprecated in `3.2.0` and say to import from `fastmcp.apps` instead.

Therefore, current documented concepts include:

- `@mcp.tool(app=True)` for app-returning tools.
- `PrefabApp` for declaring a UI in Python.
- Prefab UI components such as `Column`, `Heading`, `BarChart`, `ChartSeries`, tables, forms, and stateful/reactive components.
- `FastMCPApp` for managed UI/backend tool binding.
- `AppConfig` / `PrefabAppConfig` from `fastmcp.apps` for MCP Apps metadata.
- `ui://prefab/renderer.html` as the shared Prefab renderer resource.
- `structuredContent` as the serialized component tree sent to the host.
- MCP Apps host behavior normally expects a sandboxed iframe renderer and a `postMessage` / AppBridge path.
- `fastmcp dev apps` can preview app tools locally without a production host and includes an MCP message inspector in the Apps release line.

Important implication for Pi:

Pi TUI is not a browser iframe host. A Dex/Pi bridge must either:

1. implement enough MCP Apps host behavior in a Pi extension to fetch `ui://` resources and translate/display structured content, or
2. treat FastMCP Apps/Prefab as Dex's canonical structured-output contract while rendering a terminal-native projection of that contract in Pi TUI.

The second option is the pragmatic first milestone; the first option is the long-term target if full MCP Apps fidelity is required.

## Integration paths evaluated

### Option 1 — Project-local Pi extension with MCP client adapter

Status: **Recommended core target**

Architecture:

```text
.pi/extensions/dex-mcp-adapter.ts
  -> starts/connects to Dex FastMCP server
  -> calls MCP tools
  -> receives content + structuredContent + ui metadata
  -> maps structuredContent to Pi TUI components
  -> renders tables/charts/images inside Pi/Kitty
```

Why this is the best strategic target:

- Preserves FastMCP/MCP Apps as the canonical Dex structured-output interface.
- Uses Pi's actual supported extension system.
- Keeps DuckDB and analysis logic in Python.
- Keeps rendering in Pi TUI where it belongs.
- Provides a path to progressively support more MCP Apps features.

Minimum viable adapter responsibilities:

1. Start or connect to the Dex FastMCP server.
2. Call Dex MCP tools from Pi custom tools.
3. Capture MCP tool results:
   - `content` for LLM-readable summaries
   - `structuredContent` for typed data and app JSON
   - `meta["ui"]` / `resourceUri` when present
4. Translate common Dex result shapes into Pi TUI components:
   - tables -> text/table component projection
   - PNG charts -> `Image`
   - cards/summaries -> `Text` / `Box` / `Container`
   - timelines -> `Text` / custom component
5. Store full structured results in tool `details` so rendering and session replay have the data.
6. Avoid storing secrets/credentials in result details.

Example Pi extension rendering pattern using documented APIs:

```typescript
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { Box, Container, Image, Text } from "@mariozechner/pi-tui";

interface DexProfileDetails {
  path: string;
  rowCount: number;
  columnCount: number;
  columns: Array<{ name: string; type: string; nullPercent?: number }>;
  chartPngBase64?: string;
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "dex_profile_dataset",
    label: "Dex Profile Dataset",
    description: "Profile a local dataset with Dex and render structured results in Pi TUI.",
    parameters: Type.Object({
      path: Type.String({ description: "Path to a local CSV, Parquet, JSON, or other supported data file" }),
    }),

    async execute(_toolCallId, params, signal, _onUpdate, _ctx) {
      // MVP bridge: invoke Dex CLI or MCP client adapter and receive JSON.
      // The exact transport is chosen during implementation.
      const result = await pi.exec("uv", ["run", "dex", "profile", params.path, "--json"], { signal });
      if (result.code !== 0) throw new Error(result.stderr || result.stdout || "dex profile failed");

      const details = JSON.parse(result.stdout) as DexProfileDetails;
      return {
        content: [{ type: "text", text: `Profiled ${details.path}: ${details.rowCount} rows, ${details.columnCount} columns` }],
        details,
      };
    },

    renderResult(result, _options, theme) {
      const details = result.details as DexProfileDetails | undefined;
      if (!details) return new Text("No Dex profile details", 0, 0);

      const container = new Container();
      const summary = [
        theme.fg("toolTitle", theme.bold(`Dex profile: ${details.path}`)),
        theme.fg("text", `Rows: ${details.rowCount}`),
        theme.fg("text", `Columns: ${details.columnCount}`),
        "",
        ...details.columns.slice(0, 12).map((column) =>
          theme.fg("muted", `${column.name}: ${column.type}${column.nullPercent === undefined ? "" : ` (${column.nullPercent}% null)`}`),
        ),
      ].join("\n");

      const box = new Box(1, 1, (s: string) => theme.bg("toolSuccessBg", s));
      box.addChild(new Text(summary, 0, 0));
      container.addChild(box);

      if (details.chartPngBase64) {
        container.addChild(new Image(details.chartPngBase64, "image/png", theme, {
          maxWidthCells: 80,
          maxHeightCells: 24,
        }));
      }

      return container;
    },
  });
}
```

Notes:

- The extension is TypeScript in `.pi/extensions/`, not Python under `src/dex/`.
- Rendering uses Pi TUI components, not raw Kitty escape sequences from Python.
- The backend returns base64 PNG data, and Pi TUI's `Image` handles Kitty-compatible rendering.
- The MVP can use a CLI bridge while preserving an MCP-client adapter as the target architecture.

### Option 2 — CLI-to-extension bridge with MCP Apps-compatible JSON

Status: **Recommended MVP fallback / stepping stone**

Architecture:

```text
Pi extension tool
  -> pi.exec("uv", ["run", "dex", ...])
  -> Dex Python CLI invokes DuckDB/FastMCP logic
  -> CLI returns structured JSON + base64 assets
  -> Pi extension renderResult maps JSON to TUI components
```

Pros:

- Fastest path to a useful Pi/Kitty prototype.
- Avoids early MCP protocol complexity.
- Keeps the rendering path aligned with real Pi APIs.
- Lets Dex define a stable structured-result envelope that can later be filled by MCP Apps directly.

Cons:

- Not full MCP Apps host behavior.
- Less interactive than an app iframe/AppBridge model.
- Requires care to avoid divergence between CLI JSON and MCP Apps structured content.

Recommended use:

Use this for the first prototype if MCP client/AppBridge support is too large for the initial milestone. The JSON envelope should mirror FastMCP tool result concepts:

```json
{
  "content": "Human-readable summary for the model",
  "structuredContent": {
    "kind": "dex.dataset_profile",
    "path": "sales.csv",
    "rowCount": 1000,
    "columns": []
  },
  "artifacts": [
    { "kind": "chart", "mediaType": "image/png", "base64": "..." }
  ]
}
```

### Option 3 — Full MCP Apps host adapter in a Pi extension

Status: **Longer-term target**

Architecture:

```text
Pi extension
  -> MCP client
  -> detect tool meta["ui"].resourceUri, e.g. ui://prefab/renderer.html
  -> fetch resource HTML/CSP from FastMCP server
  -> receive structuredContent
  -> either:
      a) translate known Prefab JSON into Pi TUI components, or
      b) embed/render a sandboxed app surface if Pi later supports one
```

This is the most faithful MCP Apps integration, but it is larger than the MVP because MCP Apps are browser/iframe-oriented while Pi TUI is terminal-native. The first usable implementation should translate a constrained subset of Prefab/Dex app structures into Pi TUI components.

Recommended translation subset for Dex:

| MCP Apps / Prefab concept | Pi TUI projection |
| --- | --- |
| Heading/Text/Muted | `Text` |
| Card/CardContent | `Box` + `Container` |
| DataTable | text table or custom component |
| BarChart/LineChart/PieChart | backend-rendered PNG + `Image` |
| Column/Row/Grid | `Container` and wrapped lines |
| Forms/Inputs | defer; use `ctx.ui.custom()` or extension commands later |
| Client-side reactive state | defer or project to static snapshot |

This keeps MCP Apps central while acknowledging that full browser-like interactivity will require more adapter work.

### Option 4 — Custom Pi tools only, no MCP Apps contract

Status: **Not recommended as the strategic target**

This is simpler but loses the portability and structured-output contract that MCP Apps provide. It may be acceptable for narrow local tooling but should not be the core Dex architecture.

## Kitty-compatible chart and graph rendering

Dex should not emit raw Kitty graphics protocol escape sequences from the Python backend as the primary Pi path. Instead:

1. Dex Python generates chart images using a non-interactive backend such as Matplotlib `Agg`.
2. Dex returns base64-encoded PNG data in structured output or artifact references.
3. Pi extension renderers create `Image(base64Data, "image/png", theme, { maxWidthCells, maxHeightCells })`.
4. Pi TUI handles Kitty/iTerm2/Ghostty/WezTerm image rendering.

Recommended first chart stack:

```text
DuckDB query -> Python dataframe/Arrow result -> Matplotlib/Plotnine -> PNG bytes -> base64 -> Pi TUI Image
```

Fallback for non-image terminals:

- text summary
- markdown-like table
- sparklines or ASCII histograms
- saved artifact path under `.dex/artifacts/`

## Concrete example flow

User asks in Pi:

```text
Profile sales_data.csv and show me notable data quality issues.
```

Flow:

1. Pi skill or natural language context guides the model to use Dex tools.
2. Pi extension tool `dex_profile_dataset` is called with `path="sales_data.csv"`.
3. The extension calls either:
   - Dex MCP/FastMCP server through an MCP client adapter, or
   - `uv run dex profile sales_data.csv --json` as an MVP bridge.
4. Dex Python uses DuckDB to read/profile the local file.
5. Dex returns:
   - summary text for the LLM
   - structured profile data
   - chart PNG as base64 or an artifact reference
   - optional Field Notes events/artifact metadata
6. Pi extension stores the full result in tool `details`.
7. `renderResult` displays:
   - summary/card via `Text`/`Box`
   - column overview via text table/custom component
   - chart via `Image`
8. Field Notes later archive:
   - command/session context
   - dataset path/provenance
   - observations
   - artifact path(s)

## Structured terminal output vs saved artifacts

Structured terminal output:

- Rendered in Pi TUI for immediate analysis.
- Stored in tool result `details` for session replay where practical.
- Should be compact enough for terminal display.
- May include downsampled or summarized data.

Saved artifacts:

- Stored under `.dex/artifacts/` or another approved Dex state path.
- Used for large result sets, original chart PNGs, exported CSV/Parquet, and reproducibility.
- Referenced from Field Notes by path/hash/metadata.
- Must not include secrets or credentials.

## Recommended implementation sequence for MCP Apps target

1. Build a project-local Pi extension proof of concept in `.pi/extensions/dex-mcp-adapter.ts`.
2. Implement one custom Pi tool with `renderResult` using `Text`, `Box`, `Container`, and `Image`.
3. Back it with a CLI bridge returning an MCP Apps-compatible JSON envelope.
4. Add a FastMCP server with equivalent tool outputs.
5. Replace the CLI call with an MCP client adapter once transport/state behavior is understood.
6. Translate a constrained subset of FastMCP/Prefab structured content into Pi TUI components.
7. Defer full AppBridge/browser-iframe fidelity unless Pi gains a native surface for it or the extension can safely host one.

## Risks and open questions

- FastMCP MCP Apps/Prefab APIs are active and may change; pin versions once implementation begins.
- Pi TUI has a terminal component model, not a browser iframe model, so full MCP Apps fidelity is non-trivial.
- A constrained Dex-specific projection may be more valuable than a generic MCP Apps renderer.
- Large images/results need size limits, truncation, and artifact fallback.
- The extension must avoid persisting credentials or raw sensitive data in session details.
- The implementation bead should verify the exact installed versions of `fastmcp`, `prefab-ui`, and Pi before coding.

## Conclusion

Dex should continue targeting FastMCP MCP Apps as a core structured-output model, but the Pi integration must be explicit:

- **Pi side:** TypeScript extension in `.pi/extensions/`, custom tools, custom renderers, Pi TUI components.
- **Dex side:** Python DuckDB/FastMCP backend returning structured content and base64/image artifacts.
- **Bridge:** start with CLI-compatible structured JSON if necessary, evolve to an MCP client adapter, and eventually translate MCP Apps/Prefab structured content into terminal-native Pi TUI views.

This path preserves the product goal of rich MCP Apps-style results while respecting Pi's current extension and TUI APIs.
