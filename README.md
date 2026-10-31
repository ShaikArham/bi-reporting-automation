# Report Relay · BI Reporting Automation

A reproducible CSV-to-SQLite reporting pipeline with validation, quarantine, SQL aggregation and independent reconciliation. Its static run-review console shows actual generated results and downloadable reports.

**Fictional data only.** Built as a new portfolio implementation in October 2026. This project does not contain Hitachi code, employer data, Oracle connections or retrospective claims of business savings.

[Open the live Report Relay console](https://shaikarham.github.io/bi-reporting-automation/site/)

## Run

Python 3.12 or later, no third-party Python dependencies:

```bash
python scripts/generate_data.py
python scripts/run_pipeline.py --synthetic
python -m unittest discover -s tests -v
python -m http.server 8000 --directory site
```

Open http://localhost:8000 or `site/index.html`. CSV downloads work directly. The run JSON link on the hosted page points to the repository's public outputs folder. When serving only `site/` locally, inspect `outputs/run.json` from disk instead.

## Architecture

1. **Extract**: read customer and order CSVs, check headers and record structure.
2. **Validate**: reject invalid identifiers, dates, money, statuses and refunds. Quarantine all occurrences of duplicate order IDs.
3. **Load**: create a fresh SQLite warehouse with primary/foreign key constraints.
4. **Aggregate**: execute the checked-in `sql/monthly_sales.sql`.
5. **Reconcile**: independently calculate month-level order, gross, refund and net totals in Python, then compare every SQL result row.
6. **Publish**: write report CSV, exception CSV, run JSON and dashboard payload.

The dashboard is a snapshot of a completed run. It does not run Python, simulate execution or show invented processing durations. GitHub Actions runs tests and rebuilds outputs on pushes, pull requests and manual dispatch. No recurring schedule or automated email delivery is configured.

## Sample run

Analysis cutoff: **1 November 2026, exclusive**. Seed 91. Source orders span August–October 2026.

| Control | Fictional result |
|---|---:|
| Customer dimension | 60 customers |
| Source order rows | 405 |
| Accepted rows loaded | 399 |
| Quarantined source rows | 6 |
| Eligible report orders | 300 |
| Accepted but cancelled/zero-net | 99 |
| Net sales | €70,894.13 |
| Rejection rate | 1.48% |
| Maximum rejection rate | 2.00% |
| Run outcome | WARN, quality threshold passed |

The six rejected rows comprise two duplicate occurrences and one each for unknown customer, invalid amount, invalid date and excessive refund. WARN intentionally indicates a usable but qualified run, rather than hiding bad inputs behind a green badge. These statistics describe the dataset, not measured automation savings.

## Quality gate and failure behaviour

```bash
python scripts/run_pipeline.py --synthetic --max-reject-rate 0
```

This command deliberately fails on the supplied sample with exit code 2. Existing reports stay unchanged. Input schema or customer-dimension failures also stop the batch. A rejection rate exactly equal to the threshold is accepted; a rate above it fails. All-rejected inputs fail even with threshold 1.

SQL results must match independently calculated monthly controls. SQLite is built in temporary storage, and failed SQL/reconciliation cannot replace existing output files. The database file is replaced atomically, but CSV/JSON publication is not a single atomic transaction across all artifacts. A filesystem failure during publication may leave a partial bundle. Production use would need versioned run folders and an atomic manifest pointer.

## Custom inputs

Follow [the data contract](docs/data-contract.md):

```bash
python scripts/run_pipeline.py --data /path/to/input --as-of 2026-11-01 --max-reject-rate 0.02
```

Omit `--synthetic` for non-fictional input. Do not publish private source data or identifiers to this public repository. The shipped data and exception IDs are fictional. Input money is EUR with at most two decimals; output money uses integer cents. Fully refunded and cancelled orders can be valid records but are excluded from net sales reporting. Refunds attach to the original order date, so this is not a cash-flow ledger.

## Outputs and repository map

| Path | Purpose |
|---|---|
| `src/pipeline.py` | Validation, loading, reconciliation and artifact generation |
| `scripts/generate_data.py` | Reproducible fictional data with deliberate defects |
| `scripts/run_pipeline.py` | CLI entry point and nonzero failure exit |
| `sql/monthly_sales.sql` | Actual SQL aggregation used by the pipeline |
| `data/` | Fictional customer dimension and order inputs |
| `outputs/monthly_sales.csv` | Audited monthly order/gross/refund/net totals |
| `outputs/exceptions.csv` | Source-line, order-ID and rejection-reason ledger |
| `outputs/run.json` | Control counts, source/SQL SHA-256 hashes and stage results |
| `outputs/warehouse.sqlite` | Locally built warehouse, deliberately excluded from git |
| `site/` | Read-only batch review console and report downloads |
| `tests/` | Money, validation, duplicates, quality gates, reruns and reconciliation tests |

Rebuilding replaces the local warehouse, so repeated runs do not append duplicate orders. JSON and CSV output are deterministic for identical source files, SQL and parameters. The SQLite binary itself is not required to be byte-identical across SQLite versions.

## Interview walkthrough

1. Reconcile 405 = 399 accepted + 6 rejected.
2. Explain why both duplicate occurrences are quarantined instead of choosing an arbitrary first record.
3. Inspect primary/foreign keys and the SQL query.
4. Explain 399 = 300 eligible + 99 cancelled/zero-net.
5. Demonstrate the strict rejection threshold failure and unchanged previous reports.
6. Re-run to demonstrate idempotence, then match CSV totals and source hashes.

This is a portable batch reporting demonstration, not a production orchestration platform. It has no incremental CDC, authentication, alert delivery, secrets manager, concurrent-run protection, transfer-pricing logic or ERP integration. SQL input is trusted project code, not an untrusted query endpoint.
