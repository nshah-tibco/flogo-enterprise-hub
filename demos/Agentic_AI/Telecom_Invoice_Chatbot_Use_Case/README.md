# Telecom Invoice Chatbot Use Case

An AI-powered billing chatbot for telecom subscribers, built on TIBCO Flogo Enterprise. Subscribers ask natural-language questions ("Why is my bill so high?", "Get me a data pack", "Dispute this charge") over a WebSocket streaming chat. The system uses a 3-tier agentic architecture — an AI Orchestrator, an MCP Server for read-only BSS lookups, and A2A Servers for write workflows — all communicating via standard protocols (MCP, A2A, WebSocket).

> **Demo dataset:** a US telecom provider — currency **USD** (US Dollar), **Taxes & Regulatory Fees ~10%**, subscribers with `+1` mobile numbers, and international / roaming destinations (Mexico, Canada, Japan, China, India, UK, Germany). Six accounts carry intentionally incorrect charges for billing-dispute demos.

---

## Architecture Overview

```
                    ┌─────────────────────────┐
                    │     Chatbot UI          │
                    │  (WebSocket Client)     │
                    └───────┬─────────────────┘
                            │ WebSocket
                            │ ws://localhost:9500/telecom
                            ▼
               ┌────────────────────────────────┐
               │  Telecom Invoice               │
               │  AI Orchestrator               │
               │  (TelecomInvoiceAIOrch.)       │
               │  Port 9500 (WebSocket)         │
               │  LLM: OpenAI GPT               │
               └───────┬───────────┬────────────┘
                       │           │
          MCP (HTTP)   │           │  A2A Protocol
                       ▼           ▼
    ┌──────────────────────┐   ┌──────────────────────────────────┐
    │  Telecom Invoice     │   │  Telecom Invoice                 │
    │  MCP Server          │   │  A2A Servers                     │
    │  Port 9882           │   │                                  │
    │  /telecom-bss        │   │  billing_dispute_agent    :9883  │
    │                      │   │  recharge_agent           :9884  │
    │  Tools (read-only):  │   │  send_confirmation_email  :9885  │
    │  - GetCustomerProfile│   │                                  │
    │  - GetInvoiceDetails │   │  Uses PostgreSQL for             │
    │  - GetUsageBreakdown │   │  data validation & writes        │
    │  - GetActivePlans    │   │  + Gmail SMTP for email          │
    │  - GetPaymentHistory │   │                                  │
    │  - CheckRechargeOffers│  │                                  │
    │  - GetDisputes       │   │                                  │
    └──────────┬───────────┘   └──────────────┬───────────────────┘
               │                              │
               └──────────────┬───────────────┘
                              ▼
               ┌────────────────────────────┐
               │  PostgreSQL Database       │
               │  Database: telecom         │
               │  9 Tables                  │
               └────────────────────────────┘
```

---

## Flogo Apps

### 1. `TelecomInvoiceMCPServer.flogo` — MCP Server (Port 9882)

Exposes 7 read-only BSS lookup tools via the Model Context Protocol over Streamable HTTP (endpoint `/telecom-bss`). Each tool queries the PostgreSQL `telecom` database and returns the full result set as a string; the LLM filters by mobile number / customer ID.

| Tool | Description | SQL |
|------|-------------|-----|
| **GetCustomerProfile** | CRM profile: mobile, name, segment, account type, active since | `SELECT * FROM customers` |
| **GetInvoiceDetails** | Invoice header + line items (PLAN/IDD/ADDON/ROAMING/OTHER/TAX) | `invoices JOIN invoice_line_items` |
| **GetUsageBreakdown** | Data/voice/SMS/roaming usage vs limits | `SELECT * FROM usage_records` |
| **GetActivePlans** | Current base plan + add-ons with expiry | `SELECT * FROM plans` |
| **GetPaymentHistory** | Recent payments with method and status | `SELECT * FROM payments` |
| **CheckRechargeOffers** | Catalog of data/IDD/roaming/combo packs | `SELECT * FROM recharge_offers` |
| **GetDisputes** | Dispute tickets with status and resolution | `SELECT * FROM disputes` |

