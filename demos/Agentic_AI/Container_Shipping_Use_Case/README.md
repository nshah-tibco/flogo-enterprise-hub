# Maritime Container Shipping — Customer Self-Service Assistant

An **Agentic AI** demo for the **ocean / container shipping (liner)** vertical. A
**Beneficial Cargo Owner (BCO), freight forwarder, or enterprise shipper** chats with an AI
assistant over WebSocket to **look up their account, bookings, containers, live tracking,
sailing schedules, rate quotes, charges and cargo claims**, and — on confirmation — **book a
new shipment, file a cargo claim, request a booking amendment, or dispute a charge**. The
assistant looks the data up, performs the action against PostgreSQL, and confirms back in chat.

- **Persona:** Shipping customer / logistics coordinator (self-service), identified by a
  `customer_code` in the form `CUST-SHIP-100x`.
- **Problem automated:** the "where's my container / when does it sail / quote me a lane /
  break down these charges / why is my box delayed / file my claim" load that normally ties up a
  customer-service or documentation desk — resolved conversationally, grounded in live data.
- **Solution shape:** 3 Flogo apps — **1 MCP Server** (read-only tools), **1 A2A Agents app**
  (action agents that write **directly to PostgreSQL**), and **1 AI Orchestrator** (WebSocket
  chat, LLM routing). All state lives in **PostgreSQL**. Currency is **USD** throughout, and
  ports use **UN/LOCODE** (e.g. `CNSHA` = Shanghai, `USLAX` = Los Angeles).

---

## ⚠️ Build status — read this first

This folder is a **work in progress**. Only two of the three apps are fully converted to the
container-shipping domain:

| File | State |
|------|-------|
| `ContainerShippingMCPServer.flogo` | ✅ **Container shipping** (app `ContainerShippingMCPServer`, 8 tools, DB `container_shipping`) |
| `database.sql` / `reset_data.sql` | ✅ **Container shipping** schema + seed data |
| `ContainerShippingA2AServers.flogo` | ❌ **Stale copy** — the app inside is still `LifePensionsA2AServers` (beneficiary / contribution / fund-switch / claim / adviser-callback / email agents). It does **not** yet implement the container-shipping write agents. |
| `ContainerShippingAIOrchestrator.flogo` | ❌ **Stale copy** — the app inside is still `LifePensionsAIOrchestrator` (Life & Pensions system prompt, WS path `/lifepensions`, and MCP `serverUrl` pointing at `:9982/life-pensions` instead of the real MCP at `:9720/shipping-bss`). |

The MCP read side and the database run end-to-end today. The **A2A Agents app and the
Orchestrator must be rebuilt for this domain** (new system prompt, new write flows, matching
ports/URLs) before the full chat demo works. The intended container-shipping write agents are
described below and are driven by `database.sql` (which explicitly names them).

---

## Architecture

```
Chatbot UI --WebSocket--> AI Orchestrator --MCP (HTTP streamable)--> MCP Server --\
                                 |                                                 +--> PostgreSQL
                                 \-----------A2A (HTTP)-----> A2A Agents ----------/
```

- **MCP Server** — read-only lookups. Stateless, safe to retry; the LLM picks a tool from its
  description and filters the returned rows (by `customer_code`, `booking_ref`, `container_no`, lane, etc.).
- **A2A Agents** — action workflows. Each agent has its own trigger/port, guardrails, and system
  prompt, and **writes directly to PostgreSQL** (validate with a `SELECT`, then INSERT).
- **Orchestrator** — the AI brain. WebSocket chat endpoint; the LLM decides intent and either
  calls an MCP tool or hands off to an A2A agent.

---

## Apps / Components

