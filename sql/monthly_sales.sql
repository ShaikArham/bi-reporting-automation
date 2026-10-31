-- Completed positive-net orders only. All monetary values are integer cents.
SELECT substr(order_date, 1, 7) AS month,
       COUNT(*) AS orders,
       SUM(amount_cents) AS gross_cents,
       SUM(refund_cents) AS refund_cents,
       SUM(amount_cents - refund_cents) AS net_cents
FROM orders
WHERE status = 'completed' AND amount_cents > refund_cents
GROUP BY substr(order_date, 1, 7)
ORDER BY month;
