# Design and trade-off note

## Key decisions
1. **Pandas + SQLite:** minimal local dependencies and easy reproducibility for a 0–3 year data engineering assignment.
2. **Event time, not arrival order:** sort by user and parsed timestamp before calculating gaps. This handles out-of-order events within the supplied batch.
3. **Strictly greater-than boundary:** a gap equal to the inactivity threshold stays in the current session; a gap above it starts a new one.
4. **Quarantine rather than silent drops:** invalid records remain available with a reason and run-specific filename.
5. **Stable IDs:** session identifiers derive from stable event/user/time fields, not random UUIDs.
6. **Snapshot publishing:** replacing outputs makes reruns idempotent for a full-batch input. It is intentionally simpler than incremental merge logic.

## Limitations
A batch cannot know whether a future late event will bridge two sessions unless the affected history is reprocessed. A streaming implementation would need a lateness policy/watermark, state store, and a rule for revising previously published sessions.

## Improvement path
For larger data, partition by user (ensuring a user is never split across partitions), vectorize aggregation, and benchmark memory/time. For incremental production loads, persist event-level deduplication keys and recompute only impacted users' sessions.