| App | File | Trigger | Port (property) + path |
|-----|------|---------|------------------------|
| MCP Server | `ContainerShippingMCPServer.flogo` | `#mcpserver` | `MCP_SERVER_PORT` = **9720**, path `/shipping-bss` |
| A2A Agents | `ContainerShippingA2AServers.flogo` | `#agent` ×N | see agent table (⚠️ currently stale ports **9983–9988**) |
| AI Orchestrator | `ContainerShippingAIOrchestrator.flogo` | `#wsserver` | **9600** (⚠️ shipped path `/lifepensions`; should be a container-shipping path) |

---

## MCP tools (read-only)

All served by `ContainerShippingMCPServer.flogo`. Each tool runs a `SELECT` (some join `ports`,
`vessels`, `container_types`) and returns rows; the LLM filters/joins by customer, booking, or
container.

| Tool | Table / source | What it answers |
|------|----------------|-----------------|
| `GetCustomerProfile` | `customers` | Who the customer is: company, account type (BCO / Forwarder / Enterprise), loyalty tier, contact, country, credit terms |
| `GetBookings` | `bookings` | Booking headers: ref, lane (origin/destination UN/LOCODE), container type, quantity, cargo, amount, status, date |
| `GetContainers` | `containers` | Containers on a booking: container no, seal, type, status, current location, gross weight |
| `TrackContainer` | `tracking_events` | Scan-by-scan movement history for a container (Gate In → Loaded → Departed → Arrived → Discharged → Delivered / Hold) |
| `GetVesselSchedule` | `voyages` ⋈ `vessels`, `ports` | Sailing schedule: voyage, service, vessel, origin/destination names, ETD, ETA, transit days, status |
| `GetRates` | `rates` ⋈ `container_types`, `ports` | Ocean freight rate card: base rate (USD) per lane + container type, transit days, validity |
| `GetCharges` | `charges` | Charge breakdown per booking: Freight / Demurrage / Detention / BAF / THC, free days vs days used, status |
| `GetClaims` | `claims` | Cargo claim status: type (Damage / Loss / Shortage), amount, status, filed date (most recent first) |

---

## A2A action agents (writes / actions)

> ⚠️ **These are the intended container-shipping write agents**, derived from the target tables and
> agent names declared in `database.sql`. The shipped `ContainerShippingA2AServers.flogo` does **not**
> implement them yet — it still contains the Life & Pensions agents (see Build status above). Ports
> below are **to be assigned** when the app is rebuilt; the file currently ships placeholder ports
> **9983–9988** bound to the old Life & Pensions agents.

| Agent (intended) | Action | Writes to |
|------------------|--------|-----------|
| `book_shipment` | Book a new shipment on a voyage (auto-generates `BKG-<year>-01NN` via `booking_seq`) | INSERT `bookings` |
| `file_claim` | File a cargo claim (Damage / Loss / Shortage) against a booking | INSERT `claims` |
| `amend_booking` | Request a booking amendment (field change, reason; status `Requested`) | INSERT `booking_amendments` |
| `dispute_charge` | Dispute a charge (e.g. demurrage/detention) with a reason and amount (status `Open`) | INSERT `charge_disputes` |

**Currently shipped (stale, Life & Pensions):** `update_beneficiary_agent` (9983), `change_contribution_agent`
(9984), `fund_switch_agent` (9985), `submit_claim_agent` (9986), `adviser_callback_agent` (9987),
`send_confirmation_email` (9988, SMTP via `Email_App_Password`). Replace these when rebuilding for
this domain.

---

## Database

PostgreSQL (14+). Database name: **`container_shipping`**. `database.sql` creates the schema and
seeds demo data; `reset_data.sql` truncates everything, re-seeds the read tables + the one
pre-seeded claim, and leaves the agent-written tables empty. Volatile dates are
**`CURRENT_DATE`-relative**, so schedules, ETDs/ETAs and tracking always look current. All money is **USD**.

**Read / reference tables (seeded):** `customers` (6), `ports` (10), `vessels` (5),
`container_types` (4), `voyages` (8), `rates` (8), `bookings` (8), `containers` (10),
`tracking_events` (22), `charges` (10).

