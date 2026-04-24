"""Tests for Dex example analysis flows."""

from pathlib import Path

from examples.titanic_analysis import create_titanic_sample_data, run_analysis


def test_create_titanic_sample_data(tmp_path: Path):
    """Test Titanic sample data creation."""
    csv_path = create_titanic_sample_data(tmp_path)

    assert csv_path.exists()
    assert csv_path.suffix == ".csv"

    content = csv_path.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 21  # Header + 20 data rows
    assert "PassengerId,Survived,Pclass" in lines[0]


def test_run_analysis_creates_field_notes(tmp_path: Path):
    """Test that analysis run creates Field Notes."""
    csv_path = create_titanic_sample_data(tmp_path)

    run_analysis(csv_path, tmp_path)

    # Verify Field Notes database was created
    field_notes_db = tmp_path / ".dex" / "field_notes.duckdb"
    assert field_notes_db.exists()

    # Verify we can query the notes
    from dex.field_notes import FieldNotesStore

    with FieldNotesStore.open(tmp_path) as store:
        timeline = store.get_timeline()
        assert len(timeline) > 0

        # Should have activity events
        activity_events = [e for e in timeline if e.event_type == "activity"]
        assert len(activity_events) >= 2  # Start and end

        # Should have findings
        findings = [e for e in timeline if e.event_type == "finding"]
        assert len(findings) >= 1


def test_run_analysis_creates_artifacts_dir(tmp_path: Path):
    """Test that analysis creates artifacts directory."""
    csv_path = create_titanic_sample_data(tmp_path)

    run_analysis(csv_path, tmp_path)

    artifacts_dir = tmp_path / ".dex" / "artifacts"
    assert artifacts_dir.exists()
