from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def generate_events(rows: int, output: str, seed: int = 42, include_edge_cases: bool = True):
    if rows < 1:
        raise ValueError("rows must be >= 1")
    rng = np.random.default_rng(seed)
    users = [f"user_{i:05d}" for i in range(max(10, rows // 20))]
    base = pd.Timestamp("2026-01-01T00:00:00Z")
    user_ids = rng.choice(users, size=rows)
    offsets = rng.integers(0, 7 * 24 * 60, size=rows)
    df = pd.DataFrame({
        "event_id": [f"evt_{i:08d}" for i in range(rows)],
        "user_id": user_ids,
        "event_timestamp": [(base + pd.Timedelta(minutes=int(x))).isoformat() for x in offsets],
        "event_type": rng.choice(["page_view", "click", "add_to_cart", "purchase"], size=rows),
    })
    # Intentionally introduce reproducible data-quality cases.
    if include_edge_cases and rows >= 20:
        df.loc[0, "event_timestamp"] = ""
        df.loc[1, "user_id"] = ""
        df.loc[2, "event_timestamp"] = "not-a-timestamp"
        df.loc[3, "event_id"] = df.loc[4, "event_id"]  # duplicate key
        df = pd.concat([df, df.iloc[[5]]], ignore_index=True)  # duplicate event
        # Make a small group with deliberately out-of-order timestamps.
        df.loc[6:8, "user_id"] = "edge_user"
        df.loc[6, "event_timestamp"] = "2026-01-01T10:20:00Z"
        df.loc[7, "event_timestamp"] = "2026-01-01T10:00:00Z"
        df.loc[8, "event_timestamp"] = "2026-01-01T10:10:00Z"
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return len(df)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=100000)
    p.add_argument("--output", default="data/input/generated_events.csv")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--clean", action="store_true", help="Do not inject invalid edge cases")
    a = p.parse_args()
    count = generate_events(a.rows, a.output, a.seed, not a.clean)
    print(f"Wrote {count:,} rows to {a.output}")

if __name__ == "__main__":
    main()
