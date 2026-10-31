# Input contract

Both files must be UTF-8 CSV with unique header names. Extra named columns are ignored. Missing required columns, duplicate headers and malformed record lengths fail the batch.

## customers.csv

| Field | Rule |
|---|---|
| customer_id | Unique, nonblank identifier |
| region | Nonblank string |

An invalid customer dimension fails the entire run, because orders rely on its keys.

## orders.csv

| Field | Rule |
|---|---|
| order_id | Nonblank unique identifier; every occurrence of a duplicate ID is quarantined |
| customer_id | Must exist in customers.csv |
| order_date | ISO date, strictly before the as-of cutoff |
| amount_eur | Finite, nonnegative decimal, max two places, no more than €1 billion |
| refund_eur | Same money rule; cannot exceed amount_eur |
| status | completed or cancelled |

A valid order may be cancelled or fully refunded. Such rows enter SQLite but not the sales report. One row represents one order, not an order line. Rehires and employee records are unrelated to this project.

Validation records the first applicable rejection reason per row, in this order: blank ID, duplicate ID, unknown customer, date, status, money, refund range. Source line numbers include the header as line 1. No deduplication guess or silent correction is performed.

## Reconciliation and rates

Source rows = accepted rows + rejected rows. Accepted rows = eligible completed positive-net orders + cancelled/zero-net rows. Every monthly SQL count, gross amount, refund amount and net amount must match independent Python totals. Month is the original order's calendar month.

Rejection rate = rejected source rows / all source rows. Duplicate occurrences are counted separately in that denominator. The configured threshold applies to that rate; it is not a statistical confidence measure.

## Safety of exported identifiers

The supplied identifiers are safe fictional strings. With your own data, import IDs as text in spreadsheet applications and review formula-leading values before opening CSV files. Reports are machine-readable and preserve source identifiers in the exception ledger.
