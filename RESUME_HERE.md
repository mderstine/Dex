# Resume Here - Dex

_Last updated: 2026-04-24_

## Current status

- GitHub repo: <https://github.com/mderstine/Dex>
- Git remote: `Dex` -> `git@github.com:mderstine/Dex.git`
- Current branch: `main`
- Latest pushed milestone commit: `b48c778 feat: complete initial Dex field companion milestone`
- Beads status at last check: all 18 beads closed; `bd ready` reported no open issues.
- Dex initial field companion milestone is complete as a prototype/v0.1-style milestone.
- Dex v1 is **not** complete yet.

## Important caveat

`purser exec-build-all` completed the queue but exited non-zero with:

```text
reviewer rejected bead dex-3oa but left it closed in Beads
```

The reviewer text itself said the epic was closed successfully, with no issues and all validation gates passing. Treat this as a Purser structured-result/state interpretation inconsistency to investigate before trusting unattended batch execution.

## Validation commands

Run from repo root:

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest -x --tb=short
```

Last known result: all passed, `33 passed`.

## What was completed

Research/docs:

- `docs/architecture.md`
- `docs/tooling-research.md`
- `docs/fastmcp-mcp-apps-research.md`
- `docs/field-notes-design.md`
- `docs/privacy-boundaries.md`

Implementation:

- `src/dex/duckdb_runtime.py` - repo-local DuckDB runtime using `.dex/dex.duckdb`
- `src/dex/field_notes.py` - DuckDB-backed append-only Field Notes prototype
- `src/dex/mcp_app.py` - structured table/chart output and Kitty rendering prototype
- `.pi/skills/dex/` - Pi Skill, helper scripts, and CLI reference docs
- `examples/titanic_analysis.py` - lightweight end-to-end example
- `README.md` - setup, usage, storage, validation, privacy docs
- Tests for runtime, Field Notes, MCP output, examples, and smoke import

## Useful commands after reboot

```bash
cd /home/md/src/repos/dex

git status -sb
git pull --ff-only Dex main
bd ready
uv sync --all-groups
uv run pytest -x --tb=short
```

Manual example run:

```bash
uv run python -m examples.titanic_analysis
```

This may create local `.dex/` runtime state. `.dex/` is intentionally untracked runtime/artifact state unless explicitly needed for docs/examples.

## Recommended next milestone

Suggested next milestone: **Dex v0.2: usable local CLI + Pi Skill validation**

Potential scope:

1. Add a real `dex` console script, e.g. `dex.cli:main`.
2. Implement stable commands:
   - `dex profile <file>`
   - `dex query <sql>`
   - `dex notes timeline`
   - `dex notes export`
3. Update `.pi/skills/dex/scripts/*.sh` to call the stable CLI instead of ad hoc module invocations.
4. Run and refine the workflow inside actual Pi TUI.
5. Add GitHub Actions CI for the same gates in `.purser.toml`.
6. Add release hygiene: `CHANGELOG.md`, version tag, license decision.
7. Harden Field Notes with schema versioning, redaction helpers, JSON/Markdown export, and migration strategy.
8. Decide whether/when to build a real Pi extension/MCP Apps bridge.

## Files/directories to review first

- `README.md`
- `.pi/skills/dex/SKILL.md`
- `src/dex/field_notes.py`
- `src/dex/duckdb_runtime.py`
- `src/dex/mcp_app.py`
- `examples/titanic_analysis.py`
- `tests/`

## Beads/Purser notes

- This repo uses repo-local embedded Beads only.
- Do not switch Beads to shared/server/global mode.
- Dolt remote push is not required unless explicitly configured; git push to `Dex/main` is sufficient for source/docs/code.
- `.beads/` remains local/ignored state.
