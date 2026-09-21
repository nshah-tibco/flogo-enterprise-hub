# Reefer Cold-Chain Monitoring (AMQP) — Flogo Event-Streaming Use Case

A port-relevant, **runnable** demonstration of **TIBCO Flogo as a lightweight
event-streaming handling agent** — sitting on **both sides of an AMQP broker**
(Solace PubSub+ / any AMQP 1.0 broker) to ingest, enrich, detect, and route
refrigerated-container (reefer) telemetry in real time.

Two small Flogo apps and a PostgreSQL database are all you need. Follow
[Setup & run](#setup--run) and you'll have live alerts flowing in about 10 minutes.

---

## Overview

Refrigerated shipping containers ("reefers") carry temperature-sensitive cargo —
vaccines, insulin, seafood, produce, dairy. Each container has a **target
temperature** and an **allowed tolerance band**; drift outside the band (or a
power loss) risks spoilage, insurance claims, and — for pharma — patient safety.
At a large port, thousands of reefers stream telemetry continuously.

This use case shows how Flogo handles that stream end to end:

1. **Ingest** — a reefer publishes a telemetry reading (temperature, power, GPS) to an AMQP topic.
2. **Enrich** — Flogo looks the container up in a system-of-record (PostgreSQL) to get its
   set-point, tolerance band, cargo, customer, and destination.
3. **Detect** — Flogo compares the reading against that container's *own* limits.
4. **Route / alert** — in-range readings are logged; breaches are republished to an alerts
   topic **and** written to an audit table.
5. **Acknowledge** — each message is explicitly acknowledged only after it is fully processed,
   so an in-flight crash re-delivers rather than drops the message.

The same flow handles vaccines at −20 °C and produce at +13 °C **without any
per-container code**, because every threshold comes from the database.

**What this demonstrates for the workshop**

- Flogo as an **event agent, not an API** — there are **no REST triggers** anywhere; it is pure
  AMQP-in / AMQP-out with database enrichment.
- Flogo on **both sides** of the broker — one app produces, one app consumes.
- **At-least-once delivery** via Client acknowledgement + a durable shared subscription — no custom code.
- **Complementary to TIBCO Streaming**: Streaming does high-throughput CEP / windowing / analytics;
  Flogo is the lightweight, config-driven agent that ingests at the edge, enriches against systems of
  record, and bridges protocols — as small single-binary runtimes that fit at the edge, in containers,
  or on Kubernetes.

> This is the **AMQP variant** of the Kafka use case in
> `Flogo_Apps/Reefer_ColdChain_Monitoring_Use_Case` — identical enrichment/detection logic and
> PostgreSQL system-of-record, but the messaging layer is **AMQP 1.0 (JMS-style pub/sub)** using the
> Flogo **AMQP Receive Message** trigger and **AMQP Send Message** / **AMQP Acknowledge** activities.
> See [How this app relates to the Kafka variant](#how-this-app-relates-to-the-kafka-variant).

---

## What's in this folder

| File | Purpose |
|---|---|
| [ReeferTelemetryPublisher_AMQP.flogo](ReeferTelemetryPublisher_AMQP.flogo) | **Producer app** — timer-driven simulator that streams 5 reefer readings over AMQP every 10 s |
| [ReeferMonitorProcessor_AMQP.flogo](ReeferMonitorProcessor_AMQP.flogo) | **Consumer/processor app** — receives telemetry → enriches from PostgreSQL → detects breaches → routes/alerts → acknowledges |
| [database.sql](database.sql) | PostgreSQL schema + seed (`reefer_containers` reference data, `reefer_alerts` audit table) |
| [reset_data.sql](reset_data.sql) | Clears the audit trail and re-seeds the reference fleet between demo runs |
| [test_telemetry.md](test_telemetry.md) | Extended tester's guide (Solace UI walkthrough — Topic Endpoint, Try Me!, manual publish) |
| [build_amqp_apps.py](build_amqp_apps.py) | Deterministic builder that derived these AMQP apps from the Kafka originals (documents the clone) |
| [build_slides.py](build_slides.py) / [ReeferColdChain_Architecture_AMQP.pptx](ReeferColdChain_Architecture_AMQP.pptx) | Workshop deck (native editable shapes) |

---

## Architecture — Flogo on both sides of the AMQP broker

```
  ┌──────────────────────────────┐        ┌──────────────────┐        ┌───────────────────────────────────────────┐
  │ReeferTelemetryPublisher_AMQP │        │   AMQP broker    │        │        ReeferMonitorProcessor_AMQP        │
  │  (Flogo producer app)        │        │ (Solace PubSub+) │        │        (Flogo consumer/processor app)     │
  │                              │        │                  │        │                                           │
  │  Timer (every 10s)           │        │  topic:          │        │  AMQP Receive Message trigger             │
  │    └─ BuildReadings (mapper) │ ─────► │  topic/reefer/   │ ─────► │    └─ ParseTelemetry (mapper)             │
  │    └─ Publish1..Publish5     │        │  telemetry       │        │    └─ LookupContainer ──► PostgreSQL      │
  │       (AMQP Send Message)    │        │                  │        │    └─ EnrichReading (limits)              │
  │                              │        │                  │        │        ├─[normal]─► LogNormal ─► Ack      │
  │                              │        │                  │        │        └─[breach]─► PublishAlert ──┐      │
  └──────────────────────────────┘        │  topic:          │ ◄──────┤            (AMQP Send Message)     │      │
                                           │  topic/reefer/   │        │            PersistAlert           │      │
                                           │  alerts          │        │            LogAlert ─► Acknowledge│      │
                                           └──────────────────┘        └───────────────────────────────────┼──────┘
                                                                                     PostgreSQL (reefer_monitoring) ◄┘
                                                                       reefer_containers (reference) · reefer_alerts (audit)
```

**The event-flow pattern:** `ingest → enrich → detect → route/alert → acknowledge`.

Because the consumer runs in **Client acknowledgement mode**, every message is explicitly
acknowledged (`AMQP Acknowledge`) only after it has been fully processed on **both** the normal
and breach paths — so an in-flight crash re-delivers the message rather than dropping it.

---

## How it works

### App A — `ReeferTelemetryPublisher_AMQP` (producer / simulator)

A self-contained simulator so the demo needs no external AMQP publisher.

- **Trigger:** timer, `Repeating`, interval = `=$property["PublishInterval_sec"]` (default **10 s**).
- **Flow `PublishTelemetryFlow`:**
  1. `StartActivity` (noop)
  2. `BuildReadings` (mapper) — builds an array of **5 reefer readings** as JSON strings, each stamped
     with a live `event_time` (`datetime.currentDatetime()`).
  3. `Publish1 … Publish5` (**AMQP Send Message**) — one message per reading to `topic/reefer/telemetry`,
     `messageType: TextMessage`, `deliveryMode: Persistent`, with `container_id` carried as an AMQP
     **user property**.
- **The 5 readings** (mixed outcomes, aligned to the DB seed — 3 breaches + 2 normals every tick):

  | Container | Cargo | Reading | Power | Set-point ± tol | Outcome |
  |---|---|---|---|---|---|
  | RCON-1001 | Pharma-Vaccines | −20.1 °C | ON | −20 ± 2 | **NORMAL** |
  | RCON-1002 | Frozen Seafood | −8.0 °C | ON | −18 ± 3 | **BREACH** — too warm |
  | RCON-1003 | Fresh Produce | 13.2 °C | OFF | 13 ± 1 | **BREACH** — power off |
  | RCON-1004 | Dairy | 4.2 °C | ON | 4 ± 2 | **NORMAL** |
  | RCON-1005 | Pharma-Insulin | 9.3 °C | ON | 5 ± 1 | **BREACH** — too warm (HIGH priority) |

- **Connection:** `amqp-1.0-connection` (`authMode: None`).
- **Properties:** `AMQP.amqp-1_0-connection.Host` = `localhost`, `.Port` = `5672`, `.Virtual_Host` = `/`,
  `.User_Name` / `.Password` = `admin`, `TelemetryTopic` = `topic/reefer/telemetry`,
  `PublishInterval_sec` = `10`.

### App B — `ReeferMonitorProcessor_AMQP` (consumer / processor)

- **Trigger:** **AMQP Receive Message** (consumer), `entityType: Topic`,
  `entityName` = `=$property["TelemetryTopic"]`, **durable shared subscription**
  (`subscriptionName` = `=$property["SubscriptionName"]` = `reefer-telemetry-sub`),
  `messageType: TextMessage`, `acknowledgementMode: Client`, `prefetchCount: 10`.
- **Flow `ProcessTelemetryFlow`:**
  1. `StartActivity` (noop)
  2. `ParseTelemetry` (mapper) — parses the AMQP message **body** (`$flow.body`) into typed fields.
  3. `LookupContainer` (PostgreSQL query) — `SELECT set_point_c, allowed_deviation_c, cargo_type,
     customer_name, destination_port, priority FROM reefer_containers WHERE container_id = ?containerId`.
  4. `EnrichReading` (mapper) — carries the reading + reference fields and computes
     `upperLimit = set_point_c + allowed_deviation_c` and `lowerLimit = set_point_c − allowed_deviation_c`.
  5. **Branch:**
     - **normal** → `LogNormal` → `AckNormal` (**AMQP Acknowledge**) — when `powerStatus == "ON"` **and**
       temperature is within `[lowerLimit, upperLimit]`.
     - **breach** → `PublishAlert` (**AMQP Send Message** → `topic/reefer/alerts`) → `PersistAlert`
       (INSERT into `reefer_alerts`) → `LogAlert` → `AckBreach` (**AMQP Acknowledge**) — when power is not
       ON **or** temperature is out of band.
- **Connections:** `amqp-1.0-connection` + `ReeferDB` (PostgreSQL).
- **Properties:** `AMQP.amqp-1_0-connection.*`, `TelemetryTopic` = `topic/reefer/telemetry`,
  `AlertsTopic` = `topic/reefer/alerts`, `SubscriptionName` = `reefer-telemetry-sub`,
  `PostgreSQL.ReeferDB.Host` / `.Port` / `.Database_Name` = `reefer_monitoring` / `.User` / `.Password`.

---

## Prerequisites

| Requirement | Detail |
|---|---|
| **AMQP 1.0 broker** | Reachable at `localhost:5672`. This guide uses **Solace PubSub+ Standard** in Docker. |
| **PostgreSQL** | Reachable at `localhost:5432` (default user `postgres`). |
| **`psql`** | On your PATH, to create/seed the DB and query the audit table. |
| **Docker** | To run the Solace broker (or point the apps at any AMQP 1.0 broker you already have). |
| **Flogo VSCode extension** | To open and **Run** the two `.flogo` apps in the designer. (Optional: the Flogo build CLI — see `config.md` — if you prefer a runnable binary; you do not need to build binaries just to run the demo.) |

> Tool paths, DB credentials, and broker addresses are read from
> `skills-library/.claude/skills/config.md`. The app properties above are the built-in defaults —
> override them per environment in the designer's app-properties panel (or via engine env overrides)
> rather than editing the `.flogo` files.

---

## Setup & run

Steps 1–3 are one-time **broker setup** (per fresh container); steps 4–7 run the demo. Every SEMP
command below runs *inside* the container via `docker exec`, so you need no extra tooling on the host —
and it's exactly what this demo was verified with. (Each step also lists the PubSub+ Manager UI
equivalent if you prefer clicking.)

### 1. Start the Solace PubSub+ broker

```bash
docker run -d --name=solace \
  -p 8080:8080 -p 8008:8008 -p 1443:1443 \
  -p 5672:5672 -p 5671:5671 -p 55555:55555 \
  --shm-size=1g \
  -e username_admin_globalaccesslevel=admin \
  -e username_admin_password=admin \
  solace/solace-pubsub-standard
```

| Port | Purpose |
|---|---|
| 8080 | PubSub+ Manager (web UI) + SEMP |
| 8008 | Web messaging (SMF over WebSocket) — **required by the browser Try Me! client** (step 6) |
| 1443 | Web messaging over TLS (wss) |
| 5672 | AMQP 1.0 — **what the Flogo apps connect to** |
| 5671 | AMQP 1.0 over TLS |
| 55555 | SMF (plain TCP) |

Wait ~30–60 s for it to boot, then confirm it's ready (expect `200`) and open **PubSub+ Manager** at
<http://localhost:8080> (login `admin` / `admin`):

```bash
docker exec solace curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5550/health-check/guaranteed-active
```

### 2. Enable AMQP authentication (required)

A fresh broker leaves the `default` VPN's basic-auth type at `none`, so it only offers the **ANONYMOUS**
SASL mechanism — but the Flogo AMQP connector authenticates with **username/password (SASL PLAIN)**.
Skip this and App B dies at startup with `no supported auth mechanism ([ANONYMOUS])`. Switch the VPN to
**internal** auth and add the `admin` client-username the apps connect as:

```bash
# make the broker offer SASL PLAIN
docker exec solace curl -s -u admin:admin -X PATCH \
  http://localhost:8080/SEMP/v2/config/msgVpns/default \
  -H "Content-Type: application/json" -d '{"authenticationBasicType":"internal"}'

# the messaging client-username the apps authenticate as (admin / admin)
docker exec solace curl -s -u admin:admin -X POST \
  http://localhost:8080/SEMP/v2/config/msgVpns/default/clientUsernames \
  -H "Content-Type: application/json" \
  -d '{"clientUsername":"admin","password":"admin","enabled":true}'
```

> **UI equivalent:** Access Control → **Client Authentication** → Basic = **Internal**; then Access
> Control → **Client Usernames** → **+** `admin` / password `admin` / **Enabled**.

### 3. Create the durable Topic Endpoint

App B uses a **durable shared subscription** named `reefer-telemetry-sub`. On Solace that maps to a
**Topic Endpoint**, which must be **Non-Exclusive** (a shared subscriber requires it) with
**`modify-topic`** permission — the AMQP durable subscriber *registers* its topic on the endpoint at
bind time, so `consume` permission would make the bind fail:

```bash
docker exec solace curl -s -u admin:admin -X POST \
  http://localhost:8080/SEMP/v2/config/msgVpns/default/topicEndpoints \
  -H "Content-Type: application/json" \
  -d '{"topicEndpointName":"reefer-telemetry-sub","accessType":"non-exclusive","permission":"modify-topic","ingressEnabled":true,"egressEnabled":true}'
```

You do **not** set the topic here — App B attaches `topic/reefer/telemetry` to the endpoint
automatically when it connects. The alerts topic `topic/reefer/alerts` needs **no** endpoint; you
observe it with a direct Try Me! subscription in step 6.

> **UI equivalent:** Queues → **Topic Endpoints** → **+ Topic Endpoint** → name `reefer-telemetry-sub`,
> **Access Type = Non-Exclusive**, **Non-Owner Permission = Modify Topic**, Enabled. (The topic column
> stays blank until App B connects.) Full UI walkthrough: [test_telemetry.md](test_telemetry.md).

### 4. Create and seed the database

```bash
createdb -U postgres reefer_monitoring
psql -U postgres -d reefer_monitoring -f database.sql
```

Verify the reference fleet loaded (expect 7 containers, `reefer_alerts` empty):

```bash
psql -U postgres -d reefer_monitoring -c "SELECT container_id, cargo_type, set_point_c, allowed_deviation_c, priority FROM reefer_containers ORDER BY container_id;"
psql -U postgres -d reefer_monitoring -c "SELECT count(*) FROM reefer_alerts;"   -- expect 0
```

### 5. Run App B first (the consumer)

Open [ReeferMonitorProcessor_AMQP.flogo](ReeferMonitorProcessor_AMQP.flogo) in the Flogo designer and
**Run**. Starting it first binds the durable subscription to the topic endpoint before any telemetry
arrives. A clean start loads the AMQP/PostgreSQL contributions and shows **no** connection error — see
[How to verify it's working](#how-to-verify-its-working).

### 6. Subscribe to alerts with Try Me! (before App A)

In PubSub+ Manager open **Try Me!** (top-right) and use the **Subscriber** pane only:

| Field | Value |
|---|---|
| Broker URL | `ws://localhost:8008` |
| Message VPN | `default` |
| Client Username | `admin` |
| Client Password | `admin` |

Click **Connect**, then in **Topic Subscriber** enter **`topic/reefer/alerts`** and **Subscribe**.
(Ignore the Publisher pane — that's the built-in sample.) Subscribing *before* App A starts means every
alert is delivered live instead of discarded.

### 7. Run App A (the producer)

Open [ReeferTelemetryPublisher_AMQP.flogo](ReeferTelemetryPublisher_AMQP.flogo) and **Run**. Every 10 s
it publishes 5 readings to `topic/reefer/telemetry` — 3 of them engineered to breach — and alerts start
streaming into Try Me! and into `reefer_alerts`.

---

## How to verify it's working

Five independent green signals, from the app through the broker to the database. If all five hold, the
whole pipeline is running end to end.

### 1. App B started cleanly (no auth error)

App B's console loads the runtime + contributions and then shows **no** connection error — in particular
**not** `no supported auth mechanism ([ANONYMOUS])` (that means step 2 was skipped). A healthy start:

```
INFO  [flogo.init] -  TIBCO Flogo® Runtime - 2.26.8
INFO  [flogo.init] -  Loading contribution AMQP - 1.0.0-b01
INFO  [flogo.init] -  Loading contribution PostgreSQL - 2.7.2-b01
INFO  [flogo.init] -  Starting TIBCO Flogo® Runtime
```

Then, once App A is publishing, one log line per reading (**2 normals + 3 breaches per tick**):

```
INFO   [REEFER NORMAL] RCON-1001 (Pharma-Vaccines) temp=-20.1C within [-22,-18]C power=ON
INFO   [REEFER BREACH] MEDIUM RCON-1002 (Frozen Seafood) cust=Ocean Harvest Ltd dest=Hamburg temp=-8C setpoint=-18C allowed=[-21,-15]C power=ON
INFO   [REEFER BREACH] MEDIUM RCON-1003 (Fresh Produce) cust=Tropical Fruits Co dest=Yokohama temp=13.2C setpoint=13C allowed=[12,14]C power=OFF
INFO   [REEFER NORMAL] RCON-1004 (Dairy) temp=4.2C within [2,6]C power=ON
INFO   [REEFER BREACH] HIGH RCON-1005 (Pharma-Insulin) cust=MediCore Logistics dest=Los Angeles temp=9.3C setpoint=5C allowed=[4,6]C power=ON
```

RCON-1002 is too warm (−8 °C against a −21…−15 °C band), RCON-1003 lost power, and RCON-1005 is a
**HIGH-priority** insulin breach (9.3 °C against a 4…6 °C band). RCON-1001 and RCON-1004 are within band.
(App A produces no console output at the default log level — it just publishes — so all the visible action
is on App B and the broker.)

### 2. App B is bound to the endpoint (Consumers = 1)

PubSub+ Manager → Queues → **Topic Endpoints** → `reefer-telemetry-sub`:

| Column | Expected |
|---|---|
| Access Type | **Non-Exclusive** |
| Topic | **`topic/reefer/telemetry`** (registered by App B on connect) |
| Consumers | **1** |
| Messages Queued | **0** while App B keeps up (may spike then drain) |

Consumers = 1 with 0 queued means App B is bound and draining telemetry in real time. **Consumers = 0**
means it never bound — recheck steps 2–3 (auth + endpoint) and restart App B.

### 3. No publish discards on App A

PubSub+ Manager → **Clients** → **AMQP** tab. App A's client should show **Incoming Message Discards = 0** —
every telemetry message is spooled to the endpoint and delivered. (A discard count that climbs on *App B's*
client is its alert publishes to `topic/reefer/alerts` while nothing subscribes — harmless, and it stops
once the Try Me! subscriber from step 6 is connected.)

### 4. Alerts stream into Try Me!

With the Try Me! subscriber connected (step 6), "Messages (Most Recent 20)" fills with **3 messages every
10 s** — the enriched breach JSON for RCON-1002, RCON-1003, RCON-1005, each also carrying AMQP user
properties `container_id` and `priority`. Example body:

```json
{"container_id":"RCON-1005","cargo_type":"Pharma-Insulin","customer_name":"MediCore Logistics","destination_port":"Los Angeles","priority":"HIGH","temperature_c":9.3,"set_point_c":5,"upper_limit_c":6,"lower_limit_c":4,"power_status":"ON","event_time":"2026-09-22T10:00:00Z"}
```

### 5. The audit trail grows (the definitive proof)

Every breach is inserted into `reefer_alerts`. Run the roll-up twice a few seconds apart — the counts
climb **+3 per tick**, one per breach container, and RCON-1001 / RCON-1004 **never appear**:

```bash
psql -U postgres -d reefer_monitoring -c "SELECT container_id, count(*) AS breaches, max(alerted_at) AS last_seen FROM reefer_alerts GROUP BY container_id ORDER BY breaches DESC;"
```

```
 container_id | breaches |         last_seen
--------------+----------+----------------------------
 RCON-1003    |      113 | 2026-09-22 01:47:48.488856
 RCON-1002    |      113 | 2026-09-22 01:47:48.339350
 RCON-1005    |      113 | 2026-09-22 01:47:48.970129
```

Three containers, breach counts **increasing in lockstep**, RCON-1001/1004 absent — that's the whole
pipeline (produce → AMQP → consume → enrich → detect → route + audit) verified. The most recent rows and
their reasons:

```bash
psql -U postgres -d reefer_monitoring -c "SELECT alert_id, container_id, reported_temp_c, power_status, alert_reason FROM reefer_alerts ORDER BY alert_id DESC LIMIT 6;"
```

```
 alert_id | container_id | reported_temp_c | power_status |                      alert_reason
----------+--------------+-----------------+--------------+--------------------------------------------------------
      339 | RCON-1005    |            9.30 | ON           | power=ON, temp=9.3C, allowed 4 to 6C, setpoint=5C
      338 | RCON-1003    |           13.20 | OFF          | power=OFF, temp=13.2C, allowed 12 to 14C, setpoint=13C
      337 | RCON-1002    |           -8.00 | ON           | power=ON, temp=-8C, allowed -21 to -15C, setpoint=-18C
```

**Live tail** (a good screen to leave up during the workshop — `Ctrl-C` to stop):

```bash
while true; do psql -U postgres -d reefer_monitoring \
  -c "SELECT alert_id, container_id, reported_temp_c, power_status, alert_reason FROM reefer_alerts ORDER BY alert_id DESC LIMIT 5;"; sleep 5; done
```

---

## Publish your own reading (optional)

You don't need App A to exercise the processor. In PubSub+ Manager → **Try Me!** → **Publisher**, set
the topic to `topic/reefer/telemetry` and paste a JSON body. The payload becomes the AMQP message
**body** — exactly what `ParseTelemetry` reads via `$flow.body`.

A **normal** dairy reading (RCON-1004, 4 ± 2 °C):

```json
{"container_id":"RCON-1004","temperature_c":3.5,"humidity_pct":80,"power_status":"ON","latitude":1.29,"longitude":103.85,"event_time":"2026-09-22T10:00:00Z"}
```

A **breach** for chocolate (RCON-1007, 16 ± 2 °C — sent too warm):

```json
{"container_id":"RCON-1007","temperature_c":25.0,"humidity_pct":60,"power_status":"ON","latitude":1.29,"longitude":103.85,"event_time":"2026-09-22T10:00:05Z"}
```

Try an **unknown** container id (e.g. `RCON-9999`) to see how the lookup behaves when a container isn't registered.

---

## Reset between runs

```bash
psql -U postgres -d reefer_monitoring -f reset_data.sql
```

This truncates `reefer_alerts` (resetting `alert_id` to 1) and re-seeds the 7 reference containers.
To purge messages spooled on the topic endpoint, delete and recreate `reefer-telemetry-sub` in
PubSub+ Manager (or use its **Clear Messages** action).

> **Broker config persistence:** it lives in the container's writable layer. `docker stop solace` /
> `docker start solace` **keeps** the auth, client-username and topic endpoint from setup steps 1–3.
> `docker rm` (or `docker run` a fresh container) **wipes** them — you'll hit the `ANONYMOUS` error and an
> empty endpoint again, so re-run steps 1–3.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| **App B: `no supported auth mechanism ([ANONYMOUS])` on startup** | The `default` VPN's basic-auth type is `none`, so the broker only offers ANONYMOUS but the AMQP connector uses SASL PLAIN. Set the VPN to **internal** auth and add the `admin` client-username — **step 2**. Happens on any freshly-created container. |
| **Try Me! "Session connect failed"** | The browser client connects over **WebSocket (port 8008)**, not AMQP. Publish `8008` (and `1443` for wss) on the container — step 1. No Try Me! setting works until 8008 is mapped; the Flogo apps are unaffected (they use 5672). |
| App B logs nothing | App A not running, wrong `TelemetryTopic`, or the topic endpoint `reefer-telemetry-sub` isn't bound to `topic/reefer/telemetry` (step 3). |
| App B connects but never receives / endpoint Consumers = 0 | The durable Topic Endpoint doesn't exist, or its permission is `consume` instead of **`modify-topic`** (the bind fails silently); or `SubscriptionName` in the app doesn't match the endpoint name. Recreate per step 3 and restart App B. |
| Connection errors on startup | Broker/DB not reachable — verify `AMQP.amqp-1_0-connection.Host`/`Port` (`localhost:5672`) and `PostgreSQL.ReeferDB.Host`/`Port` (`localhost:5432`). Give Solace 30–60 s to finish starting (confirm with the health-check in step 1). |
| No rows in `reefer_alerts` | `PostgreSQL.ReeferDB.*` properties don't match your DB, or all readings happened to be normal — confirm breaches in App B's console first. |
| `topic/reefer/alerts` empty but log shows breaches | `AlertsTopic` mismatch, or your Try Me! subscriber is on the wrong topic — it must be `topic/reefer/alerts`. |
| Lookup returns nothing / enrichment blank | The `container_id` isn't in `reefer_containers` — seed it (step 4) or use a registered id. |
| Messages redelivered repeatedly | A downstream activity errored, so Client acknowledgement never reached the `Acknowledge` step — check App B's log for the failing step (the branch only acks after `LogNormal` / `LogAlert`). |
| Designer won't validate / imports look stripped | These `.flogo` files are **hand-authored for the AMQP connector**. Don't run mutating `fda` commands on them — only read-only `fda cm` is safe. Open and run them in the VSCode designer. |

---

## Positioning notes (for the workshop)

- **Not API-centric.** There are **no REST triggers** anywhere in this use case — it is pure event
  handling (AMQP in, AMQP out, database enrichment). Keeps the "event streaming agent, not integration
  API" message clean.
- **AMQP / JMS is Flogo's messaging sweet spot.** The same app pattern runs over AMQP 1.0 (Solace
  PubSub+), JMS, and TIBCO EMS — swap the connection, keep the flow. Client-acknowledgement + durable
  shared subscriptions give at-least-once delivery without any custom code.
- **Complementary to TIBCO Streaming.** Flogo handles lightweight edge ingestion, enrichment, routing,
  and protocol bridging (AMQP / JMS / EMS / Kafka). TIBCO Streaming remains the engine for
  high-throughput continuous analytics, windowing, and complex event processing. The two compose:
  Flogo agents feed and act on the streams that Streaming analyzes.
- **Footprint.** Flogo apps are config-driven and compile to small single binaries — easy to run many
  of them at the edge, in containers, or on Kubernetes, close to where the events originate.

---

## How this app relates to the Kafka variant

This use case was cloned from `Reefer_ColdChain_Monitoring_Use_Case` (Kafka) with only the messaging
layer swapped. The `ingest → enrich → detect → route/alert` logic, PostgreSQL schema, seed data, and
detection thresholds are identical, so the two make a clean side-by-side comparison of **the same event
pattern over two different brokers**.

| Concern | Kafka variant | AMQP variant (this folder) |
|---|---|---|
| Ingest | Kafka consumer trigger | AMQP Receive Message trigger (durable shared subscription) |
| Publish | Kafka producer | AMQP Send Message (persistent) |
| Delivery guarantee | consumer group + offsets | Client acknowledgement (AMQP Acknowledge) |
| Message metadata | Kafka key / headers | AMQP message + user properties |
| Enrichment / audit | PostgreSQL | PostgreSQL (unchanged) |
