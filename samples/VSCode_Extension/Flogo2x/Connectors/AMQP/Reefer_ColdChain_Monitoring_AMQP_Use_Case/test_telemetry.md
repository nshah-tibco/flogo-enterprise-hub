# Reefer Cold-Chain Monitoring (AMQP) — Tester's Guide

End-to-end walk-through for running the two Flogo apps, watching alerts flow through
an **AMQP 1.0 broker (Solace PubSub+)**, and verifying the PostgreSQL audit trail.
Everything here uses **demo data only** — no live systems.

> Tool paths, DB credentials, and broker addresses come from
> `skills-library/.claude/skills/config.md`. The commands below assume the defaults
> (AMQP `localhost:5672`, PostgreSQL `localhost:5432` user `postgres`, database
> `reefer_monitoring`). Adjust to your environment or override the app properties.

---

## 0. What you're testing

```
ReeferTelemetryPublisher_AMQP ──► AMQP topic topic/reefer/telemetry ──► ReeferMonitorProcessor_AMQP
   (App A, producer)                                                  (App B, consumer)
                                                                            │
                                        enrich against reefer_containers (PostgreSQL)
                                                                            │
                                        normal ──► log ──► Acknowledge
                                        breach ──► AMQP topic topic/reefer/alerts
                                                   + INSERT into reefer_alerts (audit)
                                                   ──► Acknowledge
```

App A publishes **5 readings every 10 s**. Three of them are engineered to breach so
you see the alert path on every tick. The consumer runs in **Client acknowledgement
mode**, so each message is explicitly acknowledged only after it is fully processed.

---

## 1. Prerequisites

- An **AMQP 1.0 broker** running and reachable at `localhost:5672`. This guide uses
  **Solace PubSub+ Standard** in Docker.
- PostgreSQL running at `localhost:5432`.
- The two Flogo apps opened in the Flogo VSCode designer (or built with the Flogo
  build CLI — see `config.md`; do not build binaries unless you need to).
- `psql` on your PATH.

---

## 2. Start the Solace PubSub+ broker

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
| 8008 | Web messaging (SMF over WebSocket) — **required by the browser "Try Me!" client** |
| 1443 | Web messaging over TLS (wss) |
| 5672 | AMQP 1.0 (what the Flogo apps connect to) |
| 5671 | AMQP 1.0 over TLS |
| 55555 | SMF (plain TCP) |

> The browser-based **Try Me!** subscriber connects over **WebSocket on port 8008**, *not*
> AMQP/5672. If 8008 isn't published, Try Me! fails with "Session connect failed" no matter
> what you type in its connection settings. The Flogo apps are unaffected (they use 5672).

### 2a. Enable AMQP authentication (required — the apps use SASL PLAIN)

A freshly-created container leaves the `default` VPN's basic-auth type at `none`, so the broker
only offers the **ANONYMOUS** SASL mechanism. The Flogo AMQP connector authenticates with
**username/password (SASL PLAIN)**, so App B fails at startup with:

```
Failed to create engine instance ... failed to connect to AMQP 1.0 broker at
amqp://localhost:5672: no supported auth mechanism ([ANONYMOUS])
```

Switch the VPN to **internal** basic auth and add the `admin` client-username the apps connect
as. Fastest via SEMP (runs inside the container — no extra tooling, no host `curl` needed):

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

Or in **PubSub+ Manager**: Access Control → **Client Authentication** → Basic = **Internal**;
then Access Control → **Client Usernames** → **+ Client Username** → `admin` / password `admin`
/ **Enabled**.

> This config lives inside the broker. A `docker rm` (not a plain `docker stop`/`start`) wipes
> it and you'll hit the ANONYMOUS error again — just re-run the two commands above.

Wait ~30–60 s for the broker to come up, then open **PubSub+ Manager** at
<http://localhost:8080> (login `admin` / `admin`). The apps connect to the default
message VPN (`default`) with user `admin` / `admin` on the `default` VPN — matching
the `AMQP.amqp-1_0-connection.*` app properties.

---

## 3. Create the durable Topic Endpoint for the subscription

App B uses a **durable shared subscription** named `reefer-telemetry-sub`. On Solace
that maps to a **Topic Endpoint**. Create it once:

1. PubSub+ Manager → your VPN (`default`) → **Queues & Topic Endpoints** →
   **Topic Endpoints** → **+ Topic Endpoint**.
2. Name: **`reefer-telemetry-sub`**. Create it.
3. Open it → **Settings** → set **Access Type = Non-Exclusive** (enables the shared
   subscription / multiple consumers), **Owner**/permissions to allow consume, and
   set the **Topic** it attaches to = **`topic/reefer/telemetry`**. Enable it.

> If you prefer, enable **"Create durable endpoints on demand"** on the client profile
> and the AMQP client will provision the endpoint automatically on first connect — but
> creating it explicitly is the reliable path for a workshop.

The alerts topic `topic/reefer/alerts` needs **no** endpoint — you'll observe it with a
direct subscription in step 6.

---

## 4. Create the database

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

## 5. Start the consumer/processor first (App B)

Open [ReeferMonitorProcessor_AMQP.flogo](ReeferMonitorProcessor_AMQP.flogo) in the designer and
**Run**. Starting it first binds the durable subscription `reefer-telemetry-sub` to the
topic endpoint before any telemetry arrives (durable → it will also drain messages that
queued on the endpoint before the consumer connected).

Watch the app's console. Once telemetry starts flowing you'll see one log line per
reading, tagged `[REEFER NORMAL]` or `[REEFER BREACH]`, each followed by an AMQP
acknowledge.

---

## 6. Subscribe to the alerts topic

