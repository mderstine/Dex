# Dex Field Notes Design

## Purpose

Field Notes are Dex's durable record of analyst work: activity, observations, decisions, hypotheses, findings, warnings, generated outputs, and provenance. They are product data for Dex analysis sessions, not workflow metadata for Purser or Beads.

Field Notes are append-only by default. Corrections, superseding observations, and retractions are represented as new note events that reference earlier events. Destructive deletion or compaction is reserved for explicit user-requested privacy or maintenance operations.

## Default Storage Model

**Default location:** repo-local `.dex/field_notes.duckdb` in the repository or analysis workspace root.

**Rationale:**

- Field Notes are project/workspace-specific analytical evidence.
- Repo-local storage makes notes easy to inspect, archive, hand off, and reason about with the data artifacts they describe.
- It aligns with the initial Dex storage recommendation: repo-local `.dex/` for Field Notes and analysis artifacts, user-level storage only for non-sensitive preferences and reusable configuration.
- It avoids cross-project leakage that could occur if project notes were stored in a shared user-level database.

**Companion directories:**

```text
.dex/
├── field_notes.duckdb
├── artifacts/
│   └── YYYY-MM-DD/
└── cache/
```

User-level storage such as `~/.local/share/dex/` or `~/.dex/` may hold non-sensitive preferences, chart defaults, reusable connector names, or documentation caches. It must not hold project-specific Field Notes, generated analysis artifacts, sensitive results, or credentials.

## Privacy Boundary

Dex must not store secrets or credentials in Field Notes.

Field Notes may store paths, source identifiers, query text, row counts, schema summaries, aggregate statistics, artifact paths, and rationale. They must not store API keys, passwords, access tokens, credential-bearing connection strings, raw sensitive data dumps, or full result sets by default.

For connector-backed data sources, Field Notes store sanitized source/provenance metadata only, such as a local path, an `s3://bucket/key` URI without credentials, or database/table identifiers without passwords or tokens.

## First-Pass DuckDB Schema

The schema separates the immutable event stream from optional detail tables for artifacts, sources, and links. This keeps the core event log simple while allowing richer queries.

```sql
CREATE SEQUENCE IF NOT EXISTS field_note_event_id_seq START 1;

CREATE TABLE IF NOT EXISTS field_note_events (
    event_id UBIGINT PRIMARY KEY DEFAULT nextval('field_note_event_id_seq'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    session_id VARCHAR,
    author_type VARCHAR NOT NULL CHECK (author_type IN ('human', 'ai', 'system')),
    author_id VARCHAR,
    event_type VARCHAR NOT NULL CHECK (event_type IN (
        'activity',
        'observation',
        'schema_profile',
        'decision',
        'hypothesis',
        'finding',
        'warning',
        'query_reference',
        'artifact_reference',
        'correction',
        'supersession',
        'retraction',
        'human_note',
        'ai_note'
    )),
    title VARCHAR,
    body TEXT NOT NULL,
    dataset_ref VARCHAR,
    query_ref VARCHAR,
    artifact_ref VARCHAR,
    parent_event_id UBIGINT,
    supersedes_event_id UBIGINT,
    severity VARCHAR CHECK (severity IS NULL OR severity IN ('info', 'warning', 'error')),
    metadata JSON,
    FOREIGN KEY (parent_event_id) REFERENCES field_note_events(event_id),
    FOREIGN KEY (supersedes_event_id) REFERENCES field_note_events(event_id)
);

CREATE TABLE IF NOT EXISTS field_note_sources (
    source_id VARCHAR PRIMARY KEY,
    source_type VARCHAR NOT NULL,
    sanitized_uri VARCHAR NOT NULL,
    display_name VARCHAR,
    content_fingerprint VARCHAR,
    schema_summary JSON,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS field_note_artifacts (
    artifact_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    artifact_type VARCHAR NOT NULL,
    relative_path VARCHAR NOT NULL,
    description TEXT,
    content_fingerprint VARCHAR,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS field_note_event_sources (
    event_id UBIGINT NOT NULL,
    source_id VARCHAR NOT NULL,
    relationship VARCHAR NOT NULL DEFAULT 'references',
    PRIMARY KEY (event_id, source_id, relationship),
    FOREIGN KEY (event_id) REFERENCES field_note_events(event_id),
    FOREIGN KEY (source_id) REFERENCES field_note_sources(source_id)
);

CREATE TABLE IF NOT EXISTS field_note_event_artifacts (
    event_id UBIGINT NOT NULL,
    artifact_id VARCHAR NOT NULL,
    relationship VARCHAR NOT NULL DEFAULT 'produced',
    PRIMARY KEY (event_id, artifact_id, relationship),
    FOREIGN KEY (event_id) REFERENCES field_note_events(event_id),
    FOREIGN KEY (artifact_id) REFERENCES field_note_artifacts(artifact_id)
);

CREATE INDEX IF NOT EXISTS field_note_events_created_at_idx
    ON field_note_events(created_at DESC);
CREATE INDEX IF NOT EXISTS field_note_events_session_idx
    ON field_note_events(session_id);
CREATE INDEX IF NOT EXISTS field_note_events_author_type_idx
    ON field_note_events(author_type);
CREATE INDEX IF NOT EXISTS field_note_events_event_type_idx
    ON field_note_events(event_type);
CREATE INDEX IF NOT EXISTS field_note_events_dataset_ref_idx
    ON field_note_events(dataset_ref);
```

### Event Type Coverage