### 2. `TelecomInvoiceA2AServers.flogo` — A2A Servers (Ports 9883–9885)

Three A2A agents that handle write workflows. Each agent has its own LLM, system prompt, and tool handler.

| Agent | Port | Description |
|-------|------|-------------|
| **billing_dispute_agent** | 9883 | Validates a disputed invoice by cross-checking line items against usage records, then inserts a dispute ticket (status OPEN, 5-day estimated resolution) into `disputes`. |
| **recharge_agent** | 9884 | Applies a chosen recharge pack: inserts an ACTIVE recharge with 30-day validity into `recharges` and confirms activation. |
| **send_confirmation_email** | 9885 | Sends a confirmation email (dispute filed / recharge applied) via Gmail SMTP. Invoked only once, after the billing action, when the user requests it. |

### 3. `TelecomInvoiceAIOrchestrator.flogo` — AI Orchestrator (Port 9500)

The main orchestration app. Exposes a WebSocket endpoint for natural-language chat. An AI Agent activity classifies intent and routes to either MCP tools (data lookups) or A2A agents (write workflows).

| Setting | Value |
|---------|-------|
| WebSocket Path | `/telecom` |
| LLM | OpenAI GPT |
| MCP Server | `http://localhost:9882/telecom-bss` |
| A2A Agents | billing_dispute (9883), recharge (9884), email (9885) |

---

## Database

9 tables in the PostgreSQL `telecom` database:

| Table | Purpose | Records |
|-------|---------|---------|
| `customers` | CRM master records (mobile = subscriber id) | 22 subscribers |
| `invoices` | Monthly invoice headers | 18 (June 2026, postpaid) |
| `invoice_line_items` | Charges per invoice (incl. Taxes & Fees) | 59 line items |
| `usage_records` | Metered usage vs limits | 22 (one per subscriber) |
| `plans` | Base plans + add-ons | 27 |
| `payments` | Payment / top-up history | 50 |
| `recharge_offers` | Global recharge catalog | 8 offers |
| `disputes` | Dispute tickets (pre-seeded + written by agent) | 3 seeded |
| `recharges` | Recharge activation log (written by agent) | starts empty |

```bash
# Initialize schema and demo data
psql -U postgres -d telecom -f database.sql

# Reset with today-relative due/payment/dispute dates (for live demos)
psql -U postgres -d telecom -f reset_data.sql
```

---

## Demo Scenarios

### Scenario 1: "Why is my bill so high?" (MCP only)

James Anderson (+1-415-555-0142, Premium, San Francisco) has a June 2026 bill of **USD 139.70**. The agent looks up his profile, invoice, and usage and explains each line item — Plan USD 70.00, IDD Mexico USD 12.00, Data Add-on 10GB USD 15.00, Roaming Mexico USD 30.00, Taxes & Regulatory Fees USD 12.70 — confirming the roaming is valid (3 roaming days recorded).

```
You:   Why is my bill so high this month? My number is +1-415-555-0142.
Agent: Your June bill is USD 139.70, made up of: Premium Unlimited (USD 70.00),
       International Calls to Mexico (USD 12.00), a 10GB Data Add-on (USD 15.00),
       Roaming Mexico for 3 days (USD 30.00), and Taxes & Regulatory Fees (USD 12.70).
       Your usage shows 3 roaming days in Mexico, so the roaming charge is valid.
```

### Scenario 2: "I was charged for roaming but I didn't travel" (MCP + A2A dispute)

Emily Carter (+1-212-555-0178) is billed **USD 45.00 Roaming Mexico**, but her usage shows **0 roaming days**. The agent detects the discrepancy and, on confirmation, files a dispute via `billing_dispute_agent`.

