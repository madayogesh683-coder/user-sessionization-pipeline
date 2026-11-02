import pandas as pd
from src.pipeline import run_pipeline

def test_pipeline_rerun_replaces_snapshot(tmp_path):
    input_file = tmp_path / "input.csv"
    pd.DataFrame([
        {"event_id":"e1","user_id":"u1","event_timestamp":"2026-01-01T10:00:00Z","event_type":"view"},
        {"event_id":"e2","user_id":"u1","event_timestamp":"2026-01-01T10:05:00Z","event_type":"click"},
    ]).to_csv(input_file, index=False)
    out = tmp_path / "output"
    db = tmp_path / "db.sqlite"
    first = run_pipeline(str(input_file), str(out), 30, str(db))
    second = run_pipeline(str(input_file), str(out), 30, str(db))
    result = pd.read_csv(out / "sessions.csv")
    assert first["output_sessions"] == second["output_sessions"] == 1
    assert len(result) == 1
