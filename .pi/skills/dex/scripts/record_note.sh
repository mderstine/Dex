#!/usr/bin/env bash
# Record a Field Note
# Usage: record_note.sh --type <event_type> --body <note-body> [--author human|ai|system] [--dataset <path>]

set -e

EVENT_TYPE=""
BODY=""
AUTHOR="ai"
DATASET=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            EVENT_TYPE="$2"
            shift 2
            ;;
        --body)
            BODY="$2"
            shift 2
            ;;
        --author)
            AUTHOR="$2"
            shift 2
            ;;
        --dataset)
            DATASET="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$EVENT_TYPE" || -z "$BODY" ]]; then
    echo "Usage: record_note.sh --type <event_type> --body <note-body> [--author human|ai|system] [--dataset <path>]" >&2
    exit 1
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
uv run python -c "
from dex.field_notes import FieldNotesStore
import sys

with FieldNotesStore.open() as store:
    event_id = store.append_event(
        event_type='$EVENT_TYPE',
        body='$BODY',
        author_type='$AUTHOR',
        dataset_ref='$DATASET' if '$DATASET' else None
    )
    print(f'Field Note recorded: event_id={event_id}')
"
