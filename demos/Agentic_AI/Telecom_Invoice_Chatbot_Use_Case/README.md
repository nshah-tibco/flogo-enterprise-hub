# Telecom Invoice Chatbot Use Case

An AI-powered billing chatbot for telecom subscribers, built on TIBCO Flogo Enterprise. Subscribers ask natural-language questions ("Why is my bill so high?", "Get me a data pack", "Dispute this charge") over a WebSocket streaming chat. The system uses a 3-tier agentic architecture — an AI Orchestrator, an MCP Server for read-only BSS lookups, and A2A Servers for write workflows — all communicating via standard protocols (MCP, A2A, WebSocket).

> **Demo dataset:** an Indonesian telecom provider — currency **IDR** (Indonesian Rupiah), VAT **PPN 11%**, subscribers with `+62` mobile numbers, and Southeast-Asia / Umrah roaming destinations (Singapore, Malaysia, Thailand, Japan, Australia, Saudi Arabia).

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
| **GetInvoiceDetails** | Invoice header + line items (PLAN/IDD/ADDON/ROAMING/TAX) | `invoices JOIN invoice_line_items` |
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
| `customers` | CRM master records (mobile = subscriber id) | 16 subscribers |
| `invoices` | Monthly invoice headers | 12 (June 2026, postpaid) |
| `invoice_line_items` | Charges per invoice (incl. PPN 11%) | 41 line items |
| `usage_records` | Metered usage vs limits | 16 (one per subscriber) |
| `plans` | Base plans + add-ons | 21 |
| `payments` | Payment / top-up history | 38 |
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

Budi Santoso (+62-812-3456-7890, Premium, Jakarta) has a June 2026 bill of **IDR 499,500**. The agent looks up his profile, invoice, and usage and explains each line item — Plan IDR 150,000, IDD Singapore IDR 85,000, Data Add-on 10GB IDR 50,000, Roaming Singapore IDR 165,000, PPN 11% IDR 49,500 — confirming the roaming is valid (3 roaming days recorded).

```
You:   Why is my bill so high this month? My number is +62-812-3456-7890.
Agent: Your June bill is IDR 499,500, made up of: Pascabayar Prime 100 (IDR 150,000),
       International Calls to Singapore (IDR 85,000), a 10GB Data Add-on (IDR 50,000),
       Roaming Singapore for 3 days (IDR 165,000), and VAT/PPN 11% (IDR 49,500). Your
       usage shows 3 roaming days in Singapore, so the roaming charge is valid.
```

### Scenario 2: "I was charged for roaming but I didn't travel" (MCP + A2A dispute)

Siti Nurhaliza (+62-813-2345-6789) is billed **IDR 220,000 Roaming Thailand**, but her usage shows **0 roaming days**. The agent detects the discrepancy and, on confirmation, files a dispute via `billing_dispute_agent`.

```
You:   I was charged for roaming in Thailand but I never left Indonesia.
       My number is +62-813-2345-6789.
Agent: I checked invoice INV-2026-06-872: it has a Roaming Thailand charge of
       IDR 220,000, but your usage shows 0 roaming days. That's a clear discrepancy.
       Would you like me to file a dispute?
You:   Yes please.
Agent: Done. Dispute DSP-2026-XXXX is now OPEN, estimated resolution within
       5 business days.
```

### Scenario 3: "I need more data" (MCP + A2A recharge)

Ahmad Wijaya (+62-852-3456-7891) has used 19.6 of 20 GB. The agent shows recharge offers and, on confirmation, applies one via `recharge_agent`.

```
You:   I'm almost out of data. My number is +62-852-3456-7891.
Agent: You've used 19.6 of your 20 GB. Here are recharge packs: Data Booster 5GB
       (IDR 30,000), Data Booster 10GB (IDR 50,000), Data Max 25GB (IDR 100,000).
You:   Give me the 10GB one.
Agent: Applied! Recharge RCG-2026-XXXX — Data Booster 10GB (IDR 50,000), 10 GB added,
       active for 30 days.
```

