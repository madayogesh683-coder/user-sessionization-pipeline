from __future__ import annotations
import argparse
import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from src.validation import validate_events
from src.sessionization import build_sessions

LOG = logging.getLogger("sessionization")

def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def run_pipeline(input_path: str, output_dir: str = "data/output",
                 gap_minutes: int = 30, db_path: str = "data/output/sessions.db") -> dict:
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rejects_dir = Path("data/rejects")
    rejects_dir.mkdir(parents=True, exist_ok=True)
    status, failure_reason = "success", None
    input_count = valid_count = reject_count = session_count = 0

    try:
        raw = pd.read_csv(input_path, dtype={"event_id": "string", "user_id": "string"})
        input_count = len(raw)
        valid, rejects = validate_events(raw)
        sessions, event_sessions = build_sessions(valid, gap_minutes=gap_minutes)
        valid_count, reject_count, session_count = len(valid), len(rejects), len(sessions)

        # Publish deterministic CSV outputs. Re-running the same source replaces these
        # snapshots rather than appending duplicate rows.
        _write_csv(sessions, out / "sessions.csv")
        _write_csv(event_sessions, out / "event_sessions.csv")
        _write_csv(rejects, rejects_dir / f"rejects_{run_id}.csv")

        # SQLite tables are snapshot tables, replaced transactionally on each successful run.
        db = Path(db_path)
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db) as conn:
            conn.execute("BEGIN")
            sessions.to_sql("sessions", conn, if_exists="replace", index=False)
            event_sessions.to_sql("event_sessions", conn, if_exists="replace", index=False)
            conn.commit()
    except Exception as exc:
        status, failure_reason = "failed", str(exc)
        LOG.exception("Pipeline failed run_id=%s", run_id)
        raise
    finally:
        ended = datetime.now(timezone.utc).isoformat()
        metrics = {
            "run_id": run_id, "status": status, "started_at": started, "ended_at": ended,
            "duration_seconds": round(time.perf_counter() - t0, 4),
            "input_rows": input_count, "valid_rows": valid_count,
            "rejected_rows": reject_count, "output_sessions": session_count,
            "failure_reason": failure_reason, "input_file": str(input_path),
            "session_gap_minutes": gap_minutes,
        }
        with (out / "run_metrics.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(metrics) + "\n")
    LOG.info("Completed run_id=%s status=%s input=%s sessions=%s rejects=%s",
             run_id, status, input_count, session_count, reject_count)
    return metrics

def main():
    parser = argparse.ArgumentParser(description="Clickstream event sessionization pipeline")
    parser.add_argument("--input", default="data/input/sample_events.csv")
    parser.add_argument("--output-dir", default="data/output")
    parser.add_argument("--gap-minutes", type=int, default=30)
    parser.add_argument("--db", default="data/output/sessions.db")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    metrics = run_pipeline(args.input, args.output_dir, args.gap_minutes, args.db)
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()
