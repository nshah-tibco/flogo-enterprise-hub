# Residential Water Utility — Customer Self-Service Use Case

> ## ⚠️ Artifacts not included in this folder
> This folder currently contains **only this README**. The Flogo apps
> (`WaterUtilityMCPServer.flogo`, `WaterUtilityA2AServers.flogo`,
> `WaterUtilityAIOrchestrator.flogo`), the `database.sql` / `reset_data.sql`
> scripts, and `prompts.md` referenced below are **not present** — this guide
> documents the *intended* design, so the demo **cannot be run as-is**. To make
> it runnable, generate the three apps + SQL + prompts with the
> `agentic-ai-use-case` skill (or copy and adapt them from a complete use case
> such as `Semiconductor_Customer_Use_Case`) before following **Setup & Run**.

An AI-powered self-service assistant for a residential **water utility** (aqueduct, sewerage &
purification services), built on TIBCO Flogo Enterprise. Customers chat in natural language
("Why is my water bill so high?", "I think I have a leak", "Let me send my own meter reading",
"Is the water safe to drink in my area?", "Can I pay this in installments?") over a WebSocket
streaming chat. The system uses a 3-tier agentic architecture — an AI Orchestrator, an MCP Server
for read-only billing / meter / network lookups, and A2A Servers for write workflows (service
requests, self meter readings, payment plans & disputes, and email) — all communicating via standard
protocols (MCP, A2A, WebSocket).

> **Demo dataset:** a residential water utility — currency **EUR**, VAT (**IVA**) **10 %** on water
> services, tiered volumetric tariff (Agevolata → Base → Eccedenza), consumption in **cubic metres
> (m³)**. Customers are identified by contract/account number (`WTR-XXXXXXXX`), the phone on file
> (`+39 320 555 01XX`), or their service address. 18 accounts span four residential tariff plans
> (Base, Social/Water-Bonus, Large-Household, Non-Resident/Second-Home) across Rome-area service
> zones, with pre-seeded service interruptions, water-quality reports, a leak service request and a
> payment plan for status demos.

---

## Architecture Overview

```
                    ┌─────────────────────────┐
                    │     Chatbot UI          │
                    │  (WebSocket Client)     │
                    └───────┬─────────────────┘
                            │ WebSocket
                            │ ws://localhost:9780/water
                            ▼
               ┌────────────────────────────────┐
               │  Water Utility                 │
               │  AI Orchestrator               │
               │  (WaterUtilityAIOrchestrator)  │
               │  Port 9780 (WebSocket)         │
               │  LLM: OpenAI GPT               │
               └───────┬───────────┬────────────┘
                       │           │
          MCP (HTTP)   │           │  A2A Protocol
                       ▼           ▼
    ┌──────────────────────┐   ┌──────────────────────────────────────┐
    │  Water Utility       │   │  Water Utility                       │
    │  MCP Server          │   │  A2A Servers                         │
    │  Port 9782           │   │                                      │
    │  /water-cis          │   │  service_request_agent        :9783  │
    │                      │   │  meter_reading_agent          :9784  │
    │  Tools (read-only):  │   │  billing_support_agent        :9785  │
    │  - GetCustomerAccounts│  │  send_confirmation_email      :9786  │
    │  - GetInvoiceDetails │   │                                      │
    │  - GetConsumption    │   │  Writes to PostgreSQL                │
    │  - GetMeterReadings  │   │  (service requests / meter reads /   │
    │  - GetPaymentHistory │   │   billing requests)                  │
    │  - GetTariffPlans    │   │  + Gmail SMTP for email              │
    │  - GetInterruptions  │   │                                      │
    │  - GetWaterQuality   │   │                                      │
    │  - GetServiceRequests│   │                                      │
    │  - GetBillingRequests│   │                                      │
    └──────────┬───────────┘   └──────────────┬───────────────────────┘
               │                              │
               └──────────────┬───────────────┘
                              ▼
               ┌────────────────────────────┐
               │  PostgreSQL Database       │
               │  Database: water_utility   │
               │  11 Tables                 │
               └────────────────────────────┘
```

**How it works:** the **AI Orchestrator** is the brain — a WebSocket endpoint whose AI Agent activity
classifies each message and routes it. Read questions (account, bill, consumption, meter readings,
payments, tariffs, interruptions, water quality, request/plan status) go to the **MCP Server**, which
exposes 10 read-only PostgreSQL lookup tools. Actions that change state (open a service request,
submit a self meter reading, set up a payment plan or dispute a bill, send an email) go to the **A2A
Servers**, one write agent per port.

---

## Flogo Apps