### Scenario 4: "Show my last 3 payments" (MCP only)

Rudi Hartono (+62-811-5678-9012, Business, Jakarta) — the agent returns his most recent Auto-Debit payments.

### Scenario 5: "What plan am I on?" (MCP only)

Any subscriber — the agent summarizes the base plan and any active add-ons with expiry dates.

### Scenario 6: "What's the status of my dispute?" (MCP only)

Maya Sari (+62-812-6789-0123, VIP, Denpasar) has a pre-seeded dispute (DSP-2026-0001, UNDER_REVIEW). The agent looks it up via `GetDisputes`.

---

## Sample Data Summary

### Subscribers

| Customer ID | Name | Mobile | City | Segment | Type | Demo role |
|-------------|------|--------|------|---------|------|-----------|
| CUST-10042871 | Budi Santoso | +62-812-3456-7890 | Jakarta | Premium | Postpaid | "Why is my bill high" (roaming Singapore valid) |
| CUST-10042872 | Siti Nurhaliza | +62-813-2345-6789 | Bandung | Consumer | Postpaid | Dispute (roaming Thailand charged, 0 roaming days) |
| CUST-10042873 | Ahmad Wijaya | +62-852-3456-7891 | Surabaya | Consumer | Postpaid | Recharge (19.6/20 GB) + OPEN dispute DSP-2026-0003 |
| CUST-10042874 | Dewi Lestari | +62-857-4567-8901 | Yogyakarta | Consumer | Prepaid | Plan lookup |
| CUST-10042875 | Rudi Hartono | +62-811-5678-9012 | Jakarta | Business | Postpaid | Payment history |
| CUST-10042876 | Maya Sari | +62-812-6789-0123 | Denpasar | VIP | Postpaid | Dispute status (DSP-2026-0001, UNDER_REVIEW) |
| CUST-10042877 | Andi Pratama | +62-853-7890-1234 | Makassar | Consumer | Prepaid | Prepaid / general |
| CUST-10042878 | Rina Melati | +62-878-8901-2345 | Medan | Premium | Postpaid | Clean bill |
| CUST-10042879 | Joko Susilo | +62-856-9012-3456 | Semarang | Consumer | Postpaid | Dispute (IDD China charged, 0 intl minutes) |
| CUST-10042880 | Putri Anggraini | +62-838-0123-4567 | Jakarta | Premium | Postpaid | High roaming (Australia, valid) |
| CUST-10042881 | Bambang Kusuma | +62-817-1234-5678 | Palembang | Business | Postpaid | Recharge (96.5/100 GB) |
| CUST-10042882 | Sri Wahyuni | +62-819-2345-6780 | Batam | Consumer | Prepaid | Prepaid top-ups |
| CUST-10042883 | Agus Salim | +62-822-3456-7801 | Surabaya | Consumer | Postpaid | Resolved dispute (DSP-2026-0002) |
| CUST-10042884 | Fitri Handayani | +62-812-4567-8902 | Bandung | Premium | Postpaid | Roaming Malaysia (valid) |
| CUST-10042885 | Hendra Gunawan | +62-813-5678-9013 | Jakarta | VIP | Postpaid | Umrah roaming Saudi Arabia (valid), highest bill |
| CUST-10042886 | Lia Permata | +62-858-6789-0124 | Denpasar | Consumer | Prepaid | Clean prepaid |

### Flagship Invoice — Budi Santoso (INV-2026-06-871)

| Line item | Category | Amount (IDR) |
|-----------|----------|--------------|
| Pascabayar Prime 100 (monthly) | PLAN | 150,000 |
| International Calls (Singapore) | IDD | 85,000 |
| Data Add-on 10GB | ADDON | 50,000 |
| Roaming Singapore (3 days) | ROAMING | 165,000 |
| VAT (PPN) 11% | TAX | 49,500 |
| **Total** | | **499,500** |

Usage: Data 38.7 / 50 GB · Local 342 min · International 47 min · SMS 12 · Roaming 3 days (Singapore)

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
