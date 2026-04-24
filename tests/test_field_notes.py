"""Tests for Dex Field Notes prototype."""

from pathlib import Path

from dex.field_notes import (
    FieldNotesStore,
    create_event_id_fingerprint,
    generate_artifact_id,
    generate_source_id,
)
from dex.duckdb_runtime import runtime_paths


def test_field_notes_store_creates_database(tmp_path: Path):
    """Test that FieldNotesStore creates the database file."""
    store = FieldNotesStore.open(tmp_path)

    paths = runtime_paths(tmp_path)
    assert paths.state_dir.exists()
    assert paths.state_dir / "field_notes.duckdb" == store.database_path
    assert store.database_path.exists()

    store.close()


def test_field_notes_append_human_note(tmp_path: Path):
    """Test appending a human-authored note."""
    with FieldNotesStore.open(tmp_path) as store:
        event_id = store.append_event(
            event_type="human_note",
            body="This is a manual observation about the dataset.",
            author_type="human",
            author_id="analyst@example.com",
            title="Manual observation",
            dataset_ref="data/sales.csv",
        )

        event = store.get_event(event_id)
        assert event is not None
        assert event.event_type == "human_note"
        assert event.author_type == "human"
        assert event.body == "This is a manual observation about the dataset."
        assert event.dataset_ref == "data/sales.csv"


def test_field_notes_append_ai_note(tmp_path: Path):
    """Test appending an AI-authored note."""
    with FieldNotesStore.open(tmp_path) as store:
        event_id = store.append_event(
            event_type="ai_note",
            body="Automated finding: column 'amount' has 5% null values.",
            author_type="ai",
            author_id="dex-v0.1.0",
            title="Null value finding",
            dataset_ref="data/sales.csv",
            severity="warning",
        )

        event = store.get_event(event_id)
        assert event is not None
        assert event.event_type == "ai_note"
        assert event.author_type == "ai"
        assert event.severity == "warning"


def test_field_notes_append_finding(tmp_path: Path):
    """Test appending a finding event."""
    with FieldNotesStore.open(tmp_path) as store:
        event_id = store.append_event(
            event_type="finding",
            body="Sales peak in Q4 with 40% of annual revenue.",
            author_type="ai",
            title="Q4 revenue peak",
            dataset_ref="data/sales.csv",
            metadata={"quarter": "Q4", "revenue_share": 0.40},
        )

        event = store.get_event(event_id)
        assert event is not None
        assert event.event_type == "finding"
        assert event.metadata == {"quarter": "Q4", "revenue_share": 0.40}


def test_field_notes_supersession_pattern(tmp_path: Path):
    """Test that corrections are appended as new events, not destructive edits."""
    with FieldNotesStore.open(tmp_path) as store:
        # Original observation
        original_id = store.append_event(
            event_type="observation",
            body="Column 'price' has no null values.",
            author_type="ai",
            dataset_ref="data/products.csv",
        )

        # Correction supersedes the original
        correction_id = store.append_event(
            event_type="correction",
            body="Correction: column 'price' has 2% null values in recent data.",
            author_type="human",
            supersedes_event_id=original_id,
        )

        # Verify both events exist
        original = store.get_event(original_id)
        correction = store.get_event(correction_id)

        assert original is not None
        assert correction is not None
        assert correction.supersedes_event_id == original_id

        # Query superseded events
        superseded_pairs = store.get_superseded_events()
        assert len(superseded_pairs) == 1
        superseded, replacement = superseded_pairs[0]
        assert superseded.event_id == original_id
        assert replacement.event_id == correction_id


def test_field_notes_source_management(tmp_path: Path):
    """Test adding and linking sources."""
    with FieldNotesStore.open(tmp_path) as store:
        # Add a source
        store.add_source(
            source_id="csv_sales_001",
            source_type="csv",
            sanitized_uri="data/sales.csv",
            display_name="Sales Data",
            schema_summary={"columns": ["id", "date", "amount", "region"]},
        )

        # Add an event referencing the source
        event_id = store.append_event(
            event_type="schema_profile",
            body="Profiled sales dataset: 4 columns, 10K rows.",
            author_type="ai",
            dataset_ref="data/sales.csv",
        )

        # Link event to source
        store.link_event_to_source(event_id, "csv_sales_001")

        # Verify source was added (would raise if schema violated)
        # The link table would also be queryable