### 1. `WaterUtilityMCPServer.flogo` — MCP Server (Port 9782)

Exposes 10 read-only lookup tools via the Model Context Protocol over Streamable HTTP (endpoint
`/water-cis`). Each tool queries the PostgreSQL `water_utility` database and returns the result set as
a string; the LLM filters by account number / phone / zone.

| Tool | Description | Table / Query |
|------|-------------|---------------|
| **GetCustomerAccounts** | Account master: account #, phone, name, address, zone, meter id, contract status, tariff plan, household size | `SELECT * FROM customers` |
| **GetInvoiceDetails** | Water bill header + itemized line items (fixed charge, tiered aqueduct, sewerage, purification, social bonus, VAT) | `invoices JOIN bill_line_items` |
| **GetConsumptionRecords** | Metered m³ consumption per period: total, per-tier split, avg daily, prior-year comparison | `SELECT * FROM consumption_records` |
| **GetMeterReadings** | Meter reading history — ACTUAL / ESTIMATED / SELF (autolettura) reads with reading value + date | `SELECT * FROM meter_readings` |
| **GetPaymentHistory** | Recent payments with method, status, reference | `SELECT * FROM payments` |
| **GetTariffPlans** | Residential water tariff catalog (Base, Social/Bonus, Large-Household, Non-Resident) | `SELECT * FROM tariff_plans` |
| **GetServiceInterruptions** | Area-level water supply interruptions by zone (planned maintenance / main break), cause, status, ETA | `SELECT * FROM service_interruptions` |
| **GetWaterQualityReports** | Per-zone water quality parameters (hardness °F, chlorine, nitrates, pH, compliance) | `SELECT * FROM water_quality_reports` |
| **GetServiceRequests** | Leak / meter-fault / low-pressure / no-water / quality tickets and status | `SELECT * FROM service_requests` |
| **GetBillingRequests** | Payment plans and bill disputes and their status | `SELECT * FROM billing_requests` |

### 2. `WaterUtilityA2AServers.flogo` — A2A Servers (Ports 9783–9786)

Four A2A agents that handle write workflows. Each agent has its own LLM, system prompt, and tool
handler, and writes to PostgreSQL (the email agent sends via SMTP).

| Agent | Port | Tool | Write Workflow |
|-------|------|------|----------------|
| **service_request_agent** | 9783 | `open_service_request` | Opens a service request (LEAK, METER_FAULT, LOW_PRESSURE, NO_WATER, WATER_QUALITY) into `service_requests` (status OPEN). Derives the customer's internal id from the account number so the caller never needs it. |
| **meter_reading_agent** | 9784 | `submit_meter_reading` | Records a customer **self meter reading** (autolettura) into `meter_readings` as a SELF read. **Guardrail:** the new reading must be ≥ the last recorded reading, else it is rejected as implausible. |
| **billing_support_agent** | 9785 | `submit_billing_request` | Submits a **PAYMENT_PLAN** (installments over N months) or a **DISPUTE** (contests an invoice) into `billing_requests`. **Guardrail:** a payment plan is only offered when there is an outstanding/overdue amount; a dispute must reference a real invoice. |
| **send_confirmation_email** | 9786 | `send_confirmation_email` | Sends a confirmation email (service request / meter reading / payment plan / dispute) via Gmail SMTP. Invoked only once, **after** the action, when the customer requests it. |

### 3. `WaterUtilityAIOrchestrator.flogo` — AI Orchestrator (Port 9780)

The main orchestration app. Exposes a WebSocket endpoint for natural-language chat. An AI Agent
activity classifies intent and routes to either MCP tools (data lookups) or A2A agents (write
workflows).

| Setting | Value |
|---------|-------|
| WebSocket Port | `9780` |
| WebSocket Path | `/water` |
| Connect URL | `ws://localhost:9780/water` |
| LLM | OpenAI GPT |
| MCP Server | `http://localhost:9782/water-cis` |
| A2A Agents | service_request (9783), meter_reading (9784), billing_support (9785), email (9786) |

---

## Database

11 tables in the PostgreSQL `water_utility` database:

