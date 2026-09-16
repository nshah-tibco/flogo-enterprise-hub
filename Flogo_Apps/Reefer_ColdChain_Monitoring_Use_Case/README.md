# Reefer Cold-Chain Monitoring — Flogo Event-Streaming Use Case

A port-relevant demonstration of **TIBCO Flogo as a lightweight event-streaming
handling agent** — sitting on **both sides of Kafka** to ingest, enrich, detect,
and route refrigerated-container (reefer) telemetry in real time.

This use case is built for the **PSA workshop** to position Flogo for
**Kafka / JMS / event handling** (not API-centric integration), **complementary
to TIBCO Streaming**: Streaming does high-throughput CEP / windowing / analytics;
Flogo is the lightweight, config-driven agent that ingests at the edge, enriches
against systems of record, and bridges protocols — as small single-binary runtimes
that fit at the edge, in containers, or on Kubernetes.

---

## What's in this folder

| File | Purpose |
|---|---|
| [ReeferTelemetryPublisher.flogo](ReeferTelemetryPublisher.flogo) | **Producer app** — timer-driven simulator that streams reefer telemetry to Kafka |
| [ReeferMonitorProcessor.flogo](ReeferMonitorProcessor.flogo) | **Consumer/processor app** — ingests telemetry → enriches from PostgreSQL → detects breaches → routes/alerts |
| [database.sql](database.sql) | PostgreSQL schema + seed (`reefer_containers` reference data, `reefer_alerts` audit) |
| [reset_data.sql](reset_data.sql) | Clears the audit trail and re-seeds the reference fleet between demo runs |
| [test_telemetry.md](test_telemetry.md) | Step-by-step tester's guide (run both apps, tail alerts, query the audit, publish manually) |
| [build_slides.py](build_slides.py) / [ReeferColdChain_Architecture.pptx](ReeferColdChain_Architecture.pptx) | Workshop deck (native editable shapes) |

---

## Architecture — Flogo on both sides of Kafka

```
  ┌──────────────────────────────┐        ┌──────────────────┐        ┌───────────────────────────────────────────┐
  │  ReeferTelemetryPublisher    │        │      Kafka       │        │        ReeferMonitorProcessor             │
  │  (Flogo producer app)        │        │                  │        │        (Flogo consumer/processor app)     │
  │                              │        │                  │        │                                           │
  │  Timer (every 10s)           │        │  topic:          │        │  Kafka consumer trigger                   │
  │    └─ BuildReadings (mapper) │ ─────► │  reefer.telemetry│ ─────► │    └─ ParseTelemetry (mapper)             │
  │    └─ Publish1..Publish5     │        │                  │        │    └─ LookupContainer ──► PostgreSQL      │
  │       (Kafka producers)      │        │                  │        │    └─ EnrichReading (limits)              │
  │                              │        │                  │        │        ├─[normal]─► LogNormal             │
  │                              │        │                  │        │        └─[breach]─► PublishAlert ──┐      │
  └──────────────────────────────┘        │  topic:          │ ◄──────┤                     PersistAlert  │      │
                                           │  reefer.alerts   │        │                     LogAlert      │      │
                                           └──────────────────┘        └───────────────────────────────────┼──────┘
                                                                                     PostgreSQL (reefer_monitoring) ◄┘
                                                                       reefer_containers (reference) · reefer_alerts (audit)
```

The **event-flow pattern**: `ingest → enrich → detect → route/alert`. Every reading
is checked against the container's own set-point and tolerance band (pulled from the
database), so the same flow handles vaccines at −20 °C and produce at +13 °C without
any per-container code.

---

## App A — `ReeferTelemetryPublisher` (producer / simulator)

A self-contained simulator so the demo needs no external Kafka producer.

- **Trigger:** timer, `Repeating`, interval = `=$property["PublishInterval_sec"]` (default **10 s**).
- **Flow `PublishTelemetryFlow`:**
  1. `StartActivity` (noop)
  2. `BuildReadings` (mapper) — builds an array of **5 reefer readings** as JSON strings,
     each stamped with a live `event_time` (`datetime.currentDatetime()`).
  3. `Publish1 … Publish5` (Kafka producers) — one message per reading to
     `reefer.telemetry`, keyed by `container_id`.
- **The 5 readings** (mixed outcomes, aligned to the DB seed):

  | Container | Cargo | Reading | Power | Expected |
  |---|---|---|---|---|
  | RCON-1001 | Pharma-Vaccines | −20.1 °C | ON | **normal** |
  | RCON-1002 | Frozen Seafood | −8.0 °C | ON | **breach** (too warm) |
  | RCON-1003 | Fresh Produce | 13.2 °C | OFF | **breach** (power off) |
  | RCON-1004 | Dairy | 4.2 °C | ON | **normal** |
  | RCON-1005 | Pharma-Insulin | 9.3 °C | ON | **breach** (too warm, HIGH priority) |

