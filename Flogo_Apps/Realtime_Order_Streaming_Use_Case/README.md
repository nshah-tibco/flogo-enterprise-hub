# Real-time Order Streaming Use Case

A TIBCO Flogo Enterprise app that demonstrates a classic **streaming event-flow**
pattern with Apache Kafka:

> **Ingest → Enrich → Route / Alert**

Order events arrive on a Kafka topic, are enriched with customer data from
PostgreSQL, and are then routed: **high-risk / high-value ("flagged") orders**
are published to a downstream Kafka topic *and* audited in a database table, while
**normal orders** are simply logged.

The app is `OrderStreamProcessor.flogo`, built entirely with the Flogo Design
Assistant CLI (`fda`). Kafka brokers, topics, consumer group, and DB credentials
are all parameterized as **application properties**, so no live cluster is baked
into the app — point the properties at your environment and run.

---

## Architecture

```
                        ┌─────────────────────────────────────────────────────────┐
   POST /orders         │                  OrderStreamProcessor                    │
  (JSON order) ───────► │                                                          │
                        │  PublishOrderFlow  (REST feeder — convenience only)      │
                        │  ┌────────────┐  ┌────────────┐  ┌──────────────┐        │
                        │  │StartActivity│─►│BuildMessage│─►│PublishIncoming│─┐     │
                        │  └────────────┘  │ (JSON str) │  │(Kafka producer)│ │     │
                        │                  └────────────┘  └──────────────┘  │     │
                        │                                          │  Return  ◄─┘   │
                        └──────────────────────────────────────────┼───────────────┘
                                                                    ▼
                                                      Kafka topic: orders.incoming
                                                                    │
                        ┌───────────────────────────────────────────┼──────────────┐
                        │                  OrderStreamProcessor       ▼              │
                        │  ProcessOrderFlow  (the streaming processor)              │
                        │                                                           │
                        │  KafkaConsumer(trigger) ─► ParseOrder ─► LookupCustomer   │
                        │                             (JSON→obj)   (PostgreSQL query)│
                        │                                              │            │
                        │                                              ▼            │
                        │                                        EnrichCustomer     │
                        │                                        (customer fields)  │
                        │                          normal ┌───────────┴──────────┐ flagged
                        │                                 ▼                       ▼         │
                        │                            LogNormal            PublishFlagged    │
                        │                             (log)              (Kafka producer)   │
                        │                                                       │           │
                        │                                                       ▼           │
                        │                                                 PersistFlagged     │
                        │                                                (PostgreSQL insert)│
                        │                                                       │           │
                        │                                                       ▼           │
                        │                                                  LogFlagged        │
                        └───────────────────────────────────────────────────────┼──────────┘
                                                                                  ▼
                                          Kafka topic: orders.flagged   +   DB table: flagged_orders
```

---

## The two flows

### 1. `PublishOrderFlow` — REST feeder (test convenience)

A small helper so you can drive the demo with `curl` instead of a Kafka producer.
Exposes `POST /orders` (port 9999). It builds a JSON order string and publishes it
to `orders.incoming`, then returns a confirmation.

| Activity | Type | What it does |
|---|---|---|
| `StartActivity` | noop | Flow entry point |
| `BuildMessage` | mapper | Concatenates the request body into a JSON string (payload) |
| `PublishIncoming` | Kafka producer | Publishes payload to `orders.incoming`, key = `order_id` |
| `Return` | actreturn | Returns `{ code, message }` to the caller |

> This flow exists purely to make the demo self-contained. In a real deployment
> the upstream system would publish directly to `orders.incoming` and this flow
> would not be needed.

### 2. `ProcessOrderFlow` — the streaming processor

Triggered by the **Kafka consumer** on `orders.incoming` (consumer group
`order-stream-processor`, `initialOffset: Oldest`).

| Activity | Type | What it does |
|---|---|---|
| `StartActivity` | noop | Flow entry point |
| `ParseOrder` | mapper | Parses the raw message string into typed fields (`coerce.toObject` + `json.get`) |
| `LookupCustomer` | PostgreSQL query | `SELECT ... FROM customers WHERE customer_id = ?customerId` |
| `EnrichCustomer` | mapper | Extracts `customerName`, `tier`, `region`, `accountStatus`, `creditLimit` from the first record |
| `LogNormal` | log | *(normal branch)* logs the order was processed normally |
| `PublishFlagged` | Kafka producer | *(flagged branch)* re-publishes the original message to `orders.flagged` |
| `PersistFlagged` | PostgreSQL insert | *(flagged branch)* writes an audit row to `flagged_orders` |
| `LogFlagged` | log | *(flagged branch)* logs the alert |

#### Routing logic (the branch conditions)

The split happens on the two outgoing links from `EnrichCustomer`:

