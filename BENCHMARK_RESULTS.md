# Benchmark and execution evidence

## Local run recorded during development

The 100K generator and pipeline were run locally in VS Code on Windows.

| Metric | Observed result |
|---|---:|
| Generated input rows | 100,001 |
| Accepted rows | 99,996 |
| Rejected rows | 5 |
| Generated sessions | 94,177 |
| Event-to-session mappings | 99,996 |
| Duplicate event mappings | 0 |
| Reconciliation | Passed (`99,996 = 99,996`) |
| Session inactivity threshold | 30 minutes |

The local terminal output confirmed `failure_reason: null`. The exact runtime was not captured in the shared execution screenshot, so it is intentionally not stated here. Run the command below to capture the runtime on your own machine:

```powershell
python -m src.pipeline --input data/input/generated_events.csv
```

The pipeline appends a machine-readable record to `data/output/run_metrics.jsonl`, including `duration_seconds`.

## Reconciliation command

```powershell
python -c "import pandas as pd; e=pd.read_csv('data/output/event_sessions.csv'); s=pd.read_csv('data/output/sessions.csv'); print('Mapped events:',len(e)); print('Session event total:',s['event_count'].sum()); print('Duplicate mappings:',e['event_id'].duplicated().sum()); print('Reconciliation:',len(e)==s['event_count'].sum())"
```

Expected for the generated dataset: 99,996 mapped events, 99,996 total session events, zero duplicate event mappings, and `Reconciliation: True`.

These are local development results, not a claim of a production-scale or cloud benchmark.