- **Connection:** `ReeferKafka` (`authMode: None`), brokers = `=$property["Kafka.Brokers"]`.
- **Properties:** `Kafka.Brokers` = `localhost:9092`, `TelemetryTopic` = `reefer.telemetry`,
  `PublishInterval_sec` = `10`.

## App B — `ReeferMonitorProcessor` (consumer / processor)

- **Trigger:** Kafka consumer, topic = `=$property["TelemetryTopic"]`,
  group = `=$property["ConsumerGroup"]` (`reefer-monitor`), `valueType: String`,
  `initialOffset: Oldest`.
- **Flow `ProcessTelemetryFlow`:**
  1. `StartActivity` (noop)
  2. `ParseTelemetry` (mapper) — parses the JSON message into typed fields.
  3. `LookupContainer` (PostgreSQL query) — `SELECT set_point_c, allowed_deviation_c,
     cargo_type, customer_name, destination_port, priority FROM reefer_containers
     WHERE container_id = ?containerId`.
  4. `EnrichReading` (mapper) — carries the reading + reference fields and computes
     `upperLimit = set_point_c + allowed_deviation_c` and `lowerLimit = set_point_c − allowed_deviation_c`.
  5. **Branch:**
     - **normal** → `LogNormal` — when `powerStatus == "ON"` **and** temperature is within `[lowerLimit, upperLimit]`.
     - **breach** → `PublishAlert` (Kafka → `reefer.alerts`) → `PersistAlert`
       (INSERT into `reefer_alerts`) → `LogAlert` — when power is not ON **or** temperature is out of band.
- **Connections:** `ReeferKafka` + `ReeferDB` (PostgreSQL).
- **Properties:** `Kafka.Brokers`, `TelemetryTopic`, `AlertsTopic` = `reefer.alerts`,
  `ConsumerGroup` = `reefer-monitor`, `PG.Host`, `PG.Port`, `PG.Database` = `reefer_monitoring`,
  `PG.User`, `PG.Password`.

---

## Prerequisites

- A running **Kafka** broker reachable at `Kafka.Brokers` (default `localhost:9092`).
- A running **PostgreSQL** instance (see `skills-library/.claude/skills/config.md` for host/port/user;
  defaults `localhost:5432`, user `postgres`).
- The **Flogo VSCode extension** (to open/run the apps in the designer) and/or the
  Flogo build CLI (paths are in `config.md`).

> Tool paths, DB credentials, and other environment values are read from
> `skills-library/.claude/skills/config.md`. Update that file to match your machine
> before running. The app properties above are the built-in defaults — override them
> per environment (designer app-properties panel, or engine env overrides) rather than
> editing the `.flogo` files.

## Setup & run

1. **Create the database and seed it:**
   ```bash
   createdb -U postgres reefer_monitoring
   psql -U postgres -d reefer_monitoring -f database.sql
   ```
2. **Create the Kafka topics** (or rely on broker auto-create):
   ```bash
   kafka-topics.sh --create --topic reefer.telemetry --bootstrap-server localhost:9092
   kafka-topics.sh --create --topic reefer.alerts    --bootstrap-server localhost:9092
   ```
3. **Run App B first** (`ReeferMonitorProcessor`) so the consumer is listening, then
   **run App A** (`ReeferTelemetryPublisher`). Open each `.flogo` in the Flogo designer
   and Run, or build a runnable with the Flogo build CLI (see `config.md`).
4. **Observe:** App A publishes 5 readings every 10 s; App B logs each reading as
   `[REEFER NORMAL]` or `[REEFER BREACH]`, publishes breaches to `reefer.alerts`, and
   appends them to `reefer_alerts`.

Full walk-through — including how to tail the alerts topic, query the audit table, and
publish your own readings — is in [test_telemetry.md](test_telemetry.md).

---

## Positioning notes (for the workshop)

- **Not API-centric.** There are **no REST triggers** anywhere in this use case — it is
  pure event handling (Kafka in, Kafka out, database enrichment). This keeps the
  "event streaming agent, not integration API" message clean.
- **Complementary to TIBCO Streaming.** Flogo handles lightweight edge ingestion,
  enrichment, routing, and protocol bridging (Kafka / JMS / EMS). TIBCO Streaming
  remains the engine for high-throughput continuous analytics, windowing, and complex
  event processing. The two compose: Flogo agents feed and act on the streams that
  Streaming analyzes.
- **Footprint.** Flogo apps are config-driven and compile to small single binaries —
  easy to run many of them at the edge, in containers, or on Kubernetes, close to where
  the events originate.
