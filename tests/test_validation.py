import pandas as pd
import pytest
from src.validation import validate_events

def test_rejects_missing_timestamp_and_duplicate():
    df = pd.DataFrame([
        {"event_id":"e1","user_id":"u1","event_timestamp":"2026-01-01T10:00:00Z","event_type":"view"},
        {"event_id":"e2","user_id":"u1","event_timestamp":"","event_type":"click"},
        {"event_id":"e1","user_id":"u2","event_timestamp":"2026-01-01T10:05:00Z","event_type":"view"},
    ])
    valid, rejects = validate_events(df)
    assert len(valid) == 1
    assert len(rejects) == 2
    assert set(rejects.reject_reason) == {
        "missing_or_invalid_event_timestamp", "duplicate_event_id"
    }

def test_missing_required_column_fails_fast():
    with pytest.raises(ValueError, match="Unexpected schema"):
        validate_events(pd.DataFrame({"event_id": ["e1"]}))

def test_missing_user_is_rejected():
    df = pd.DataFrame([{"event_id":"e1","user_id":"","event_timestamp":"2026-01-01T10:00:00Z","event_type":"view"}])
    valid, rejects = validate_events(df)
    assert valid.empty
    assert rejects.reject_reason.iloc[0] == "missing_or_blank_user_id"