In PubSub+ Manager open **Try Me!** (top-right). In the **Subscriber** pane set the
topic to **`topic/reefer/alerts`** and click **Subscribe**. Leave it open — the enriched
breach events the processor republishes will stream in here.

Each breach message carries an enriched JSON payload (container id, cargo, customer,
destination, priority, temperature, set-point, upper/lower limits, power status, event
time), plus AMQP **user properties** `container_id` and `priority`. You should see 3 new
messages every 10 s once App A is running.

---

## 7. Start the producer (App A)

Open [ReeferTelemetryPublisher_AMQP.flogo](ReeferTelemetryPublisher_AMQP.flogo) and **Run**.
Every 10 s it publishes 5 readings to `topic/reefer/telemetry`. Expected per tick:

| Container | Cargo | Reading | Power | Set-point ± tol | Outcome |
|---|---|---|---|---|---|
| RCON-1001 | Pharma-Vaccines | −20.1 °C | ON | −20 ± 2 | **NORMAL** |
| RCON-1002 | Frozen Seafood | −8.0 °C | ON | −18 ± 3 | **BREACH** — too warm |
| RCON-1003 | Fresh Produce | 13.2 °C | OFF | 13 ± 1 | **BREACH** — power off |
| RCON-1004 | Dairy | 4.2 °C | ON | 4 ± 2 | **NORMAL** |
| RCON-1005 | Pharma-Insulin | 9.3 °C | ON | 5 ± 1 | **BREACH** — too warm (HIGH priority) |

So each tick produces **3 breaches** (RCON-1002, 1003, 1005) and **2 normals**. Watch
the breaches arrive in the Try Me! subscriber from step 6.

---

## 8. Verify the audit trail

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

## 9. (Optional) Publish your own reading manually

You don't need App A to exercise the processor — publish any reading straight to
`topic/reefer/telemetry`. Use the **Try Me!** **Publisher** pane in PubSub+ Manager:
set the topic to `topic/reefer/telemetry` and paste a JSON body.

A **normal** dairy reading (RCON-1004, 4 ± 2 °C):

```json
{"container_id":"RCON-1004","temperature_c":3.5,"humidity_pct":80,"power_status":"ON","latitude":1.29,"longitude":103.85,"event_time":"2026-09-16T10:00:00Z"}
```

…or a **breach** for chocolate (RCON-1007, 16 ± 2 °C — send it too warm):

```json
{"container_id":"RCON-1007","temperature_c":25.0,"humidity_pct":60,"power_status":"ON","latitude":1.29,"longitude":103.85,"event_time":"2026-09-16T10:00:05Z"}
```

Watch App B's log, the `topic/reefer/alerts` subscriber, and `reefer_alerts` react to
your input. Try an **unknown** container id (e.g. `RCON-9999`) to see how the lookup
behaves when a container isn't registered.

> The Try Me! publisher sends a message whose payload becomes the AMQP message **body** —
> exactly what `ParseTelemetry` reads via `$flow.body`. Make sure the endpoint from
> step 3 is subscribed to `topic/reefer/telemetry` so durable delivery reaches App B.

---

## 10. Reset between runs

To clear the audit trail and restore the reference fleet to its seeded state without
recreating the tables:

```bash
psql -U postgres -d reefer_monitoring -f reset_data.sql
```

This truncates `reefer_alerts` (resetting `alert_id` to 1) and upserts the 7 reference
containers back to their known-good values.

To purge any messages spooled on the topic endpoint between runs, delete and recreate
`reefer-telemetry-sub` in PubSub+ Manager (or use its **Clear Messages** action).

---

## 11. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| App B logs nothing | Producer not running, wrong `TelemetryTopic`, or the topic endpoint `reefer-telemetry-sub` isn't subscribed to `topic/reefer/telemetry` — check step 3 and that App A is publishing. |
| App B connects but never receives | The durable Topic Endpoint doesn't exist or has no subscription to `topic/reefer/telemetry`; or the subscription name in the app (`SubscriptionName`) doesn't match the endpoint name. |
| No rows in `reefer_alerts` | DB connection settings (`PostgreSQL.ReeferDB.*` properties) don't match your PostgreSQL, or all readings happen to be normal — confirm with the Try Me! telemetry subscriber. |
| `topic/reefer/alerts` empty but log shows breaches | `AlertsTopic` property mismatch, or your Try Me! subscriber is on the wrong topic — it must be `topic/reefer/alerts`. |
| Lookup returns nothing / enrichment blank | The `container_id` isn't in `reefer_containers` — seed it or use a registered id. |
| Connection errors on startup | Broker/DB not reachable at the configured host:port — verify `AMQP.amqp-1_0-connection.Host`/`Port` (default `localhost:5672`) and `PostgreSQL.ReeferDB.Host`/`Port` against `config.md`. |
| Messages redelivered repeatedly | Client acknowledgement never reached the `Acknowledge` activity (a downstream activity errored) — check App B's log for the failing step; the branch only acks after `LogNormal` / `LogAlert`. |
| **Try Me!** "Session connect failed" / connection error | The browser client connects over **WebSocket (port 8008)**, not AMQP. Publish port `8008` (and `1443` for wss) on the container — see step 2. No Try Me! setting works until 8008 is mapped. The Flogo apps still work (they use 5672). |
| App B: `no supported auth mechanism ([ANONYMOUS])` on startup | The `default` VPN's basic-auth type is `none`, so the broker only offers ANONYMOUS but the AMQP connector uses SASL PLAIN. Set the VPN to **internal** auth and add the `admin` client-username — see step **2a**. Happens on any freshly-created container. |