| Table | Purpose | Records |
|-------|---------|---------|
| `tariff_plans` | Residential water tariff catalog (Base, Social/Bonus, Large-Household, Non-Resident) | 4 plans |
| `customers` | Account master — one contract = one service point / meter | 18 accounts |
| `invoices` | Water bill headers (current period) | 18 invoices |
| `bill_line_items` | Itemized charges per invoice (fixed, tiered aqueduct, sewerage, purification, bonus, VAT) | 80+ line items |
| `consumption_records` | Metered m³ consumption vs prior year, per tier | 18 (one per account) |
| `meter_readings` | Reading history — ACTUAL / ESTIMATED / SELF (**appended by** meter_reading_agent) | ~40 pre-seeded |
| `payments` | Payment history | ~34 payments |
| `service_interruptions` | Area-level supply interruptions by zone | 3 interruptions |
| `water_quality_reports` | Per-zone water quality parameters | 8 zones |
| `service_requests` | Leak / meter / pressure / quality tickets (**written by** service_request_agent) | 1 pre-seeded |
| `billing_requests` | Payment plans & disputes (**written by** billing_support_agent) | 1 pre-seeded |

```bash
# Initialize schema and demo data
psql -U postgres -d water_utility -f database.sql

# Reset to a clean demo state (today-relative dates; clears agent-written rows)
psql -U postgres -d water_utility -f reset_data.sql
```

---

## Demo Personas

Residents identified by account number (`WTR-300100XX`), phone (`+39 320 555 01XX`), or service
address. Currency **EUR**; consumption in **m³**.

| Account ID | Name | Zone (CAP) | Tariff | Demo role |
|------------|------|------------|--------|-----------|
| WTR-30010001 | Giulia Ricci | Aurelio (00165) | Base | **Flagship** — "Why is my bill so high?" 78 m³ vs 30 m³ prior year → suspected hidden leak; open a leak request; set up a payment plan; email confirmation |
| WTR-30010002 | Marco Bianchi | Trastevere (00153) | Large-Household | Family of 5 — extended tier-1 allowance explanation |
| WTR-30010003 | Sofia Russo | EUR (00144) | Social/Bonus | Water Bonus (Bonus Sociale Idrico) credit on the bill |
| WTR-30010004 | Luca Esposito | Ostia (00121) | Non-Resident | Second home — higher rate, no tier-1 subsidy |
| WTR-30010005 | Elena Romano | Prati (00192) | Base | ESTIMATED reading → prompted to submit a self-reading (autolettura) |
| WTR-30010006 | Giovanni Colombo | Monteverde (00152) | Base | Outstanding overdue balance → payment plan candidate |
| WTR-30010007 | Chiara Ferrari | Testaccio (00153) | Base | Wants to dispute a bill (charge looks wrong for a low-usage month) |
| WTR-30010008 | Alessandro Marino | Prati (00192) | Base | In a PLANNED maintenance interruption zone |
| WTR-30010009 | Francesca Greco | Monteverde (00152) | Base | In an unplanned MAIN_BREAK zone (RESTORING) |
| WTR-30010010 | Matteo Bruno | Nomentano (00162) | Base | Water quality question (hardness / chlorine) |
| WTR-30010011 | Valentina Gallo | Tiburtino (00159) | Base | Pre-seeded leak request SRQ-2026-0001 (IN_PROGRESS) |
| WTR-30010012 | Davide Conti | Appio (00183) | Base | Pre-seeded payment plan BRQ-2026-0001 (ACTIVE, 6 installments) |
| WTR-30010013 | Martina De Luca | Flaminio (00196) | Base | Clean bill / general |
| WTR-30010014 | Andrea Mancini | Garbatella (00154) | Base | Rich self-reading history (autolettura) |
| WTR-30010015 | Silvia Rizzo | Trieste (00198) | Large-Household | High consumption but explained (large family, not a leak) |
| WTR-30010016 | Paolo Costa | Marconi (00146) | Base | Meter fault (readings frozen) → meter-check request |
| WTR-30010017 | Laura Fontana | Pigneto (00176) | Base | Low-pressure complaint → service request |
| WTR-30010018 | Roberto Moretti | Aurelio (00165) | Base | General |

### Flagship Bill — Giulia Ricci (INV-2026-06-0001)

| Line item | Category | Amount (EUR) |
|-----------|----------|--------------|
| Fixed Service Charge (Quota Fissa) | FIXED_CHARGE | 18.00 |
| Aqueduct – Agevolata (tier 1) | AQUEDUCT_T1 | 9.90 |
| Aqueduct – Base (tier 2) | AQUEDUCT_T2 | 24.60 |
| Aqueduct – Eccedenza (tier 3) | AQUEDUCT_T3 | 66.30 |
| Sewerage (Fognatura) | SEWERAGE | 23.40 |
| Purification (Depurazione) | PURIFICATION | 31.20 |
| VAT (IVA 10 %) | VAT | 17.34 |
| **Total** | | **190.74** |

Consumption: **78 m³** this period vs **30 m³** a year ago (~160 % spike, most of it billed in the
expensive Eccedenza tier) — a likely **hidden leak** the assistant flags and offers to log.