**Agent-written tables:** `claims` (1 pre-seeded baseline), `booking_amendments` (starts **empty**),
`charge_disputes` (starts **empty**). A `booking_seq` sequence generates refs for agent-created bookings.

Load / reset:

```bash
# create + load:
psql -h <host> -p <port> -U <db-user> -d container_shipping -f database.sql
# between demos:
psql -h <host> -p <port> -U <db-user> -d container_shipping -f reset_data.sql
```

Flagship demo data hooks:
- **`CUST-SHIP-1001` (Pacific Traders Inc**, US / BCO / Gold, contact Sarah Chen) — the flagship
  customer, with several bookings including the delayed `BKG-2026-0007`.
- **`MSKU7000001` on `BKG-2026-0007`** — **weather-held at the Singapore (`SGSIN`) transshipment hub**
  → drives the "where is my container / why is it delayed" tracking demo.
- **`CHG-1008`** — a **demurrage** charge on `BKG-2026-0007` with **5 free days but 8 used** → the
  natural candidate for the dispute-charge demo.
- **`BKG-2026-0002` shortage claim** (`CUST-SHIP-1002`, Global Spice Co, "Under Review") — the
  pre-seeded claim so `GetClaims` shows data.
- **Rate `CNSHA → USLAX`, `40HC` = $2,500** (`RATE-003`) → drives lane/rate quote demos.

---

## Demo scenarios

Prompts are copy-pasteable; start every session by identifying yourself. (Read scenarios work
today against the MCP server; write scenarios require the rebuilt A2A Agents app + Orchestrator.)

1. **Identify the customer.** "I'm CUST-SHIP-1001." → `GetCustomerProfile`.
2. **List bookings.** "Show my bookings and their status." → `GetBookings`.
3. **Booking detail + containers.** "What containers are on BKG-2026-0003 and where are they?" → `GetBookings` + `GetContainers`.
4. **⭐ Track a container.** "Where is container MSKU7000001 and why is it delayed?" → `TrackContainer` (held at SGSIN, severe-weather delay).
5. **Sailing schedule.** "When does VOY-501 depart Shanghai and arrive in Los Angeles?" → `GetVesselSchedule`.
6. **Rate quote.** "Quote me a 40HC from Shanghai (CNSHA) to Los Angeles (USLAX)." → `GetRates` (base rate $2,500).
7. **Charge breakdown.** "Break down the charges on BKG-2026-0007." → `GetCharges` (freight + demurrage; 5 free days vs 8 used).
8. **Claim status.** "What's the status of my cargo claim?" (as CUST-SHIP-1002) → `GetClaims`.
9. **Book a shipment** *(write)*. "Book 2×40HC Shanghai→LA on VOY-501 for CUST-SHIP-1001, cargo Furniture." → `book_shipment`.
10. **File a claim** *(write)*. "File a Damage claim on BKG-2026-0001 for $1,200 — pallets crushed." → `file_claim`.
11. **Amend a booking** *(write)*. "Change the quantity on BKG-2026-0003 from 3 to 4 containers." → `amend_booking`.
12. **Dispute a charge** *(write)*. "Dispute the demurrage charge CHG-1008 on BKG-2026-0007 — the delay was carrier-caused." → `dispute_charge`.

---

## Prerequisites

- **PostgreSQL** (14+) running; a database named **`container_shipping`** created for this demo.
- **TIBCO Flogo Enterprise** (import the `.flogo` apps into the designer) — or the `flogobuild` CLI
  if you prefer to build `.exe`s. CLI paths / versions / contexts live in
  `skills-library/.claude/skills/config.md`.
- An **LLM provider** key (OpenAI-compatible). The base URL must be a **real endpoint**, e.g.
  `https://api.openai.com/v1`.
- **SMTP** access **only if** you keep/rebuild an email-confirmation agent (Gmail:
  `smtp.gmail.com:465`, SSL, an app-specific password).
- A **chatbot / WebSocket UI** — the shared one under `demos/Agentic_AI/Chatbot`, or any WS test client.

