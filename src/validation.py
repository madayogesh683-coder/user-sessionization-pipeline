from __future__ import annotations
import pandas as pd

REQUIRED_COLUMNS = {"event_id", "user_id", "event_timestamp", "event_type"}

def validate_events(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (valid, rejects). Rejects retain original columns plus reject_reason."""
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise ValueError(f"Unexpected schema: missing columns {sorted(missing_columns)}")

    work = df.copy()
    work["event_timestamp_parsed"] = pd.to_datetime(
        work["event_timestamp"], errors="coerce", utc=True
    )
    reasons = pd.Series("", index=work.index, dtype="object")

    for col in ("event_id", "user_id", "event_type"):
        bad = work[col].isna() | work[col].astype(str).str.strip().eq("")
        reasons.loc[bad & reasons.eq("")] = f"missing_or_blank_{col}"

    bad_ts = work["event_timestamp_parsed"].isna()
    reasons.loc[bad_ts & reasons.eq("")] = "missing_or_invalid_event_timestamp"

    # An event ID is the source event's stable key. Keep the first occurrence.
    duplicate = work["event_id"].notna() & work["event_id"].duplicated(keep="first")
    reasons.loc[duplicate & reasons.eq("")] = "duplicate_event_id"

    rejects = work.loc[reasons.ne("")].copy()
    rejects["reject_reason"] = reasons.loc[reasons.ne("")]
    valid = work.loc[reasons.eq("")].copy()
    valid = valid.drop(columns=["event_timestamp"])
    valid = valid.rename(columns={"event_timestamp_parsed": "event_timestamp"})
    return valid, rejects
