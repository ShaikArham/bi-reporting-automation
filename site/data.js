window.REPORT_DATA = {
  "accepted_rows": 399,
  "as_of": "2026-11-01",
  "eligible_orders": 300,
  "exceptions": [
    {
      "order_id": "O0002",
      "reason": "DUPLICATE_ORDER_ID",
      "source_line": 3
    },
    {
      "order_id": "BAD-customer_id",
      "reason": "UNKNOWN_CUSTOMER",
      "source_line": 402
    },
    {
      "order_id": "BAD-amount_eur",
      "reason": "INVALID_MONEY",
      "source_line": 403
    },
    {
      "order_id": "BAD-order_date",
      "reason": "INVALID_DATE",
      "source_line": 404
    },
    {
      "order_id": "BAD-refund_eur",
      "reason": "REFUND_EXCEEDS_AMOUNT",
      "source_line": 405
    },
    {
      "order_id": "O0002",
      "reason": "DUPLICATE_ORDER_ID",
      "source_line": 406
    }
  ],
  "excluded_accepted_rows": 99,
  "input_rows": 405,
  "max_reject_rate": 0.02,
  "monthly": [
    {
      "gross_cents": 2380493,
      "month": "2026-08",
      "net_cents": 2173857,
      "orders": 92,
      "refund_cents": 206636
    },
    {
      "gross_cents": 2621507,
      "month": "2026-09",
      "net_cents": 2442326,
      "orders": 104,
      "refund_cents": 179181
    },
    {
      "gross_cents": 2634419,
      "month": "2026-10",
      "net_cents": 2473230,
      "orders": 104,
      "refund_cents": 161189
    }
  ],
  "net_cents": 7089413,
  "project": "Report Relay",
  "reasons": {
    "DUPLICATE_ORDER_ID": 2,
    "INVALID_DATE": 1,
    "INVALID_MONEY": 1,
    "REFUND_EXCEEDS_AMOUNT": 1,
    "UNKNOWN_CUSTOMER": 1
  },
  "rejected_rows": 6,
  "rejection_rate": 0.014814814814814815,
  "source_sha256": {
    "customers.csv": "1c33a80804cff79b0ea936ff527e31425edfed2d58afb63661648ca9a8556f94",
    "orders.csv": "e92fd75fa75d53009cdf4aa7d3963f54096c6452b43943da04952de548dca080"
  },
  "sql_sha256": "8a5a70bff88fed67dc361928e52ceea6e857e0f009c9c36b86bcf67a03c5ad73",
  "stages": [
    {
      "detail": "60 customers; 405 order rows",
      "name": "Extract",
      "status": "PASS"
    },
    {
      "detail": "6 quarantined; 1.48% vs 2.00% limit",
      "name": "Validate",
      "status": "WARN"
    },
    {
      "detail": "399 rows loaded; primary and foreign keys enforced",
      "name": "Load SQLite",
      "status": "PASS"
    },
    {
      "detail": "3 monthly report rows",
      "name": "Aggregate SQL",
      "status": "PASS"
    },
    {
      "detail": "7089413 net cents; 300 report orders matched Python",
      "name": "Reconcile",
      "status": "PASS"
    },
    {
      "detail": "CSV, JSON and static dashboard files generated",
      "name": "Publish",
      "status": "PASS"
    }
  ],
  "status": "WARN",
  "synthetic": true
}