---

## Setup & Run

1. **Database** — create `container_shipping` and load the schema/data:
   ```bash
   psql -h <host> -p <port> -U <db-user> -d container_shipping -f database.sql
   ```
   Use `reset_data.sql` to restore a clean state between demos.
2. **Import / build the three apps** into Flogo Enterprise (or build each to an `.exe` with `flogobuild`).
   The MCP Server is ready; **rebuild the A2A Agents app and the Orchestrator for this domain** first
   (see Build status).
3. **Set app properties** — PostgreSQL `Host` / `Port` / `Database_Name` / `User` / `Password`;
   LLM `API_Key` / `LLM_Base_URL` / `LLM_Model`; the MCP and A2A ports; SMTP creds if you keep an
   email agent. See the manual-config section below.
4. **Start order:** **MCP Server → A2A Agents → Orchestrator.**
5. **Connect a WebSocket client** to `ws://<host>:<wsPort>/<path>` (as shipped that is
   `ws://<host>:9600/lifepensions` — rename the path when you rebuild the Orchestrator) and start chatting.

---

## Ports

| Component | Property | Value (as shipped) | Notes |
|-----------|----------|--------------------|-------|
| MCP Server | `MCP_SERVER_PORT` | **9720** (path `/shipping-bss`) | ✅ container shipping |
| Orchestrator (WebSocket) | `#wsserver` trigger port | **9600** (path `/lifepensions`) | ⚠️ stale path; MCP `serverUrl` points at `:9982/life-pensions` (wrong — should be `:9720/shipping-bss`) |
| A2A agent 1 | `UpdateBeneficiary_A2AServer_PORT` | 9983 | ⚠️ stale (Life & Pensions) — reassign for `book_shipment` |
| A2A agent 2 | `ChangeContribution_A2AServer_PORT` | 9984 | ⚠️ stale — reassign for `file_claim` |
| A2A agent 3 | `FundSwitch_A2AServer_PORT` | 9985 | ⚠️ stale — reassign for `amend_booking` |
| A2A agent 4 | `SubmitClaim_A2AServer_PORT` | 9986 | ⚠️ stale — reassign for `dispute_charge` |
| A2A agent 5 | `AdviserCallback_A2AServer_PORT` | 9987 | ⚠️ stale (no equivalent unless you add one) |
| A2A agent 6 | `SendEmail_A2AServer_PORT` | 9988 | ⚠️ stale (optional email agent) |

---

## Troubleshooting

- **Orchestrator/A2A agents are for the wrong domain** — the shipped `ContainerShippingA2AServers.flogo`
  and `ContainerShippingAIOrchestrator.flogo` are Life & Pensions copies. Rebuild them (system prompt,
  write flows, ports, MCP/A2A `serverUrl`s) before running the full demo (see Build status).
- **`unsupported protocol scheme` / posts to `/New_value/...`** — the LLM base URL is blank; set it to a real endpoint.
- **MCP runtime panics `missing input schema`** — a tool handler is missing its input/output schema;
  **Sync** the MCP trigger in the designer.
- **A2A `missing substitution for: <name>`** on a write — the runtime `input.mapping.parameters` is
  missing that param; patch it, then **Sync** the trigger to regenerate the design-time schemas.
- **`Configured connection is not a WebSocket Connection`** — the orchestrator's `wsconnection` /
  `content` inputs were coerced to `object`; they must stay type **`any`**.
- **Email field warns "type … differs from bound app property"** — if you keep an email agent, re-enter
  `Email_App_Password` in App Properties so it is stored as a `SECRET:` (keep the property type `string`).
- **Orchestrator can't reach a tool/agent** — each MCP/A2A `serverUrl` must match the MCP/A2A ports
  above. As shipped, the orchestrator's MCP URL (`:9982`) does **not** match the MCP server (`:9720`).

---

## ⚠️ Below things are NOT configured — please configure them manually before running end to end

