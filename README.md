# User Sessionization Pipeline

A reproducible Python data-engineering project that converts raw clickstream events into user sessions using event-time inactivity gaps. It includes validation, quarantine, deterministic session IDs, SQLite publishing, operational metrics, synthetic data generation, and automated tests.

## 1. Business rule and assumptions

- One input row represents one source event.
- `event_id` is the globally unique, stable event key. The first occurrence is retained; later occurrences are quarantined as duplicates.
- `user_id`, `event_id`, `event_timestamp`, and `event_type` are required.
- Timestamps are parsed as UTC. Invalid or missing timestamps are quarantined.
- Events are sorted by `user_id`, event timestamp, and event ID before sessionization. Thus out-of-order arrival is supported for a complete input batch.
- A new session starts when the gap from the previous event for that user is **strictly greater than** the configured threshold. A gap exactly equal to 30 minutes remains in the same session.
- Session IDs are deterministic hashes of user ID, first event ID, and session start.
- The pipeline publishes a full snapshot for each successful run. Re-running the same input replaces the output tables/files rather than appending duplicate sessions.
- This batch design assumes the input file contains the complete event history being sessionized. Streaming watermarks and cross-batch late-event updates are outside this starter scope.

## 2. Architecture

```text
CSV source
   |
   v
Ingestion (Pandas)
   |
   v
Schema + timestamp + required-field validation
   |                         |
   v                         v
Valid events              Reject quarantine CSV
   |
   v
Sort by user + event time; remove duplicate event IDs
   |
   v
Sessionize using configurable inactivity gap
   |
   +------> sessions.csv
   +------> event_sessions.csv
   +------> SQLite snapshot tables
   +------> run_metrics.jsonl
```

## 3. Data dictionary

### Source: `events`

| Column | Type | Nullable | Rule |
|---|---|---:|---|
| event_id | string | No | Stable globally unique event key |
| user_id | string | No | User/business key |
| event_timestamp | ISO-8601 timestamp | No | Parsed and normalized to UTC |
| event_type | string | No | Event category, e.g. page_view |

### Target: `sessions`

| Column | Type | Nullable | Meaning |
|---|---|---:|---|
| user_id | string | No | User key |
| session_id | string | No | Deterministic 20-character SHA-256 prefix |
| session_start | UTC timestamp | No | First event time |
| session_end | UTC timestamp | No | Last event time |
| event_count | integer | No | Events in session |
| event_types | string | No | Sorted distinct event types |
| first_event_id | string | No | Stable first event key |

### Target: `event_sessions`

One row per accepted event, mapping its event ID to exactly one session.

### Rejects

Original source columns plus `event_timestamp_parsed` and `reject_reason`. The reason is one of: missing/blank required field, missing/invalid timestamp, or duplicate event ID. Files are named with the pipeline run ID.

## 4. Setup

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 5. Run the sample

From the project root:

```bash
python -m src.pipeline --input data/input/sample_events.csv --gap-minutes 30
```

Outputs (created when you run the pipeline; generated files are intentionally git-ignored):
- `data/output/sessions.csv`
- `data/output/event_sessions.csv`
- `data/output/sessions.db` (SQLite tables: `sessions`, `event_sessions`)
- `data/output/run_metrics.jsonl`
- `data/rejects/rejects_<run_id>.csv`

To change the inactivity threshold:

```bash
python -m src.pipeline --input data/input/sample_events.csv --gap-minutes 20
```

## 6. Generate larger reproducible data

Generate 100,000+ rows using a fixed seed:

```bash
python -m src.generate_data --rows 100000 --seed 42 --output data/input/generated_events.csv
python -m src.pipeline --input data/input/generated_events.csv --gap-minutes 30
```

The generator injects a few intentionally invalid records, a duplicate, and an out-of-order user sequence. Use `--clean` to generate only valid events.

## 7. Tests

```bash
pytest -q
```

Coverage includes:
- Normal session grouping and exact-threshold boundary
- Out-of-order event arrival
- Empty input
- User isolation
- Deterministic session IDs
- Missing timestamps and duplicate event IDs
- Missing required schema columns
- Missing user IDs
- Pipeline rerun / snapshot idempotency

## 8. Reconciliation checks

After a run, use Python or SQLite to check:

```sql
-- Accepted event count should equal event-session mapping count.
SELECT COUNT(*) FROM event_sessions;

-- No event should map to more than one session.
SELECT event_id, COUNT(*)
FROM event_sessions
GROUP BY event_id
HAVING COUNT(*) > 1;

-- Session event counts should reconcile to mapped events.
SELECT SUM(event_count) FROM sessions;
```

The first and third counts should match. The duplicate query should return zero rows. Input rows reconcile as:

`input_rows = valid_rows + rejected_rows`

For the supplied sample, the expected counts are 13 input rows, 9 accepted rows, 4 rejects, and 6 sessions. (The two events exactly 30 minutes apart remain in the same session.)

## 9. Operational behavior and recovery

- Each run receives a UUID `run_id`, timestamps, duration, row counts, status, source path, configured gap, and failure reason.
- Pipeline logs go to standard output/error; run metrics append to `run_metrics.jsonl`.
- A failed run records a failed metrics entry and re-raises the exception.
- Re-run: safe for the same snapshot outputs; output CSVs and SQLite tables are replaced after successful processing.
- Retry: rerun the same command after correcting the underlying issue.
- Backfill: run against a historical source file. Keep each source file separately if auditability is required.
- Reject files are retained per run for traceability.

## 10. Performance and optimization

The generator supports 100,000+ rows. The pipeline uses vectorized Pandas timestamp parsing and sorting; session aggregation currently loops over user-session groups for readable, maintainable code. Measure runtime from `duration_seconds` in `run_metrics.jsonl`. A reasonable next optimization for very large data is to replace the Python group loop with vectorized groupby aggregations and/or process partitioned data by user while preserving complete user history.

## 11. Known limitations / next steps

- Batch processing only; late events arriving in a later batch require reprocessing the affected user's history.
- `event_id` uniqueness is assumed global. If the source only guarantees uniqueness within a producer, use a composite key such as `(source_system, event_id)`.
- CSV schema drift fails fast when required columns are missing; additional unexpected columns are retained in rejects but not used by the transform.
- For production, add structured logging, schema versioning, data retention policy, atomic file replacement, and a run ledger table.

## 12. GitHub submission checklist

Before pushing:
- Confirm `pytest -q` passes.
- Run the sample pipeline and inspect `sessions.csv`, `event_sessions.csv`, and the reject file.
- Run the 100,000-row generator and pipeline; record your machine's runtime from `run_metrics.jsonl`.
- Do not commit `.venv/`, `venv/`, API keys, or large generated datasets.
- Include a few genuine terminal screenshots in a `screenshots/` folder if the evaluator requests execution evidence.
- Review `BENCHMARK_RESULTS.md` and update the runtime if you capture it locally.

Suggested GitHub repository name: `user-sessionization-pipeline`.
