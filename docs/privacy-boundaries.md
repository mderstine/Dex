# Dex Privacy and Export Boundaries

## Overview

This document defines the privacy boundaries for Dex Field Notes, saved artifacts, exports, connector metadata, and credentials. These boundaries ensure users can avoid accidental disclosure of sensitive data.

**This is spillover work discovered from Field Notes and MCP tooling research (bead dex-tbw).**

---

## Core Principle: No Secrets in Field Notes

**Dex must NOT store secrets or credentials in Field Notes.**

This is a binding requirement from the spec non-goals. Dex will:

- **Never persist credentials** in `.dex/field_notes.duckdb`
- **Never include credentials** in Field Notes metadata or artifact paths
- **Never store API keys, passwords, tokens, or connection strings** in Field Notes content
- **Never log sensitive authentication data** even in encrypted or obfuscated form

---

## Storage Boundaries

### Repo-Local `.dex/` (Project-Specific)

**Location:** `.dex/` in the repository or analysis workspace root

**What belongs here:**

| Data Type | Description | Sensitivity |
|-----------|-------------|-------------|
| **Field Notes database** | `.dex/field_notes.duckdb` - append-only activity log | Low (no credentials stored) |
| **Generated artifacts** | `.dex/artifacts/` - charts, exported query results, profiling summaries | Medium (may contain analysis results) |
| **Cached schema profiles** | `.dex/cache/` - reusable metadata for known datasets | Low (schema only, no data) |
| **Analysis traces** | Provenance records, query references, dataset paths | Low (metadata only) |
| **Connection metadata** | **Path/URI only** - e.g., `s3://bucket/data.csv`, `postgres://host/db/table` | Low (no credentials in path) |

**What does NOT belong here:**

- Connector credentials (passwords, API keys, tokens)
- Raw sensitive data from external sources
- User-level preferences or cross-project caches

**Default behavior:**
- Field Notes database is created automatically on first use
- Artifacts are organized by date: `.dex/artifacts/2026-04-24/`
- Cache entries are keyed by dataset path or hash

---

### User-Level Storage (Cross-Project)

**Locations:** `~/.local/share/dex/`, `~/.dex/`, or platform-appropriate user data directory

**What belongs here:**

| Data Type | Description | Sensitivity |
|-----------|-------------|-------------|
| **User preferences** | CLI defaults, chart rendering options, preferred connectors | Low |
| **Reusable connection profiles** | **Non-sensitive configuration only** - hostnames, ports, database names | Low |
| **Global caches** | Cross-project schema caches, documentation indices | Low |
| **Session history** | Optional: command history, frequently-used queries | Low |

**What does NOT belong here:**

- Credentials (use system credential stores instead)
- Project-specific Field Notes or artifacts
- Sensitive analysis results

**Credential management:**
- AWS credentials: `~/.aws/credentials` (standard AWS CLI location)
- Database passwords: Environment variables or system keychain
- API tokens: Environment variables or secret management tools

---

### What Must NEVER Be Persisted

| Data Type | Reason | Alternative |
|-----------|--------|-------------|
| **Secrets** | API keys, passwords, tokens, private keys | Use environment variables or system credential stores |
| **Credentials** | Database connection strings with passwords, AWS access keys | Use DuckDB's native credential chain |
| **Raw PII** | Unmasked personal data from analyzed datasets | Store only aggregate statistics or schema metadata |
| **Full query results** | Large result sets may contain sensitive data | Store query text and summary statistics only |
| **Session state with credentials** | Temporary files or state that includes auth tokens | Use in-memory state only |

---

## Export and Archive Behavior

### Export Guidelines

**Users can export Field Notes and artifacts, but must be aware of risks:**

1. **Field Notes export** (`.dex/field_notes.duckdb`):
   - Safe to export: Contains no credentials by design
   - Risk: May reference dataset paths that reveal project structure
   - Mitigation: Review exported content before sharing

2. **Artifacts export** (`.dex/artifacts/`):
   - Risk: Charts and query results may contain sensitive analysis findings
   - Mitigation: Review artifacts before exporting; consider redaction for sensitive data

3. **Cache export** (`.dex/cache/`):
   - Generally safe: Contains schema metadata only
   - Risk: Schema names may reveal business logic
   - Mitigation: Review before sharing externally

### Archive Recommendations

**For long-term archival:**

1. **Full project archive:**
   ```bash
   tar -czf dex-archive-$(date +%Y%m%d).tar.gz .dex/
   ```
   - Includes Field Notes, artifacts, and cache
   - Suitable for project handoff or backup
   - Review for sensitive data before sharing

2. **Field Notes only:**
   ```bash
   cp .dex/field_notes.duckdb field_notes-backup-$(date +%Y%m%d).duckdb
   ```
   - Preserves activity log without artifacts
   - Lower risk of sensitive data exposure

3. **Selective export:**
   - Export specific artifacts by date or type
   - Exclude cache if not needed
   - Review Field Notes content before sharing

### Avoiding Accidental Disclosure

**Checklist before exporting or sharing `.dex/` contents:**

- [ ] Review Field Notes for any accidentally logged sensitive data
- [ ] Check artifact filenames for sensitive project names or identifiers
- [ ] Verify query results in artifacts do not contain PII or confidential data
- [ ] Remove or redact cache entries if they reveal sensitive schema information
- [ ] Ensure no credential files were accidentally placed in `.dex/`

