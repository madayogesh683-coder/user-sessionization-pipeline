from __future__ import annotations
import hashlib
import pandas as pd

def _stable_session_id(user_id: str, first_event_id: str, session_start: pd.Timestamp) -> str:
    raw = f"{user_id}|{first_event_id}|{session_start.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

def build_sessions(events: pd.DataFrame, gap_minutes: int = 30) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sessionize by user using event-time gaps. A gap strictly greater than threshold starts a session."""
    if gap_minutes < 0:
        raise ValueError("gap_minutes must be >= 0")
    columns = ["user_id", "session_id", "session_start", "session_end",
               "event_count", "event_types", "first_event_id"]
    if events.empty:
        return pd.DataFrame(columns=columns), pd.DataFrame(columns=[
            "event_id", "user_id", "event_timestamp", "event_type", "session_id"
        ])

    ordered = events.sort_values(
        ["user_id", "event_timestamp", "event_id"], kind="mergesort"
    ).copy()
    delta = ordered.groupby("user_id")["event_timestamp"].diff()
    ordered["_new_session"] = delta.isna() | (delta > pd.Timedelta(minutes=gap_minutes))
    ordered["_session_number"] = ordered.groupby("user_id")["_new_session"].cumsum()

    rows = []
    event_rows = []
    for (user_id, number), group in ordered.groupby(["user_id", "_session_number"], sort=True):
        group = group.sort_values(["event_timestamp", "event_id"], kind="mergesort")
        start = group["event_timestamp"].iloc[0]
        end = group["event_timestamp"].iloc[-1]
        first_event_id = str(group["event_id"].iloc[0])
        session_id = _stable_session_id(str(user_id), first_event_id, start)
        rows.append({
            "user_id": user_id,
            "session_id": session_id,
            "session_start": start,
            "session_end": end,
            "event_count": int(len(group)),
            "event_types": ",".join(sorted(set(group["event_type"].astype(str)))),
            "first_event_id": first_event_id,
        })
        for _, event in group.iterrows():
            event_rows.append({
                "event_id": event["event_id"],
                "user_id": user_id,
                "event_timestamp": event["event_timestamp"],
                "event_type": event["event_type"],
                "session_id": session_id,
            })
    return pd.DataFrame(rows, columns=columns), pd.DataFrame(event_rows)