### Pre-seeded operational rows (for status demos)

| Record | Account | State |
|--------|---------|-------|
| Interruptions INT-2026-0001/0002/0003 | Prati / Monteverde / Tiburtino | PLANNED (SCHEDULED) / MAIN_BREAK (RESTORING) / PLANNED (CREW_ASSIGNED) |
| Service request SRQ-2026-0001 | Valentina Gallo (WTR-30010011) | LEAK, IN_PROGRESS, technician assigned |
| Billing request BRQ-2026-0001 | Davide Conti (WTR-30010012) | PAYMENT_PLAN, ACTIVE, 6 installments |

---

## Demo Scenarios

### Scenario 1 — "Why is my bill so high?" (MCP only)
Giulia Ricci (WTR-30010001) has a period bill of **EUR 190.74**. The assistant looks up her account,
invoice line items, and consumption and explains that **78 m³** (up from 30 m³ a year ago) pushed most
of her volume into the expensive Eccedenza tier — and flags that a jump this large often means a
**hidden leak**.

### Scenario 2 — "How does my tariff / credit work?" (MCP only)
Marco Bianchi (Large-Household tier allowance), Sofia Russo (Social/Water-Bonus credit), Luca Esposito
(Non-Resident second-home rate) each showcase a distinct residential water-billing construct the
assistant explains from `GetInvoiceDetails` + `GetTariffPlans`.

### Scenario 3 — "Is there a water outage / is my water safe?" (MCP only)
Alessandro Marino / Francesca Greco (Prati, Monteverde) sit under active interruptions (planned
maintenance, main break). Matteo Bruno asks about water hardness/chlorine, answered from
`GetWaterQualityReports`.

### Scenario 4 — "What's the status of my request?" (MCP only)
Valentina Gallo (WTR-30010011) has a pre-seeded leak ticket SRQ-2026-0001; Davide Conti
(WTR-30010012) has an ACTIVE payment plan BRQ-2026-0001. The assistant looks each up and reports
status.

### Scenario 5 — "I think I have a leak — report it" (MCP + A2A open_service_request)
Giulia Ricci's consumption spike (or Laura Fontana's low pressure, Paolo Costa's frozen meter) is
confirmed from the data, then on confirmation the assistant files a service request via
`service_request_agent`, returning a request ID.

### Scenario 6 — "Let me send my own meter reading" (MCP + A2A submit_meter_reading + guardrail)
Elena Romano (WTR-30010005, last read ESTIMATED) submits a self-reading; `meter_reading_agent` records
it as a SELF read. **Guardrail:** a value below the last recorded reading is rejected as implausible.

### Scenario 7 — "Can I pay in installments / this charge is wrong" (MCP + A2A submit_billing_request + guardrail)
Giovanni Colombo (WTR-30010006, overdue) sets up a payment plan; Chiara Ferrari (WTR-30010007) disputes
a bill. `billing_support_agent` writes the request. **Guardrail:** a payment plan is only offered when
there is an outstanding balance.

### Scenario 8 — Email confirmation (A2A send_confirmation_email)
After any write action, the customer can ask "email me a confirmation" and `send_confirmation_email`
sends the details to the address on file via SMTP.

### Scenario 9 — Full end-to-end (read → write → write → email)
Giulia Ricci: explain the high bill → open a leak service request → set up a payment plan for the
higher-than-usual bill → email the confirmation. Exercises reads + two write agents + email in one
conversation.

See `prompts.md` for copy-paste-ready prompts grouped by scenario.

---

## Prerequisites

- TIBCO Flogo Enterprise v2.26.x+
- PostgreSQL 14+ (local or remote)
- OpenAI API key (or an on-premises OpenAI-compatible LLM endpoint)
- Gmail account with an App Password (for the email agent)
- Chatbot UI (from `demos/Agentic_AI/Chatbot/`)

> Environment values (PostgreSQL host/port/user/password, OpenAI API key & model, SMTP host/port/user/
> app-password) are kept in `skills-library/.claude/skills/config.md`. Do **not** paste secrets into
> the apps or this repo — read them from `config.md` and set them as app properties at import time.

---

## Setup & Run

### Step 1 — Create the PostgreSQL database

```bash
psql -U postgres -c "CREATE DATABASE water_utility;"
psql -U postgres -d water_utility -f database.sql
psql -U postgres -d water_utility -f reset_data.sql   # today-relative dates; clean demo state
```

### Step 2 — Import the 3 Flogo apps into TIBCO Flogo Enterprise
1. `WaterUtilityMCPServer.flogo`
2. `WaterUtilityA2AServers.flogo`
3. `WaterUtilityAIOrchestrator.flogo`