---

## Boundary Coverage

### Generated Artifacts

**What may be stored:**

- Charts and graphs (PNG, SVG)
- Exported query results (CSV, Parquet)
- Profiling summaries (Markdown, JSON)
- Analysis recommendations

**What must not be stored:**

- Raw data dumps from external sources
- Credentials or authentication tokens
- Full dataset copies (store path/reference only)

**Best practices:**

- Store artifacts in `.dex/artifacts/YYYY-MM-DD/` organized by date
- Use descriptive but non-sensitive filenames
- Reference artifacts in Field Notes by relative path only

---

### Provenance Metadata

**What may be stored:**

- Dataset paths (e.g., `s3://bucket/data.csv`, `/home/user/data/sales.parquet`)
- Query text (SQL statements)
- Timestamps and authorship (human vs. AI)
- Tool versions and configuration

**What must not be stored:**

- Credentials embedded in paths (e.g., `s3://key:secret@bucket/data.csv`)
- Full result sets (store summary statistics only)
- Session tokens or temporary auth credentials

**Best practices:**

- Store URI/path without credentials
- Log query text but not full results
- Include enough metadata for reproducibility without exposing sensitive data

---

### Connector Credentials

**External database connectors require credentials. Dex handles them as follows:**

| Connector Type | Credential Management | Dex Storage |
|----------------|----------------------|-------------|
| **AWS S3** | `~/.aws/credentials` or environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) | **None** - store path only (`s3://bucket/key`) |
| **PostgreSQL** | Environment variables (`PGPASSWORD`, `PGUSER`) or `.pgpass` file | **None** - store connection metadata only (host, port, database, table) |
| **MySQL** | Environment variables or MySQL config file | **None** - store connection metadata only |
| **MotherDuck** | MotherDuck token in environment variable (`MOTHERDUCK_TOKEN`) | **None** - store database reference only |
| **HTTP/HTTPS** | No credentials for public URLs; auth headers for private | **None** - store URL only (no query params with tokens) |

**Dex's stance:**

- Rely on DuckDB's native credential chain (environment variables, system config files)
- Never prompt users to enter credentials interactively
- Never log credential values even in debug mode
- Document that connector credentials must be managed externally

---

### Local Data Access Risks

**Dex runs locally with the user's permissions. Risks to consider:**

1. **File access:**
   - Dex CLI tools can read any file the user can access
   - Risk: Accidental exposure of sensitive files in the workspace
   - Mitigation: Only profile/query files explicitly specified by the user

2. **Database attachments:**
   - DuckDB can attach to any database file the user can read
   - Risk: Attaching to databases containing sensitive data
   - Mitigation: Document attachment behavior; require explicit user confirmation

3. **Network connectors:**
   - DuckDB extensions can connect to external databases
   - Risk: Credentials leaked via logs, Field Notes, or error messages
   - Mitigation: Never log credentials; use external credential management

4. **Exported results:**
   - Query results may contain sensitive data
   - Risk: Accidental sharing of artifacts containing PII or confidential data
   - Mitigation: Review artifacts before sharing; document export risks

---

## Git and Version Control

### `.gitignore` Recommendations

**Add `.dex/` to `.gitignore` if:**

- The repository is public or shared with users who should not see Field Notes
- Field Notes may contain project-sensitive metadata
- Artifacts contain confidential analysis results

**Keep `.dex/` out of `.gitignore` if:**

- The repository is private and Field Notes are valuable for collaboration
- Field Notes serve as an audit trail for analysis work
- Team members benefit from shared artifacts and provenance records

**Current project (dex):** `.dex/` is NOT in `.gitignore` because:
- This is the Dex product repository itself
- Field Notes are part of the product being developed
- Example Field Notes may be useful for documentation

**For user projects using Dex:** Add to `.gitignore`:
```
# Dex Field Notes and artifacts (may contain sensitive analysis data)
.dex/
```

---

## Summary Table

| Storage Location | What Belongs Here | What Does NOT Belong Here |
|------------------|-------------------|---------------------------|
| **`.dex/field_notes.duckdb`** | Activity logs, observations, decisions, query references, dataset paths | Credentials, secrets, raw sensitive data |
| **`.dex/artifacts/`** | Charts, exported results, profiling summaries | Credentials, full dataset copies, PII without review |
| **`.dex/cache/`** | Schema metadata, documentation indices | Raw data, credentials |
| **`~/.local/share/dex/`** | User preferences, non-sensitive connection profiles | Credentials, project-specific Field Notes |
| **External (env vars, system stores)** | AWS credentials, database passwords, API tokens | N/A (this is the correct location) |

---

## Non-Goals (Preserved from Spec)

- Do not build a full production data platform
- Do not implement every DuckDB connector
- Do not create a GUI outside the terminal/Pi TUI experience
- Do not make generated code the primary user-facing artifact
- Do not bypass Purser/Beads for Dex product work
- **Do not store secrets or credentials in Field Notes** (binding requirement)
- Do not configure Beads shared/server/global mode

---

## Related Documents

- `docs/architecture.md` - Dex architecture and storage strategy
- `docs/tooling-research.md` - Tooling research including security considerations
- `specs/dex-data-analysts-field-companion.md` - Original spec with non-goals

---

**Bead:** dex-tbw  
**Status:** Design complete  
**Next steps:** Implementation beads should enforce these boundaries in code