def test_field_notes_artifact_management(tmp_path: Path):
    """Test adding and linking artifacts."""
    with FieldNotesStore.open(tmp_path) as store:
        # Add an artifact
        store.add_artifact(
            artifact_id="chart_nulls_001",
            artifact_type="chart",
            relative_path=".dex/artifacts/2026-04-24/null-percentages.png",
            description="Bar chart of null percentages by column",
        )

        # Add an event that produced the artifact
        event_id = store.append_event(
            event_type="artifact_reference",
            body="Generated null percentage chart.",
            author_type="ai",
            artifact_ref=".dex/artifacts/2026-04-24/null-percentages.png",
        )

        # Link event to artifact
        store.link_event_to_artifact(event_id, "chart_nulls_001")

        # Verify artifact was added
        # (The artifact table would be queryable)


def test_field_notes_timeline_query(tmp_path: Path):
    """Test querying the event timeline."""
    with FieldNotesStore.open(tmp_path) as store:
        session_id = "test-session-123"

        # Add multiple events
        store.append_event(
            event_type="activity",
            body="Started analysis session.",
            author_type="system",
            session_id=session_id,
        )

        store.append_event(
            event_type="observation",
            body="Dataset has 15 columns.",
            author_type="ai",
            session_id=session_id,
            dataset_ref="data/sales.csv",
        )

        store.append_event(
            event_type="finding",
            body="Q4 shows peak sales.",
            author_type="ai",
            session_id=session_id,
            dataset_ref="data/sales.csv",
        )

        # Query full timeline
        timeline = store.get_timeline(session_id=session_id)
        assert len(timeline) == 3
        assert timeline[0].event_type == "finding"  # Most recent first

        # Query filtered by event type
        findings = store.get_timeline(
            session_id=session_id,
            event_types=["finding", "observation"],
        )
        assert len(findings) == 2

        # Query by author type
        ai_notes = store.get_timeline(session_id=session_id, author_type="ai")
        assert len(ai_notes) == 2


def test_field_notes_dataset_summary(tmp_path: Path):
    """Test getting a dataset summary."""
    with FieldNotesStore.open(tmp_path) as store:
        dataset_ref = "data/sales.csv"

        store.append_event(
            event_type="observation",
            body="15 columns detected.",
            author_type="ai",
            dataset_ref=dataset_ref,
        )

        store.append_event(
            event_type="finding",
            body="Q4 peak sales.",
            author_type="ai",
            dataset_ref=dataset_ref,
        )

        store.append_event(
            event_type="warning",
            body="5% null values in 'amount'.",
            author_type="ai",
            dataset_ref=dataset_ref,
            severity="warning",
        )

        summary = store.get_dataset_summary(dataset_ref)

        assert summary["dataset_ref"] == dataset_ref
        assert summary["total_events"] == 3
        assert len(summary["findings"]) == 2  # observation + finding
        assert len(summary["warnings"]) == 1
        assert len(summary["decisions"]) == 0
        assert summary["ai_authored_count"] == 3


def test_field_notes_export_csv(tmp_path: Path):
    """Test exporting timeline to CSV."""
    with FieldNotesStore.open(tmp_path) as store:
        store.append_event(
            event_type="activity",
            body="Session started.",
            author_type="system",
        )

        store.append_event(
            event_type="finding",
            body="Test finding.",
            author_type="ai",
        )

        output_path = tmp_path / "export" / "timeline.csv"
        rows_exported = store.export_timeline_csv(output_path)

        assert output_path.exists()
        assert rows_exported == 2

        # Verify CSV content
        content = output_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3  # Header + 2 data rows
        assert "created_at,author_type,event_type,title,body" in lines[0]


def test_field_notes_fingerprint_utility():
    """Test the fingerprint utility function."""
    content = "Test content for fingerprinting"
    fingerprint1 = create_event_id_fingerprint(content)
    fingerprint2 = create_event_id_fingerprint(content)
    fingerprint3 = create_event_id_fingerprint("Different content")

    assert fingerprint1 == fingerprint2
    assert fingerprint1 != fingerprint3
    assert len(fingerprint1) == 16  # 16 hex characters


def test_field_notes_artifact_id_generation():
    """Test artifact ID generation."""
    artifact_id1 = generate_artifact_id("chart", "session-123")
    artifact_id2 = generate_artifact_id("chart", "session-123")
    artifact_id3 = generate_artifact_id("chart")  # No session

    assert artifact_id1.startswith("chart_session-123_")
    assert artifact_id2.startswith("chart_session-123_")
    assert artifact_id1 != artifact_id2  # Unique
    assert artifact_id3.startswith("chart_dex_")


def test_field_notes_source_id_generation():
    """Test source ID generation."""
    source_id = generate_source_id("csv", "data/sales.csv")
    assert source_id.startswith("csv_")
    assert len(source_id) > 4  # Has hash component
