# Reefer Cold-Chain Monitoring — Tester's Guide

End-to-end walk-through for running the two Flogo apps, watching alerts flow through
Kafka, and verifying the PostgreSQL audit trail. Everything here uses **demo data
only** — no live systems.

> Tool paths, DB credentials, and broker addresses come from
> `skills-library/.claude/skills/config.md`. The commands below assume the defaults
> (`localhost:9092`, PostgreSQL `localhost:5432` user `postgres`, database
> `reefer_monitoring`). Adjust to your environment or override the app properties.

---

## 0. What you're testing

```
ReeferTelemetryPublisher ──► Kafka topic reefer.telemetry ──► ReeferMonitorProcessor
   (App A, producer)                                              (App B, consumer)
                                                                       │
                                        enrich against reefer_containers (PostgreSQL)
                                                                       │
                                        normal ──► log only
                                        breach ──► Kafka topic reefer.alerts
                                                   + INSERT into reefer_alerts (audit)
```

App A publishes **5 readings every 10 s**. Three of them are engineered to breach so
you see the alert path on every tick.

---

## 1. Prerequisites

- Kafka broker running and reachable at `localhost:9092`.
- PostgreSQL running at `localhost:5432`.
- The two Flogo apps opened in the Flogo VSCode designer (or built with the Flogo
  build CLI — see `config.md`; do not build binaries unless you need to).
- `psql` and the Kafka console scripts (`kafka-console-consumer.sh`,
  `kafka-console-producer.sh`, `kafka-topics.sh`) on your PATH.

---

## 2. Create the database

```bash
createdb -U postgres reefer_monitoring
psql -U postgres -d reefer_monitoring -f database.sql
```

Verify the reference fleet loaded:

```bash
psql -U postgres -d reefer_monitoring -c "SELECT container_id, cargo_type, set_point_c, allowed_deviation_c, priority FROM reefer_containers ORDER BY container_id;"
```

You should see 7 containers (RCON-1001 … RCON-1007). The audit table starts empty:

```bash
psql -U postgres -d reefer_monitoring -c "SELECT count(*) FROM reefer_alerts;"   -- expect 0
```

---

## 3. Create the Kafka topics

Auto-create may be on; if not, create them explicitly:

```bash
kafka-topics.sh --create --if-not-exists --topic reefer.telemetry --bootstrap-server localhost:9092
kafka-topics.sh --create --if-not-exists --topic reefer.alerts    --bootstrap-server localhost:9092
kafka-topics.sh --list --bootstrap-server localhost:9092          # confirm both exist
```

---

## 4. Start the consumer/processor first (App B)

Open [ReeferMonitorProcessor.flogo](ReeferMonitorProcessor.flogo) in the designer and
**Run**. Starting it first means the consumer group `reefer-monitor` is listening
before any telemetry arrives. (The trigger uses `initialOffset: Oldest`, so it will
also pick up messages already on the topic.)

Watch the app's console. Once telemetry starts flowing you'll see one log line per
reading, tagged `[REEFER NORMAL]` or `[REEFER BREACH]`.

---

## 5. Start the producer (App A)

Open [ReeferTelemetryPublisher.flogo](ReeferTelemetryPublisher.flogo) and **Run**.
Every 10 s it publishes 5 readings to `reefer.telemetry`. Expected per tick:

| Container | Cargo | Reading | Power | Set-point ± tol | Outcome |
|---|---|---|---|---|---|
| RCON-1001 | Pharma-Vaccines | −20.1 °C | ON | −20 ± 2 | **NORMAL** |
| RCON-1002 | Frozen Seafood | −8.0 °C | ON | −18 ± 3 | **BREACH** — too warm |
| RCON-1003 | Fresh Produce | 13.2 °C | OFF | 13 ± 1 | **BREACH** — power off |
| RCON-1004 | Dairy | 4.2 °C | ON | 4 ± 2 | **NORMAL** |
| RCON-1005 | Pharma-Insulin | 9.3 °C | ON | 5 ± 1 | **BREACH** — too warm (HIGH priority) |