```
You:   I was charged for roaming in Mexico but I never left the country.
       My number is +1-212-555-0178.
Agent: I checked invoice INV-2026-06-872: it has a Roaming Mexico charge of
       USD 45.00, but your usage shows 0 roaming days. That's a clear discrepancy.
       Would you like me to file a dispute?
You:   Yes please.
Agent: Done. Dispute DSP-2026-XXXX is now OPEN, estimated resolution within
       5 business days.
```

### Scenario 3: "I need more data" (MCP + A2A recharge)

Michael Rodriguez (+1-312-555-0163) has used 19.6 of 20 GB. The agent shows recharge offers and, on confirmation, applies one via `recharge_agent`.

```
You:   I'm almost out of data. My number is +1-312-555-0163.
Agent: You've used 19.6 of your 20 GB. Here are recharge packs: Data Booster 5GB
       (USD 10.00), Data Booster 10GB (USD 15.00), Data Max 25GB (USD 30.00).
You:   Give me the 10GB one.
Agent: Applied! Recharge RCG-2026-XXXX — Data Booster 10GB (USD 15.00), 10 GB added,
       active for 30 days.
```

### Scenario 4: "Show my last 3 payments" (MCP only)

David Martinez (+1-617-555-0187, Business, Boston) — the agent returns his most recent Auto-Pay payments.

### Scenario 5: "What plan am I on?" (MCP only)

Any subscriber — the agent summarizes the base plan and any active add-ons with expiry dates.

### Scenario 6: "What's the status of my dispute?" (MCP only)

Jessica Williams (+1-305-555-0134, VIP, Miami) has a pre-seeded dispute (DSP-2026-0001, UNDER_REVIEW). The agent looks it up via `GetDisputes`.

### Scenario 7: Wrong-charge disputes (MCP + A2A dispute)

Six dedicated accounts (CUST-10042887 … CUST-10042892) each carry one intentionally incorrect charge on their June invoice, contradicted by their usage record — a roaming charge with 0 roaming days, an international-call charge with 0 intl minutes, a duplicated monthly plan fee, an unauthorized premium-content subscription, a data-overage fee while under the limit, and a late-payment fee despite paying on time. Each lets the agent confirm the discrepancy and file a dispute. See `prompts.md` §10 for the exact prompts.

---

## Sample Data Summary

### Subscribers