The committed `.flogo` files carry placeholders / reference-app values for every secret; replace them
with your own before an end-to-end run. Never commit real secrets.

1. **Domain rebuild (biggest gap).**
   - Rebuild `ContainerShippingA2AServers.flogo` with the four container-shipping write agents
     (`book_shipment`, `file_claim`, `amend_booking`, `dispute_charge`) writing to `bookings`,
     `claims`, `booking_amendments`, `charge_disputes` respectively.
   - Rebuild `ContainerShippingAIOrchestrator.flogo` with a container-shipping system prompt, a
     container-shipping WS path, the MCP `serverUrl` pointing at `:9720/shipping-bss`, and A2A
     `serverUrl`s matching the rebuilt agent ports.

2. **LLM credentials & endpoint.**
   - `AgenticAI.OpenAIConn.API_Key` — set your real provider key (inject as an app property / platform secret).
   - `AgenticAI.OpenAIConn.LLM_Base_URL` — a **real endpoint** (`https://api.openai.com/v1`). An empty
     value becomes the literal `New_value` and the LLM call fails with `unsupported protocol scheme`.
   - `LLM_Model` — confirm the model name is one your key can access.

3. **PostgreSQL database & credentials.**
   - Create the **`container_shipping`** database and load `database.sql`; run `reset_data.sql` to reset between demos.
   - Set the PostgreSQL connection `Host` / `Port` / `Database_Name` / `User` / `Password` to your
     instance. `Password` is a `SECRET:` app property — set the real secret in App Properties, not in plaintext.
   - Verify connectivity: run each MCP tool's `SELECT` and each A2A write's SQL against the DB.

4. **Ports must be free & consistent.**
   - MCP **9720** and the orchestrator WebSocket **9600** must be free on the host, plus a port per
     A2A agent. The orchestrator's MCP `serverUrl` and each A2A `serverUrl` must match those ports.
   - If you change a port, change it in the app property **and** in the corresponding orchestrator connection URL.

5. **Email / SMTP** (only if you keep an email-confirmation agent).
   - Set `Email_Username`, `Email_App_Password` (an app-specific password, **not** the account password),
     and the recipient property. Confirm outbound SMTP (`smtp.gmail.com:465`, SSL) is allowed from the host.
   - **Re-enter `Email_App_Password` in App Properties so it is stored as a `SECRET:` value** (leave the
     property type as `string`).

6. **Chatbot / WebSocket client.**
   - Point the shared UI (`demos/Agentic_AI/Chatbot`) or a WS test client at
     `ws://<host>:<wsPort>/<path>`.

7. **Flogo designer manual steps** (clear design-time validation after import).
   - **Sync every trigger** (MCP, each A2A agent, the WS server) once, so `toolParams` and WS input
     mappings render without a red ✗.
   - **Validate every connection** (PostgreSQL, LLM provider, MCP server config, all A2A server
     connections) — click **Connect / Test** before running.

**Quick pre-flight checklist**

- [ ] A2A Agents app + Orchestrator **rebuilt for container shipping** (not the stale Life & Pensions copies)
- [ ] DB `container_shipping` created, `database.sql` loaded, row counts sane (customers 6, bookings 8, containers 10, rates 8, tracking_events 22)
- [ ] LLM `API_Key`, `LLM_Base_URL` (real endpoint), `LLM_Model` set
- [ ] PostgreSQL `Password` set; MCP tool `SELECT`s and A2A write SQL run cleanly
- [ ] All ports free; orchestrator MCP `serverUrl` = `:9720/shipping-bss` and A2A URLs match the agent ports
- [ ] (If used) `Email_App_Password` re-entered as a `SECRET:` (type stays `string`); SMTP reachable
- [ ] Every trigger Synced; every connection validated in the designer
- [ ] Start order: MCP → A2A → Orchestrator; each logs a clean start
- [ ] WebSocket client connects to `ws://<host>:<wsPort>/<path>` and gets a reply
