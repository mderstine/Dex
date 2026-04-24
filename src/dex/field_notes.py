"""DuckDB-backed Field Notes prototype for Dex.

Field Notes are durable, append-only-by-default records of analyst activity,
observations, decisions, hypotheses, findings, warnings, generated outputs,
and provenance. They are product data for Dex analysis sessions, not workflow
metadata for Purser or Beads.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import duckdb

from .duckdb_runtime import runtime_paths

AuthorType = Literal["human", "ai", "system"]

EventType = Literal[
    "activity",
    "observation",
    "schema_profile",
    "decision",
    "hypothesis",
    "finding",
    "warning",
    "query_reference",
    "artifact_reference",
    "correction",
    "supersession",
    "retraction",
    "human_note",
    "ai_note",
]

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class FieldNoteEvent:
    """A single Field Notes event record."""

    event_id: int
    created_at: datetime
    session_id: str | None
    author_type: AuthorType
    author_id: str | None
    event_type: EventType
    title: str | None
    body: str
    dataset_ref: str | None
    query_ref: str | None
    artifact_ref: str | None
    parent_event_id: int | None
    supersedes_event_id: int | None
    severity: Severity | None
    metadata: dict[str, Any] | None


@dataclass(frozen=True)
class FieldNoteSource:
    """A data source referenced by Field Notes."""

    source_id: str
    source_type: str
    sanitized_uri: str
    display_name: str | None
    content_fingerprint: str | None
    schema_summary: dict[str, Any] | None
    metadata: dict[str, Any] | None


@dataclass(frozen=True)
class FieldNoteArtifact:
    """A generated artifact referenced by Field Notes."""

    artifact_id: str
    created_at: datetime
    artifact_type: str
    relative_path: str
    description: str | None
    content_fingerprint: str | None
    metadata: dict[str, Any] | None


class FieldNotesStore:
    """Append-only Field Notes store backed by DuckDB.

    Default storage: repo-local `.dex/field_notes.duckdb`.

    The store separates the immutable event stream from optional detail
    tables for sources and artifacts. Events are append-only by default;
    corrections and retractions are new events referencing earlier events.
    """

    def __init__(self, workspace: str | Path = ".") -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.paths = runtime_paths(self.workspace)
        self.paths.ensure()
        self.database_path = self.paths.state_dir / "field_notes.duckdb"
        self._connection = duckdb.connect(str(self.database_path))
        self._ensure_schema()

    @classmethod
    def open(cls, workspace: str | Path = ".") -> "FieldNotesStore":
        """Open or create a Field Notes store for a workspace."""
        return cls(workspace)

    def _ensure_schema(self) -> None:
        """Create Field Notes schema if it does not exist."""
        # DuckDB execute() supports multiple statements separated by semicolons
        self._connection.execute(
            """
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
                metadata JSON
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
                PRIMARY KEY (event_id, source_id, relationship)
            );

            CREATE TABLE IF NOT EXISTS field_note_event_artifacts (
                event_id UBIGINT NOT NULL,
                artifact_id VARCHAR NOT NULL,
                relationship VARCHAR NOT NULL DEFAULT 'produced',
                PRIMARY KEY (event_id, artifact_id, relationship)
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
        """
        )

    def append_event(
        self,
        event_type: EventType,
        body: str,
        *,
        author_type: AuthorType,
        session_id: str | None = None,
        author_id: str | None = None,
        title: str | None = None,
        dataset_ref: str | None = None,
        query_ref: str | None = None,
        artifact_ref: str | None = None,
        parent_event_id: int | None = None,
        supersedes_event_id: int | None = None,
        severity: Severity | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Append a new event to the Field Notes store.

        Args:
            event_type: The type of event (e.g., 'observation', 'finding').
            body: The main content of the note (required).
            author_type: Who authored this note ('human', 'ai', or 'system').
            session_id: Optional session identifier.
            author_id: Optional author identifier (e.g., username, model name).
            title: Optional short title.
            dataset_ref: Optional reference to a dataset (e.g., path).
            query_ref: Optional reference to a query (text or hash).
            artifact_ref: Optional reference to a generated artifact (path).
            parent_event_id: Optional reference to a parent event.
            supersedes_event_id: Optional reference to a superseded event.
            severity: Optional severity level for warnings/errors.
            metadata: Optional JSON metadata.

        Returns:
            The event_id of the newly created event.

        Note:
            Corrections, supersessions, and retractions should be appended as
            new events with supersedes_event_id pointing to the earlier event,
            not as destructive edits.
        """
        if not body:
            msg = "body is required for all events"
            raise ValueError(msg)

        metadata_json = json.dumps(metadata) if metadata else None

        result = self._connection.execute(
            """
            INSERT INTO field_note_events (
                session_id, author_type, author_id, event_type, title, body,
                dataset_ref, query_ref, artifact_ref, parent_event_id,
                supersedes_event_id, severity, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING event_id
        """,
            (
                session_id,
                author_type,
                author_id,
                event_type,
                title,
                body,
                dataset_ref,
                query_ref,
                artifact_ref,
                parent_event_id,
                supersedes_event_id,
                severity,
                metadata_json,
            ),
        ).fetchone()

        if result is None:
            msg = "Failed to create event: no event_id returned"
            raise RuntimeError(msg)

        return int(result[0])

    def add_source(
        self,
        source_id: str,
        source_type: str,
        sanitized_uri: str,
        *,
        display_name: str | None = None,
        content_fingerprint: str | None = None,
        schema_summary: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register or update a data source in Field Notes.

        Args:
            source_id: Unique identifier for this source.
            source_type: Type of source (e.g., 'csv', 'parquet', 'postgres').
            sanitized_uri: URI without credentials (e.g., s3://bucket/key).
            display_name: Optional human-readable name.
            content_fingerprint: Optional hash of content for change detection.
            schema_summary: Optional schema metadata.
            metadata: Optional additional metadata.

        Note:
            Sources may be upserted because they are catalogs for immutable
            events. The event stream itself is append-only.
        """
        schema_json = json.dumps(schema_summary) if schema_summary else None
        metadata_json = json.dumps(metadata) if metadata else None

        self._connection.execute(
            """
            INSERT INTO field_note_sources (
                source_id, source_type, sanitized_uri, display_name,
                content_fingerprint, schema_summary, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (source_id) DO UPDATE SET
                source_type = excluded.source_type,
                sanitized_uri = excluded.sanitized_uri,
                display_name = excluded.display_name,
                content_fingerprint = excluded.content_fingerprint,
                schema_summary = excluded.schema_summary,
                metadata = excluded.metadata
        """,
            (
                source_id,
                source_type,
                sanitized_uri,
                display_name,
                content_fingerprint,
                schema_json,
                metadata_json,
            ),
        )

    def add_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        relative_path: str,
        *,
        description: str | None = None,
        content_fingerprint: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register or update a generated artifact in Field Notes.

        Args:
            artifact_id: Unique identifier for this artifact.
            artifact_type: Type of artifact (e.g., 'chart', 'csv_export').
            relative_path: Path relative to workspace (e.g., .dex/artifacts/...).
            description: Optional description.
            content_fingerprint: Optional hash for change detection.
            metadata: Optional additional metadata.

        Note:
            Artifacts may be upserted because they are catalogs for immutable
            events. The event stream itself is append-only.
        """
        metadata_json = json.dumps(metadata) if metadata else None

        self._connection.execute(
            """
            INSERT INTO field_note_artifacts (
                artifact_id, artifact_type, relative_path, description,
                content_fingerprint, metadata
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (artifact_id) DO UPDATE SET
                artifact_type = excluded.artifact_type,
                relative_path = excluded.relative_path,
                description = excluded.description,
                content_fingerprint = excluded.content_fingerprint,
                metadata = excluded.metadata
        """,
            (
                artifact_id,
                artifact_type,
                relative_path,
                description,
                content_fingerprint,
                metadata_json,
            ),
        )

    def link_event_to_source(
        self,
        event_id: int,
        source_id: str,
        relationship: str = "references",
    ) -> None:
        """Link an event to a source."""
        self._connection.execute(
            """
            INSERT INTO field_note_event_sources (event_id, source_id, relationship)
            VALUES (?, ?, ?)
            ON CONFLICT (event_id, source_id, relationship) DO NOTHING
        """,
            (event_id, source_id, relationship),
        )

    def link_event_to_artifact(
        self,
        event_id: int,
        artifact_id: str,
        relationship: str = "produced",
    ) -> None:
        """Link an event to an artifact."""
        self._connection.execute(
            """
            INSERT INTO field_note_event_artifacts (event_id, artifact_id, relationship)
            VALUES (?, ?, ?)
            ON CONFLICT (event_id, artifact_id, relationship) DO NOTHING
        """,
            (event_id, artifact_id, relationship),
        )

    def get_event(self, event_id: int) -> FieldNoteEvent | None:
        """Retrieve a single event by ID."""
        row = self._connection.execute(
            """
            SELECT event_id, created_at, session_id, author_type, author_id,
                   event_type, title, body, dataset_ref, query_ref, artifact_ref,
                   parent_event_id, supersedes_event_id, severity, metadata
            FROM field_note_events
            WHERE event_id = ?
        """,
            (event_id,),
        ).fetchone()

        if row is None:
            return None

        return FieldNoteEvent(
            event_id=int(row[0]),
            created_at=row[1],
            session_id=row[2],
            author_type=row[3],
            author_id=row[4],
            event_type=row[5],
            title=row[6],
            body=row[7],
            dataset_ref=row[8],
            query_ref=row[9],
            artifact_ref=row[10],
            parent_event_id=row[11],
            supersedes_event_id=row[12],
            severity=row[13],
            metadata=json.loads(row[14]) if row[14] else None,
        )

    def get_timeline(
        self,
        *,
        session_id: str | None = None,
        dataset_ref: str | None = None,
        event_types: Sequence[EventType] | None = None,
        author_type: AuthorType | None = None,
        limit: int | None = None,
    ) -> list[FieldNoteEvent]:
        """Query events in chronological order.

        Args:
            session_id: Filter by session.
            dataset_ref: Filter by dataset reference.
            event_types: Filter by event types.
            author_type: Filter by author type.
            limit: Maximum number of events to return.

        Returns:
            List of events ordered by created_at descending.
        """
        where_clauses = []
        params: list[Any] = []

        if session_id is not None:
            where_clauses.append("session_id = ?")
            params.append(session_id)

        if dataset_ref is not None:
            where_clauses.append("dataset_ref = ?")
            params.append(dataset_ref)

        if event_types is not None:
            placeholders = ", ".join("?" for _ in event_types)
            where_clauses.append(f"event_type IN ({placeholders})")
            params.extend(event_types)

        if author_type is not None:
            where_clauses.append("author_type = ?")
            params.append(author_type)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        limit_sql = f"LIMIT {int(limit)}" if limit is not None else ""

        rows = self._connection.execute(
            f"""
            SELECT event_id, created_at, session_id, author_type, author_id,
                   event_type, title, body, dataset_ref, query_ref, artifact_ref,
                   parent_event_id, supersedes_event_id, severity, metadata
            FROM field_note_events
            {where_sql}
            ORDER BY created_at DESC
            {limit_sql}
        """,
            params,
        ).fetchall()

        return [
            FieldNoteEvent(
                event_id=int(row[0]),
                created_at=row[1],
                session_id=row[2],
                author_type=row[3],
                author_id=row[4],
                event_type=row[5],
                title=row[6],
                body=row[7],
                dataset_ref=row[8],
                query_ref=row[9],
                artifact_ref=row[10],
                parent_event_id=row[11],
                supersedes_event_id=row[12],
                severity=row[13],
                metadata=json.loads(row[14]) if row[14] else None,
            )
            for row in rows
        ]

    def get_dataset_summary(self, dataset_ref: str) -> dict[str, Any]:
        """Get a summary of all notes related to a dataset.

        Returns:
            Dictionary with timeline, findings, warnings, and decisions.
        """
        timeline = self.get_timeline(dataset_ref=dataset_ref)

        findings = [
            e
            for e in timeline
            if e.event_type in ("finding", "observation", "schema_profile")
        ]
        warnings = [e for e in timeline if e.event_type == "warning"]
        decisions = [e for e in timeline if e.event_type == "decision"]

        return {
            "dataset_ref": dataset_ref,
            "total_events": len(timeline),
            "findings": findings,
            "warnings": warnings,
            "decisions": decisions,
            "ai_authored_count": sum(1 for e in timeline if e.author_type == "ai"),
            "human_authored_count": sum(
                1 for e in timeline if e.author_type == "human"
            ),
        }

    def get_superseded_events(self) -> list[tuple[FieldNoteEvent, FieldNoteEvent]]:
        """Get all superseded events with their replacement events.

        Returns:
            List of (superseded_event, replacement_event) pairs.
        """
        rows = self._connection.execute("""
            SELECT
                old.event_id, old.created_at, old.session_id, old.author_type,
                old.author_id, old.event_type, old.title, old.body, old.dataset_ref,
                old.query_ref, old.artifact_ref, old.parent_event_id,
                old.supersedes_event_id, old.severity, old.metadata,
                new.event_id, new.created_at, new.body
            FROM field_note_events AS new
            JOIN field_note_events AS old
              ON new.supersedes_event_id = old.event_id
            WHERE new.event_type IN ('correction', 'supersession', 'retraction')
            ORDER BY new.created_at DESC
        """).fetchall()

        pairs = []
        for row in rows:
            superseded = FieldNoteEvent(
                event_id=int(row[0]),
                created_at=row[1],
                session_id=row[2],
                author_type=row[3],
                author_id=row[4],
                event_type=row[5],
                title=row[6],
                body=row[7],
                dataset_ref=row[8],
                query_ref=row[9],
                artifact_ref=row[10],
                parent_event_id=row[11],
                supersedes_event_id=row[12],
                severity=row[13],
                metadata=json.loads(row[14]) if row[14] else None,
            )
            replacement = FieldNoteEvent(
                event_id=int(row[15]),
                created_at=row[16],
                session_id=row[2],
                author_type=row[3],
                author_id=row[4],
                event_type=row[5],
                title=row[6],
                body=row[17],
                dataset_ref=row[8],
                query_ref=row[9],
                artifact_ref=row[10],
                parent_event_id=row[11],
                supersedes_event_id=superseded.event_id,
                severity=row[13],
                metadata=json.loads(row[14]) if row[14] else None,
            )
            pairs.append((superseded, replacement))

        return pairs

    def export_timeline_csv(self, output_path: str | Path) -> int:
        """Export the event timeline to a CSV file.

        Args:
            output_path: Path to write the CSV file.

        Returns:
            Number of rows exported.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        result = self._connection.execute(f"""
            COPY (
                SELECT created_at, author_type, event_type, title, body,
                       dataset_ref, artifact_ref, severity
                FROM field_note_events
                ORDER BY created_at
            ) TO '{output}' (HEADER, DELIMITER ',')
        """)

        # COPY returns row count in result
        row_result = result.fetchone()
        return int(row_result[0]) if row_result else 0

    def close(self) -> None:
        """Close the database connection."""
        self._connection.close()

    def __enter__(self) -> "FieldNotesStore":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def create_event_id_fingerprint(content: str) -> str:
    """Create a short fingerprint for event content.

    Useful for detecting duplicate notes or content changes.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def generate_artifact_id(artifact_type: str, session_id: str | None = None) -> str:
    """Generate a unique artifact ID."""
    prefix = f"{artifact_type}_{session_id or 'dex'}"
    unique = uuid.uuid4().hex[:8]
    return f"{prefix}_{unique}"


def generate_source_id(source_type: str, uri: str) -> str:
    """Generate a unique source ID from type and URI."""
    unique = hashlib.sha256(f"{source_type}:{uri}".encode("utf-8")).hexdigest()[:12]
    return f"{source_type}_{unique}"
