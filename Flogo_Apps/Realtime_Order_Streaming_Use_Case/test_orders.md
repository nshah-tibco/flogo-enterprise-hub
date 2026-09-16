# Real-time Order Streaming - Tester's Guide

End-to-end guide for exercising the **Real-time Order Streaming** demo. Orders are
ingested from Kafka, enriched with customer data from PostgreSQL, then routed:
flagged orders are published to a downstream Kafka topic and audited in a DB table,
while normal orders are just logged.

**Flag rule** — an order is **FLAGGED** if any of the following is true:

- `amount > 5000`, OR
- customer `tier = 'VIP'`, OR
- customer `account_status <> 'ACTIVE'`

Otherwise it is **NORMAL**.

---

## Prerequisites

**1. A running Kafka broker at `localhost:9092`** with the two demo topics. Create
them (idempotent-ish; skip if they already exist):

```bash
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic orders.incoming \
  --partitions 1 --replication-factor 1

kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic orders.flagged \
  --partitions 1 --replication-factor 1
```

The processor consumes `orders.incoming` under consumer group
`order-stream-processor` and publishes flagged orders to `orders.flagged`.
Brokers use `authMode None` (no SASL/TLS) for local dev.

**2. PostgreSQL with the `order_streaming` database set up.** Create the database
once, then load the schema and seed data:

```bash
psql -c "CREATE DATABASE order_streaming;"
psql -d order_streaming -f database.sql
```

**3. The running OrderStreamProcessor Flogo app**, connected to the Kafka broker
above and to the `order_streaming` database. It also exposes the REST feeder
endpoint at `http://localhost:9999/orders`, which accepts an order as JSON and
publishes it onto `orders.incoming`.

---

## Publish test orders

Post orders to the REST feeder. Each example below states the expected outcome.

**(a) NORMAL** — customer 103 (STANDARD / ACTIVE), amount 200. No rule matches,
so the order is simply logged (nothing published to `orders.flagged`, no audit row).

```bash
curl -X POST http://localhost:9999/orders \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-2001","customer_id":103,"amount":200,"currency":"USD","items":1,"channel":"web"}'
```

**(b) FLAGGED (high-value)** — customer 101 (GOLD / ACTIVE), amount 7500. Amount
exceeds 5000, so the order is **published to `orders.flagged`**, a row is written
to `flagged_orders`, and an alert is logged.

```bash
curl -X POST http://localhost:9999/orders \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-2002","customer_id":101,"amount":7500,"currency":"USD","items":3,"channel":"web"}'
```

**(c) FLAGGED (VIP)** — customer 102 (VIP / ACTIVE), amount 300. The customer tier
is VIP, so even a small order is **published to `orders.flagged`**, audited in
`flagged_orders`, and alerted.

```bash
curl -X POST http://localhost:9999/orders \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-2003","customer_id":102,"amount":300,"currency":"USD","items":1,"channel":"mobile"}'
```

**(d) FLAGGED (account status)** — customer 104 (STANDARD / SUSPENDED), amount 100.
Account status is not ACTIVE, so the order is **published to `orders.flagged`**,
audited in `flagged_orders`, and alerted.

```bash
curl -X POST http://localhost:9999/orders \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-2004","customer_id":104,"amount":100,"currency":"USD","items":2,"channel":"store"}'
```

---

## Watch the flagged stream

Tail the downstream topic to see enriched, flagged orders as they are published:

```bash
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic orders.flagged \
  --from-beginning
```

Examples (b), (c), and (d) should appear here; example (a) should not.

---

## Verify the audit table

Query the audit sink to confirm each flagged order was recorded with its reason:

```bash
psql -d order_streaming -c "SELECT order_id, customer_name, amount, tier, account_status, flag_reason, flagged_at FROM flagged_orders ORDER BY flagged_at DESC;"
```

You should see one row each for ORD-2002, ORD-2003, and ORD-2004 (not ORD-2001).

---

## Reset between runs

Clear the audit table and restore the seed customers without dropping any tables:

```bash
psql -d order_streaming -f reset_data.sql
```