So each tick produces **3 breaches** (RCON-1002, 1003, 1005) and **2 normals**.

---

## 6. Watch the alerts topic

In a separate terminal, tail `reefer.alerts` to see the enriched breach events the
processor republishes:

```bash
kafka-console-consumer.sh --topic reefer.alerts --bootstrap-server localhost:9092 --property print.key=true
```

Each breach message is keyed by `container_id` and carries an enriched JSON payload
(container id, cargo, customer, destination, priority, temperature, set-point, upper/
lower limits, power status, event time). You should see 3 new messages every 10 s.

To sanity-check the raw input side, tail the telemetry topic too:

```bash
kafka-console-consumer.sh --topic reefer.telemetry --bootstrap-server localhost:9092 --property print.key=true
```

---

## 7. Verify the audit trail

Every breach is also inserted into `reefer_alerts`. After a few ticks:

```bash
psql -U postgres -d reefer_monitoring -c "SELECT alert_id, container_id, cargo_type, reported_temp_c, set_point_c, power_status, alert_reason, alerted_at FROM reefer_alerts ORDER BY alert_id DESC LIMIT 15;"
```

You should see rows for RCON-1002, RCON-1003, and RCON-1005 accumulating over time,
with `alert_reason` describing the excursion (e.g. `power=ON, temp=-8C, allowed -21 to
-15C, setpoint=-18C`). RCON-1001 and RCON-1004 never appear — they're within band.

Useful roll-up:

```bash
psql -U postgres -d reefer_monitoring -c "SELECT container_id, count(*) AS breaches, max(alerted_at) AS last_seen FROM reefer_alerts GROUP BY container_id ORDER BY breaches DESC;"
```

---

## 8. (Optional) Publish your own reading manually

You don't need App A to exercise the processor — publish any reading straight to
`reefer.telemetry`. The message value is a JSON string; the key is arbitrary.

```bash
kafka-console-producer.sh --topic reefer.telemetry --bootstrap-server localhost:9092
```

Then paste a line, e.g. a **normal** dairy reading (RCON-1004, 4 ± 2 °C):

```json
{"container_id":"RCON-1004","temperature_c":3.5,"humidity_pct":80,"power_status":"ON","latitude":1.29,"longitude":103.85,"event_time":"2026-09-16T10:00:00Z"}
```

…or a **breach** for chocolate (RCON-1007, 16 ± 2 °C — send it too warm):

```json
{"container_id":"RCON-1007","temperature_c":25.0,"humidity_pct":60,"power_status":"ON","latitude":1.29,"longitude":103.85,"event_time":"2026-09-16T10:00:05Z"}
```

Watch App B's log, the `reefer.alerts` topic, and `reefer_alerts` react to your input.
Try an **unknown** container id (e.g. `RCON-9999`) to see how the lookup behaves when a
container isn't registered.

---

## 9. Reset between runs

To clear the audit trail and restore the reference fleet to its seeded state without
recreating the tables:

```bash
psql -U postgres -d reefer_monitoring -f reset_data.sql
```

This truncates `reefer_alerts` (resetting `alert_id` to 1) and upserts the 7 reference
containers back to their known-good values.

---

## 10. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| App B logs nothing | Producer not running, wrong `TelemetryTopic`, or consumer group already advanced past the messages — check the topic name matches and that App A is publishing. |
| No rows in `reefer_alerts` | DB connection settings (`PG.*` properties) don't match your PostgreSQL, or all readings happen to be normal — confirm with the telemetry tail. |
| `reefer.alerts` empty but log shows breaches | `AlertsTopic` property mismatch, or the topic doesn't exist and auto-create is off — create it (step 3). |
| Lookup returns nothing / enrichment blank | The `container_id` isn't in `reefer_containers` — seed it or use a registered id. |
| Connection errors on startup | Broker/DB not reachable at the configured host:port — verify `Kafka.Brokers` and `PG.Host`/`PG.Port` against `config.md`. |
