import pandas as pd
from src.sessionization import build_sessions

def make(rows):
    return pd.DataFrame(rows, columns=["event_id", "user_id", "event_timestamp", "event_type"]).assign(
        event_timestamp=lambda x: pd.to_datetime(x.event_timestamp, utc=True)
    )

def test_happy_path_and_boundary():
    df = make([
        ("e1", "u1", "2026-01-01T10:00:00Z", "view"),
        ("e2", "u1", "2026-01-01T10:30:00Z", "click"),
        ("e3", "u1", "2026-01-01T11:00:01Z", "view"),
    ])
    sessions, _ = build_sessions(df, 30)
    assert sessions.event_count.tolist() == [2, 1]  # exactly 30m stays in same session

def test_out_of_order_events_are_sorted():
    df = make([
        ("e2", "u1", "2026-01-01T10:10:00Z", "click"),
        ("e1", "u1", "2026-01-01T10:00:00Z", "view"),
    ])
    sessions, events = build_sessions(df)
    assert len(sessions) == 1
    assert events.event_id.tolist() == ["e1", "e2"]

def test_empty_input():
    cols = ["event_id", "user_id", "event_timestamp", "event_type"]
    sessions, events = build_sessions(pd.DataFrame(columns=cols))
    assert sessions.empty and events.empty

def test_separate_users_never_share_session():
    df = make([
        ("e1", "u1", "2026-01-01T10:00:00Z", "view"),
        ("e2", "u2", "2026-01-01T10:01:00Z", "view"),
    ])
    sessions, _ = build_sessions(df)
    assert len(sessions) == 2

def test_deterministic_session_ids():
    df = make([("e1", "u1", "2026-01-01T10:00:00Z", "view")])
    a, _ = build_sessions(df)
    b, _ = build_sessions(df)
    assert a.session_id.iloc[0] == b.session_id.iloc[0]