### Step 3 — Configure app properties (values from `config.md`; do not hard-code secrets)

**WaterUtilityMCPServer**

| Property | Value |
|----------|-------|
| `PostgreSQL.PostgresConn.Host` | `localhost` |
| `PostgreSQL.PostgresConn.Port` | `5432` |
| `PostgreSQL.PostgresConn.Database_Name` | `water_utility` |
| `PostgreSQL.PostgresConn.User` | `postgres` |
| `PostgreSQL.PostgresConn.Password` | your PostgreSQL password |
| `MCP_SERVER_PORT` | `9782` |

**WaterUtilityA2AServers**

| Property | Value |
|----------|-------|
| `AgenticAI.OpenAIConn.API_Key` | your OpenAI API key |
| `AgenticAI.OpenAIConn.LLM_Base_URL` | `https://api.openai.com/v1` |
| `LLM_Model` | your model (from `config.md`) |
| `PostgreSQL.PostgresConn.*` | as above, DB `water_utility` |
| `Email_Username` / `Email_App_Password` / `To_Email` | Gmail SMTP creds + recipient |
| `ServiceRequest_A2AServer_PORT` | `9783` |
| `MeterReading_A2AServer_PORT` | `9784` |
| `BillingSupport_A2AServer_PORT` | `9785` |
| `SendEmail_A2AServer_PORT` | `9786` |

**WaterUtilityAIOrchestrator**

| Property | Value |
|----------|-------|
| `AgenticAI.OpenAIConn.API_Key` | your OpenAI API key |
| `AgenticAI.OpenAIConn.LLM_Base_URL` | `https://api.openai.com/v1` |
| `LLM_Model` | your model |

### Step 4 — Start the apps (in this order)
1. `WaterUtilityMCPServer` (9782 first)
2. `WaterUtilityA2AServers` (9783–9786)
3. `WaterUtilityAIOrchestrator` (9780 — needs MCP + A2A running)

### Step 5 — Connect the chatbot UI
```bash
cd demos/Agentic_AI/Chatbot
npm install && npm start
```
Open http://localhost:3000, connect to `ws://localhost:9780/water`, and run the prompts from
`prompts.md`. Reset between demos with `reset_data.sql`.

---

## Port Summary

| App | Port | Protocol |
|-----|------|----------|
| WaterUtilityAIOrchestrator | 9780 | WebSocket, `/water` |
| WaterUtilityMCPServer | 9782 | HTTP (MCP), `/water-cis` |
| WaterUtilityA2AServers — service_request_agent | 9783 | HTTP (A2A), `open_service_request` |
| WaterUtilityA2AServers — meter_reading_agent | 9784 | HTTP (A2A), `submit_meter_reading` |
| WaterUtilityA2AServers — billing_support_agent | 9785 | HTTP (A2A), `submit_billing_request` |
| WaterUtilityA2AServers — send_confirmation_email | 9786 | HTTP (A2A), `send_confirmation_email` |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP Server not connecting | Verify port 9782 is open and the MCP app is running before the orchestrator |
| A2A agents not responding | Check ports 9783–9786 are open and the A2A app is running |
| PostgreSQL connection failed | Verify database `water_utility` exists and credentials match `config.md` |
| Agent can't find an account | Match the account number (`WTR-300100XX`), phone, or address to `customers` |
| Interruptions / requests look stale | Re-run `reset_data.sql` — operational rows use today-relative timestamps |
| Self-reading rejected | Expected guardrail: the value is below the last recorded reading |
| Payment plan refused | Expected guardrail: the account has no outstanding balance |
| Email not sending | Verify the Gmail **App Password** (not the account password) and SMTP `smtp.gmail.com:465` |
| WebSocket disconnects | Ensure the Orchestrator is running on 9780 and the client uses `ws://localhost:9780/water` |

---

## Security & Production Notes

This is a working demo. For production the design calls for: TLS on all endpoints (WebSocket + MCP +
A2A), Bearer-token auth on the MCP Server, API-gateway rate limiting, an on-premises LLM for data
residency, and swapping the PostgreSQL-backed tools for real utility backend integrations (Billing/CIS,
CRM, Meter Data Management, Network/Outage Management, Field Service).

---

<!-- The "⚠️ Below things are NOT configured…" manual-config gap section will be appended here at
     finalize time (Phase 5), covering LLM creds/endpoint, DB creds, ports, SMTP-password-as-secret,
     WebSocket client, and the FDA Tech-Preview manual steps (Sync every trigger, validate every
     connection). -->