| Customer ID | Name | Mobile | City | Segment | Type | Demo role |
|-------------|------|--------|------|---------|------|-----------|
| CUST-10042871 | James Anderson | +1-415-555-0142 | San Francisco | Premium | Postpaid | "Why is my bill high" (roaming Mexico valid) |
| CUST-10042872 | Emily Carter | +1-212-555-0178 | New York | Consumer | Postpaid | Dispute (roaming Mexico charged, 0 roaming days) |
| CUST-10042873 | Michael Rodriguez | +1-312-555-0163 | Chicago | Consumer | Postpaid | Recharge (19.6/20 GB) + OPEN dispute DSP-2026-0003 |
| CUST-10042874 | Sarah Thompson | +1-206-555-0119 | Seattle | Consumer | Prepaid | Plan lookup |
| CUST-10042875 | David Martinez | +1-617-555-0187 | Boston | Business | Postpaid | Payment history |
| CUST-10042876 | Jessica Williams | +1-305-555-0134 | Miami | VIP | Postpaid | Dispute status (DSP-2026-0001, UNDER_REVIEW) |
| CUST-10042877 | Christopher Lee | +1-702-555-0155 | Las Vegas | Consumer | Prepaid | Prepaid / general |
| CUST-10042878 | Amanda Davis | +1-512-555-0198 | Austin | Premium | Postpaid | Clean bill |
| CUST-10042879 | Robert Johnson | +1-404-555-0172 | Atlanta | Consumer | Postpaid | Dispute (IDD China charged, 0 intl minutes) |
| CUST-10042880 | Ashley Brown | +1-646-555-0110 | New York | Premium | Postpaid | High roaming (Canada, valid) |
| CUST-10042881 | Daniel Wilson | +1-773-555-0145 | Chicago | Business | Postpaid | Recharge (96.5/100 GB) |
| CUST-10042882 | Michelle Garcia | +1-480-555-0166 | Phoenix | Consumer | Prepaid | Prepaid top-ups |
| CUST-10042883 | Matthew Miller | +1-215-555-0129 | Philadelphia | Consumer | Postpaid | Resolved dispute (DSP-2026-0002) |
| CUST-10042884 | Stephanie Moore | +1-503-555-0181 | Portland | Premium | Postpaid | Roaming Mexico (valid) |
| CUST-10042885 | Kevin Taylor | +1-725-555-0193 | Las Vegas | VIP | Postpaid | Roaming Japan (valid), highest bill |
| CUST-10042886 | Nicole Jackson | +1-919-555-0157 | Raleigh | Consumer | Prepaid | Clean prepaid |
| CUST-10042887 | Brian Hall | +1-408-555-0102 | San Jose | Consumer | Postpaid | Wrong charge: roaming Mexico, 0 roaming days |
| CUST-10042888 | Laura Adams | +1-619-555-0113 | San Diego | Premium | Postpaid | Wrong charge: IDD India, 0 intl minutes |
| CUST-10042889 | Kevin Nguyen | +1-716-555-0124 | Buffalo | Consumer | Postpaid | Wrong charge: monthly plan billed twice |
| CUST-10042890 | Rachel Scott | +1-813-555-0135 | Tampa | Consumer | Postpaid | Wrong charge: unauthorized premium content |
| CUST-10042891 | Justin King | +1-901-555-0146 | Memphis | Premium | Postpaid | Wrong charge: data overage while under limit |
| CUST-10042892 | Megan Wright | +1-303-555-0157 | Denver | Consumer | Postpaid | Wrong charge: late fee despite paying on time |

### Flagship Invoice — James Anderson (INV-2026-06-871)

| Line item | Category | Amount (USD) |
|-----------|----------|--------------|
| Premium Unlimited (monthly) | PLAN | 70.00 |
| International Calls (Mexico) | IDD | 12.00 |
| Data Add-on 10GB | ADDON | 15.00 |
| Roaming Mexico (3 days) | ROAMING | 30.00 |
| Taxes & Regulatory Fees | TAX | 12.70 |
| **Total** | | **139.70** |

Usage: Data 38.7 / 50 GB · Local 342 min · International 47 min · SMS 12 · Roaming 3 days (Mexico)

---

## Port Summary

| App | Port | Protocol |
|-----|------|----------|
| TelecomInvoiceMCPServer | 9882 | HTTP (MCP), `/telecom-bss` |
| TelecomInvoiceA2AServers — billing_dispute | 9883 | HTTP (A2A) |
| TelecomInvoiceA2AServers — recharge | 9884 | HTTP (A2A) |
| TelecomInvoiceA2AServers — send_email | 9885 | HTTP (A2A) |
| TelecomInvoiceAIOrchestrator | 9500 | WebSocket |

---

## Supporting Files

| File | Description |
|------|-------------|
| `database.sql` | PostgreSQL schema with 9 tables and demo data |
| `reset_data.sql` | Data reset script (today-relative dates; clears agent-written rows) |
| `prompts.md` | Demo prompts organized by scenario |
| `manual-steps.md` | Step-by-step setup and deployment instructions |

---

## Security & Production Notes (from the design)

This is the Phase-1 working demo. For production the design calls for: TLS on all endpoints (WebSocket + MCP + A2A), Bearer-token auth on the MCP Server, API-gateway rate limiting, an on-premises LLM for data residency, and swapping the PostgreSQL-backed tools for real BSS API calls (Billing, CRM, Product Catalog, Payment Gateway). See the source deck `Telecom-Invoice-Chatbot-Flogo-Agentic-AI-v2.pdf`.
