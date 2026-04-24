# Dex Validation Audit

This document audits the current repository baseline and recommends a validation path for the Dex Python + uv milestone.

## Current Repository State

### Files and Directories

| Item | Exists | Notes |
|------|--------|-------|
| `pyproject.toml` | ✅ Yes | Minimal scaffold; no dependencies declared; no dev dependencies for validation tools |
| `src/dex/` | ❌ No | Package directory does not exist yet |
| `tests/` | ❌ No | Test directory does not exist yet |
| `.purser.toml` | ✅ Yes | Gates section present but no real validation commands configured |

### Validation Tooling Status

| Tool | Available via `uv run` | Configured in `pyproject.toml` | Configured in `.purser.toml` gates |
|------|------------------------|--------------------------------|------------------------------------|
| ruff (lint/format) | ❌ No | ❌ No | ❌ No |
| ty (type check) | ❌ No | ❌ No | ❌ No |
| pytest | ❌ No | ❌ No | ❌ No |

## Recommendation: Defer Automated Validation Tooling

**Decision:** Defer adding automated validation tooling to this bead.

**Rationale:**

1. This bead (dex-7ue) is an **audit/research bead**, not an implementation bead. The acceptance criteria explicitly state: "Do not implement source-code changes in this bead."

2. The Dex project is at the **research spike phase**. The spec's first milestone is a research spike to determine architecture, integration models, and tooling choices. Adding validation infrastructure now would be premature before the product architecture is settled.

3. The spec's "Validation expectations" section already identifies the recommended validation direction. Implementation beads can add these tools when the package structure is created.

4. Keeping validation deferred allows the initial implementation beads to focus on:
   - Architecture documentation
   - Package scaffold creation
   - Research deliverables

## Manual Validation Commands for Implementation Beads

Until automated validation tooling is added, subsequent implementation beads should use these **honest manual validation commands**:

### 1. Package Import Smoke Test

```bash
cd /home/md/src/repos/dex
uv run python -c "import dex; print('dex package imports successfully')"
```

### 2. Manual Code Quality Review

- Visually inspect new Python files for:
  - Consistent indentation (4 spaces)
  - No trailing whitespace
  - Reasonable line lengths (<100 chars preferred)
  - Clear function/method names
  - Docstrings on public APIs

### 3. Manual Type Safety Review

- Ensure type hints are present on:
  - Function parameters
  - Return types
  - Class attributes
- Verify no obvious type mismatches in logic

### 4. Manual Functional Testing

- Run any example scripts in `examples/` directory
- Verify expected outputs match actual outputs
- Document any manual test steps in the bead description

## Future: Candidate Validation Commands (When Tooling is Added)

When a subsequent bead adds validation tooling to `pyproject.toml`, these are the exact commands to configure:

### Lint and Format Check
```bash
uv run ruff check . && uv run ruff format --check .
```

### Type Check
```bash
uv run ty check
```

### Test Suite
```bash
uv run pytest -x --tb=short
```

### `.purser.toml` Gates Update (Future)

When validation tools are added, `.purser.toml` gates should be updated to:

```toml
[gates]
lint = "uv run ruff check . && uv run ruff format --check ."
typecheck = "uv run ty check"
test = "uv run pytest -x --tb=short"
timeout_seconds = 600
```

## Summary

- **Current state:** Minimal scaffold with no validation tooling
- **Recommendation:** Defer automated validation until package structure and architecture are established
- **Manual validation:** Use import smoke tests and code review for early implementation beads
- **Future path:** Add ruff, ty, and pytest when the Dex package structure is created in a subsequent bead