- **FLAGGED** if **any** of:
  - `amount > HighValueThreshold` (default **5000**), **or**
  - customer `tier == "VIP"`, **or**
  - customer `accountStatus != "ACTIVE"` (e.g. `SUSPENDED`, `FRAUD_HOLD`)
- **NORMAL** otherwise (the exact complement).

The flagged branch does three things: publishes to `orders.flagged`, persists an
audit row (with a human-readable `flag_reason`), and logs an alert.

---

## Components

### Connections
| Name | Type | Bound to |
|---|---|---|
| `OrderKafka` | Kafka (`con_kafka`) | `brokers = $property["Kafka.Brokers"]`, `authMode: None` |
| `OrderDB` | PostgreSQL (`con_postgresql`) | host/port/database/user/password → `PG.*` properties |

### Application properties (edit these for your environment)
| Property | Type | Default |
|---|---|---|
| `Kafka.Brokers` | string | `localhost:9092` |
| `IncomingTopic` | string | `orders.incoming` |
| `FlaggedTopic` | string | `orders.flagged` |
| `ConsumerGroup` | string | `order-stream-processor` |
| `HighValueThreshold` | number | `5000` |
| `PG.Host` | string | `localhost` |
| `PG.Port` | number | `5432` |
| `PG.Database` | string | `order_streaming` |
| `PG.User` | string | `postgres` |
| `PG.Password` | string | `admin` |
| `HttpStatusCode` | number | `200` |

> At runtime you can override any of these with environment variables when the
> engine is started with `FLOGO_APP_PROPS_ENV=auto`.

### Schemas
`OrderRequest` (REST body) · `OrderParsed` (typed order) · `CustomerEnriched`
(enrichment output) · `OrderMessage` (Kafka payload wrapper).

---

## Setup & run

### 1. Kafka
Have a broker at `localhost:9092` and create the two topics:

```bash
kafka-topics.sh --create --bootstrap-server localhost:9092 --topic orders.incoming --partitions 1 --replication-factor 1
kafka-topics.sh --create --bootstrap-server localhost:9092 --topic orders.flagged  --partitions 1 --replication-factor 1
```

### 2. PostgreSQL
Create the database and load the schema + seed data:

```bash
psql -c "CREATE DATABASE order_streaming;"
psql -d order_streaming -f database.sql
```

`database.sql` creates the `customers` lookup table (6 seed customers chosen to
show both outcomes) and the `flagged_orders` audit table.

### 3. Run the app
Open `OrderStreamProcessor.flogo` in the TIBCO Flogo VS Code designer and run it,
or build it with your Flogo build toolchain. The REST feeder listens on `:9999`;
the Kafka consumer starts polling `orders.incoming` automatically.

> This repo ships the **app design** (`.flogo`) only — it is not pre-compiled to a
> binary. Build it with your usual Flogo build step when you want an executable.

---

## Testing

See **[test_orders.md](test_orders.md)** for ready-to-run `curl` commands covering
all four cases (normal, high-value, VIP, non-active account), how to tail the
`orders.flagged` topic, and how to query the audit table.

Quick sanity flow:

```bash
# NORMAL  (customer 103, STANDARD/ACTIVE, small amount) → logged only
curl -X POST http://localhost:9999/orders -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-2001","customer_id":103,"amount":200,"currency":"USD","items":1,"channel":"web"}'

# FLAGGED (customer 101, amount 7500 > 5000) → orders.flagged + audit row + alert
curl -X POST http://localhost:9999/orders -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-2002","customer_id":101,"amount":7500,"currency":"USD","items":3,"channel":"web"}'
```

Reset between runs (keeps tables, clears audit + re-seeds customers):

```bash
psql -d order_streaming -f reset_data.sql
```

---

## Files

| File | Purpose |
|---|---|
| `OrderStreamProcessor.flogo` | The Flogo app (both flows, connections, properties, schemas) |
| `orders-api-spec.json` | OpenAPI 3.0 spec for the REST feeder (embedded in the app as the trigger swagger) |
| `database.sql` | Creates + seeds `customers` and `flagged_orders` (idempotent) |
| `reset_data.sql` | Resets demo state without dropping tables |
| `test_orders.md` | Tester's guide with curl commands and verification queries |

---

## Implementation notes

- **JSON handling.** Flogo has no `json.stringify`. The REST feeder builds the
  outbound JSON by string concatenation; the processor parses inbound messages
  with `coerce.toObject(...)` + `json.get(obj, "key")`. The query result is read
  as `json.get(array.get($activity[LookupCustomer].Output.records, 0), "col")`.
- **Kafka value type is `String`** on the trigger and both producers — messages
  are plain JSON strings (no Avro/schema registry needed for the demo).
- **Link conditions** use `==` / `!=` / `>` (not the unary `!`), which the Flogo
  designer's expression linter accepts.
- **Demo credentials.** `PG.Password` defaults to `admin` and Kafka uses
  `authMode: None`. These are local-dev placeholders — change them (or override
  via env vars) before using anywhere real.