| Required Field Notes content | Schema representation |
| --- | --- |
| Chronological activity logs | `field_note_events.created_at`, `event_type = 'activity'` |
| Dataset observations | `event_type = 'observation'`, `dataset_ref`, `field_note_event_sources` |
| Schema/profile summaries | `event_type = 'schema_profile'`, `field_note_sources.schema_summary`, `metadata` |
| Analysis decisions and rationale | `event_type = 'decision'`, `body`, `metadata` |
| Hypotheses | `event_type = 'hypothesis'` |
| Findings | `event_type = 'finding'` |
| Warnings | `event_type = 'warning'`, `severity = 'warning'` |
| Generated query references | `event_type = 'query_reference'`, `query_ref`, `metadata.sql_hash` |
| Source/provenance metadata | `field_note_sources`, `field_note_event_sources` |
| Links/paths to saved artifacts | `field_note_artifacts.relative_path`, `field_note_event_artifacts` |
| Human-authored notes | `author_type = 'human'` and/or `event_type = 'human_note'` |
| AI-authored notes | `author_type = 'ai'` and/or `event_type = 'ai_note'` |

## Append Flow During Analysis Sessions

Dex appends Field Notes at explicit workflow boundaries:

1. **Session start:** append an `activity` event with the session id, workspace root, Dex version, and requested task summary.
2. **Source discovery:** upsert sanitized records in `field_note_sources`, then append observations or schema/profile summaries linked to those sources.
3. **Query execution:** append a `query_reference` event with query text or a query hash, execution metadata, row-count summary, and sanitized dataset references. Large/full results are saved only as reviewed artifacts, not embedded in the event body.
4. **Analysis reasoning:** append `decision`, `hypothesis`, `finding`, and `warning` events as Dex or the user makes choices and records conclusions.
5. **Artifact generation:** write artifacts under `.dex/artifacts/YYYY-MM-DD/`, upsert `field_note_artifacts`, then append an `artifact_reference` event linked to the artifact.
6. **Human notes:** user-authored notes append as `author_type = 'human'`; AI-generated notes append as `author_type = 'ai'`. The author distinction is mandatory.
7. **Corrections:** append a `correction`, `supersession`, or `retraction` event with `supersedes_event_id` pointing at the earlier event. The earlier event remains intact.

Source and artifact tables may be upserted because they are indexes/catalogs for immutable events. The event stream itself is append-only by default.

## Querying and Summarizing Field Notes

Users and Dex can query Field Notes directly with DuckDB or through future Dex CLI helpers.

Example chronological timeline:

```sql
SELECT created_at, author_type, event_type, title, body
FROM field_note_events
ORDER BY created_at;
```

Example findings for a dataset:

```sql
SELECT created_at, title, body, artifact_ref
FROM field_note_events
WHERE dataset_ref = 'data/sales.csv'
  AND event_type IN ('finding', 'warning', 'decision')
ORDER BY created_at DESC;
```

Example AI-authored notes needing review:

```sql
SELECT event_id, created_at, event_type, title, body
FROM field_note_events
WHERE author_type = 'ai'
ORDER BY created_at DESC;
```

Example superseded notes:

```sql
SELECT old.event_id AS superseded_event_id,
       new.event_id AS replacement_event_id,
       new.created_at AS replaced_at,
       new.body AS replacement_reason
FROM field_note_events AS new
JOIN field_note_events AS old
  ON new.supersedes_event_id = old.event_id
WHERE new.event_type IN ('correction', 'supersession', 'retraction');
```

Summaries can be generated by grouping events by session, dataset, source, event type, or artifact. For user-facing summaries, Dex should include provenance and clearly label AI-authored conclusions.

## Export and Archive Behavior

Field Notes are designed to be easy to back up and review while preserving privacy boundaries.

**Archive the full project Dex state:**

```bash
tar -czf dex-archive-$(date +%Y%m%d).tar.gz .dex/
```

**Copy only the Field Notes database:**

```bash
cp .dex/field_notes.duckdb field_notes-backup-$(date +%Y%m%d).duckdb
```

**Export a reviewable timeline:**

```sql
COPY (
    SELECT created_at, author_type, event_type, title, body, dataset_ref, artifact_ref
    FROM field_note_events
    ORDER BY created_at
) TO 'field-notes-timeline.csv' (HEADER, DELIMITER ',');
```

Before sharing exports or archives, users should review Field Notes and artifacts for sensitive project names, dataset paths, schema details, PII in generated artifacts, and any accidentally captured secrets. Credentials are prohibited by design, but review remains necessary because analysis artifacts may contain sensitive results.

## Distinction from Purser and Beads

Field Notes are Dex product data for data analysis work. They record what happened during analysis sessions, what was observed, what decisions were made, which queries and artifacts were produced, and what conclusions were reached.

Purser and Beads are development workflow systems for planning, executing, and reviewing Dex repository work. They track issues, implementation tasks, dependencies, and review status. Dex Field Notes must not replace or bypass Purser/Beads for Dex product development, and Purser/Beads metadata should not be copied into Field Notes except as ordinary provenance if a Dex analysis explicitly studies project workflow data.

## Implementation Notes for the Prototype

The first implementation bead should provide a small API that:

- Opens `.dex/field_notes.duckdb`, creating parent directories and schema on first use.
- Appends events through typed helper methods rather than ad hoc SQL.
- Requires `author_type` and `event_type` for every event.
- Sanitizes source URIs before persistence.
- Stores generated artifact references as relative paths under `.dex/artifacts/`.
- Provides read helpers for timeline, dataset summaries, and export.
- Represents corrections and retractions as new events.
- Does not persist secrets or credentials.
