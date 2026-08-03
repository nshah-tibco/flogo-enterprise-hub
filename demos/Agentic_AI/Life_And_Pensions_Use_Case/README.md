# Life & Pensions Member Assistant Use Case

An AI-powered member self-service assistant for a mutual life, pensions & investments provider, built on TIBCO Flogo Enterprise. Members ask natural-language questions ("What's my 401(k) balance?", "How am I invested?", "Update my beneficiary", "File a claim") over a WebSocket streaming chat. The system uses a 3-tier agentic architecture — an AI Orchestrator, an MCP Server for read-only book-of-record lookups, and A2A Servers for write workflows — all communicating via standard protocols (MCP, A2A, WebSocket).

> **Demo dataset:** a US mutual life, pensions & investments provider — currency **USD** (US Dollar). Members hold protection policies (Life / Critical Illness / Income Protection / Investment), 401(k) and IRA retirement accounts, fund holdings, contribution history, nominated beneficiaries and claims. The flagship persona (James Carter) is engineered so every write workflow has a clear, real reason to fire: an outdated beneficiary, an under-matched 401(k) contribution, an over-weight high-risk fund holding, and a claimable policy with no existing claim.

---

## Architecture Overview

```
                    ┌─────────────────────────┐
                    │     Chatbot UI          │
                    │  (WebSocket Client)     │
                    └───────┬─────────────────┘
                            │ WebSocket
                            │ ws://localhost:9600/lifepensions
                            ▼
               ┌────────────────────────────────┐
               │  Life & Pensions               │
               │  AI Orchestrator               │
               │  (LifePensionsAIOrchestrator)  │
               │  Port 9600 (WebSocket)         │
               │  LLM: OpenAI gpt-5.5           │
               └───────┬───────────┬────────────┘
                       │           │
          MCP (HTTP)   │           │  A2A Protocol
                       ▼           ▼
    ┌──────────────────────┐   ┌──────────────────────────────────────┐
    │  Life & Pensions     │   │  Life & Pensions                     │
    │  MCP Server          │   │  A2A Servers                         │
    │  Port 9982           │   │                                      │
    │  /life-pensions      │   │  update_beneficiary_agent     :9983  │
    │                      │   │  change_contribution_agent    :9984  │
    │  Tools (read-only):  │   │  fund_switch_agent            :9985  │
    │  - GetMemberProfile  │   │  submit_claim_agent           :9986  │
    │  - GetPolicies       │   │  adviser_callback_agent       :9987  │
    │  - GetRetirementAccts│   │  send_confirmation_email      :9988  │
    │  - GetFunds          │   │                                      │
    │  - GetHoldings       │   │  Uses PostgreSQL for                 │
    │  - GetContributions  │   │  data validation & writes            │
    │  - GetBeneficiaries  │   │  + Gmail SMTP for email              │
    │  - GetClaims         │   │                                      │
    └──────────┬───────────┘   └──────────────┬───────────────────────┘
               │                              │
               └──────────────┬───────────────┘
                              ▼
               ┌────────────────────────────┐
               │  PostgreSQL Database       │
               │  Database: life_pensions   │
               │  10 Tables                 │
               └────────────────────────────┘
```

---

## Flogo Apps

### 1. `LifePensionsMCPServer.flogo` — MCP Server (Port 9982)

Exposes 8 read-only lookup tools via the Model Context Protocol over Streamable HTTP (endpoint `/life-pensions`). Each tool queries the PostgreSQL `life_pensions` database and returns the full result set as a string; the LLM filters by `member_id` / name / email.

| Tool | Description | SQL |
|------|-------------|-----|
| **GetMemberProfile** | Member profile: name, email, phone, DOB, address, marital status, member since | `SELECT * FROM members` |
| **GetPolicies** | Protection & investment policies: product type, sum assured, premium, status, renewal | `SELECT * FROM policies` |
| **GetRetirementAccounts** | 401(k) / IRA balances, contribution rate, employer match, YTD & limit, vested balance | `SELECT * FROM retirement_accounts` |
| **GetFunds** | Fund catalog: category, risk level, returns (YTD / 1yr / 3yr), expense ratio, NAV | `SELECT * FROM funds` |
| **GetHoldings** | Per-account fund allocation with fund details (units, value, allocation %) | `holdings JOIN funds` |
| **GetContributions** | Contribution & premium payment history (Employee / Employer / Premium / Rollover) | `SELECT * FROM contributions` |
| **GetBeneficiaries** | Nominated beneficiaries per policy with policy context | `beneficiaries JOIN policies` |
| **GetClaims** | Protection claims with type, amount, status and last update | `SELECT * FROM claims` |

### 2. `LifePensionsA2AServers.flogo` — A2A Servers (Ports 9983–9988)

Six A2A agents that handle write workflows. Each agent has its own LLM, system prompt, and tool handler. The first five perform a data change; the sixth sends a confirmation email.

| Agent | Port | Description | Generated ID |
|-------|------|-------------|--------------|
| **update_beneficiary_agent** | 9983 | Replaces the nominated beneficiary on a policy (e.g. swaps out an ex-spouse), writing a new beneficiary record. | `BEN-2026-XXXX` |
| **change_contribution_agent** | 9984 | Changes a 401(k) contribution rate (e.g. raising it to capture the full employer match) and logs the change. | `CON-2026-XXXX` |
| **fund_switch_agent** | 9985 | Moves value out of one fund into another within a retirement account, inserting a fund-switch request into `fund_switches`. | `SWT-2026-XXXX` |
| **submit_claim_agent** | 9986 | Files a protection claim against an eligible active policy, inserting a new row into `claims` (status Submitted). | `CLM-2026-XXX` |
| **adviser_callback_agent** | 9987 | Books a callback with a financial adviser on a chosen topic and preferred time, inserting into `adviser_callbacks`. | `CBK-2026-XXXX` |
| **send_confirmation_email** | 9988 | Sends a confirmation email (contribution change / fund switch / claim filed / callback booked) via Gmail SMTP. Invoked once, after a write action, when the user requests it. | — |

### 3. `LifePensionsAIOrchestrator.flogo` — AI Orchestrator (Port 9600)

The main orchestration app. Exposes a WebSocket endpoint for natural-language chat. An AI Agent activity classifies intent and routes to either MCP tools (data lookups) or A2A agents (write workflows).

| Setting | Value |
|---------|-------|
| WebSocket Path | `/lifepensions` |
| LLM | OpenAI gpt-5.5 |
| MCP Server | `http://localhost:9982/life-pensions` |
| A2A Agents | update_beneficiary (9983), change_contribution (9984), fund_switch (9985), submit_claim (9986), adviser_callback (9987), email (9988) |

---

## Database

10 tables in the PostgreSQL `life_pensions` database:

| Table | Purpose | Records |
|-------|---------|---------|
| `members` | Member master records (member_id = subscriber id) | 10 members |
| `policies` | Protection & investment products per member | 17 policies |
| `retirement_accounts` | 401(k) / IRA balances (writeable: contribution rate) | 8 accounts |
| `funds` | Shared fund catalog | 10 funds |
| `holdings` | Per-account fund allocation (writeable: fund switch) | 15 holdings |
| `contributions` | Contribution / premium history (writeable: change) | 16 records |
| `beneficiaries` | Nominated beneficiaries per policy (writeable: update) | 10 records |
| `claims` | Protection claims (writeable: submit) | 4 seeded |
| `adviser_callbacks` | Adviser callback requests (written by agent) | starts empty |
| `fund_switches` | Fund switch requests (written by agent) | starts empty |

```bash
# Initialize schema and demo data
psql -U postgres -d life_pensions -f database.sql

# Reset with today-relative contribution/claim/pending-policy dates (for live demos)
psql -U postgres -d life_pensions -f reset_data.sql
```

---

## Demo Scenarios

The demo is built around a flagship persona — **James Carter (member_id `MBR-100001`, james.carter@example.com, San Francisco CA, Divorced)** — whose data is engineered so each of the six capabilities has a real trigger.

### Scenario 1: "What's my pension pot?" (MCP only)

James Carter asks about his retirement savings. The agent looks up his accounts via `GetRetirementAccounts` and reports his **401(k) (RET-5001) balance of USD 181,685** and **Roth IRA (RET-5002) of USD 45,300** — and flags that he is contributing only **3%** while his employer matches up to **6%**, so he is leaving free money on the table.

```
You:   What's my 401(k) balance? My member ID is MBR-100001.
Agent: Your 401(k) (RET-5001) balance is USD 181,685 and your Roth IRA (RET-5002)
       is USD 45,300. Note: you're contributing 3%, but your employer matches up
       to 6% — raising your rate to 6% would capture the full match.
```

### Scenario 2: "How am I invested?" (MCP only)

James reviews his 401(k) allocation. The agent uses `GetHoldings` and highlights that **34.8% sits in the Aggressive Growth Equity Fund (FND-001, HIGH risk)**, which is aggressive for someone approaching retirement.

```
You:   How is my 401(k) invested? MBR-100001.
Agent: Your RET-5001 holdings are: Aggressive Growth Equity Fund (HIGH risk) 34.8%,
       S&P 500 Index Fund 38.9%, Total Bond Market Fund 26.3%. A third of your pot
       is in a HIGH-risk fund — worth reviewing as you near retirement.
```

### Scenario 3: Increase contribution to capture full match (MCP + A2A change_contribution)

James raises his 401(k) contribution from **3% to 6%** to capture the full employer match. The agent confirms, then fires `change_contribution_agent` (→ `CON-2026-XXXX`) and can email a confirmation.

```
You:   Increase my 401(k) contribution to 6% so I get the full employer match. MBR-100001.
Agent: Done — your contribution rate on RET-5001 is now 6% (CON-2026-XXXX), which
       captures your full 6% employer match. Would you like an email confirmation?
```

### Scenario 4: Switch out of the high-risk fund (MCP + A2A fund_switch)

James de-risks by moving out of the HIGH-risk **Aggressive Growth Equity Fund (FND-001)** into **Target Retirement 2045 (FND-005)** (or Total Bond, FND-003). The agent fires `fund_switch_agent` (→ `SWT-2026-XXXX`).

```
You:   Move my Aggressive Growth holding into the Target Retirement 2045 fund. MBR-100001.
Agent: Switch requested: FND-001 (Aggressive Growth) → FND-005 (Target Retirement 2045)
       in RET-5001 (SWT-2026-XXXX), status Requested.
```

### Scenario 5: Update an outdated beneficiary (MCP + A2A update_beneficiary)

James is divorced but his Term Life (POL-2026-1001) and Critical Illness (POL-2026-1002) policies still name his ex-spouse **Emily Carter**. The agent detects this via `GetBeneficiaries` and, on confirmation, replaces her via `update_beneficiary_agent` (→ `BEN-2026-XXXX`).

```
You:   My Term Life policy still lists my ex-wife. Change the beneficiary to my daughter, Sarah Carter. MBR-100001.
Agent: Your Term Life policy (POL-2026-1001) currently names Emily Carter (Spouse, 100%).
       I've replaced her with Sarah Carter (Child, 100%) — new record BEN-2026-XXXX.
```

### Scenario 6: File an Income Protection claim (MCP + A2A submit_claim)

James has an active Income Shield Plan (POL-2026-1003, IncomeProtection, USD 4,000/mo) and **no existing claim**, so he can file one. The agent files it via `submit_claim_agent` (→ `CLM-2026-XXX`) and can email a confirmation.

```
You:   I've been signed off work and need to claim on my income protection policy. MBR-100001.
Agent: I've submitted an Income Protection claim on POL-2026-1003 (CLM-2026-XXX),
       monthly benefit USD 4,000, status Submitted. Shall I email you the confirmation?
```

### Scenario 7: Book an adviser callback (A2A adviser_callback)

James requests a retirement-planning call. The agent books it via `adviser_callback_agent` (→ `CBK-2026-XXXX`).

```
You:   Can a financial adviser call me about my retirement plan? Tomorrow afternoon works. MBR-100001.
Agent: Booked — a retirement-planning callback is scheduled for tomorrow afternoon
       (CBK-2026-XXXX). An adviser will call you on +1-415-555-0101.
```

### Scenario 8: Other personas (read + edge cases)

- **Robert Johnson** (`MBR-100005`) — near retirement, large **401(k) (RET-5005) of USD 512,300**; good "big pot" read demo.
- **David Chen** (`MBR-100003`) — has an Income Protection claim **UnderReview** (`CLM-2026-001`); claim-status lookup.
- **Susan Miller** (`MBR-100004`) — her only policy (POL-2026-1008) is **Lapsed**; the agent should decline a claim on it (edge case).
- **Patricia Wilson** (`MBR-100010`) — her Critical Illness policy (POL-2026-1017) is **Pending** underwriting (edge case).

---

## Sample Data Summary

### Members

| Member ID | Name | Email | City, State | Marital | Demo role |
|-----------|------|-------|-------------|---------|-----------|
| MBR-100001 | James Carter | james.carter@example.com | San Francisco, CA | Divorced | **Flagship** — all six workflows |
| MBR-100002 | Maria Gonzalez | maria.gonzalez@example.com | Chicago, IL | Married | Fully matched 401(k) (6%) |
| MBR-100003 | David Chen | david.chen@example.com | Seattle, WA | Married | Income Protection claim UnderReview |
| MBR-100004 | Susan Miller | susan.miller@example.com | Boston, MA | Single | Lapsed policy (edge case) |
| MBR-100005 | Robert Johnson | robert.johnson@example.com | Denver, CO | Married | Near retirement, USD 512k 401(k) |
| MBR-100006 | Linda Williams | linda.williams@example.com | Austin, TX | Widowed | Denied claim; Trust beneficiary |
| MBR-100007 | Michael Brown | michael.brown@example.com | Atlanta, GA | Single | Roth IRA, 100% in high-risk fund |
| MBR-100008 | Jennifer Davis | jennifer.davis@example.com | Miami, FL | Married | Paid claim; Investment plan |
| MBR-100009 | William Martinez | william.martinez@example.com | Phoenix, AZ | Married | Whole Life; split beneficiaries |
| MBR-100010 | Patricia Wilson | patricia.wilson@example.com | Portland, OR | Single | Pending policy (edge case) |

### Flagship Profile — James Carter (MBR-100001)

**Policies (all Active, no existing claim):**

| Policy | Product | Type | Sum assured / benefit | Premium |
|--------|---------|------|-----------------------|---------|
| POL-2026-1001 | 20-Year Term Life | Life | USD 500,000 | USD 45.00/mo |
| POL-2026-1002 | Critical Illness Protect | CriticalIllness | USD 100,000 | USD 28.50/mo |
| POL-2026-1003 | Income Shield Plan | IncomeProtection | USD 4,000/mo benefit | USD 32.00/mo |

**Retirement accounts:**

| Account | Type | Balance | Contribution | Employer match | Note |
|---------|------|---------|--------------|----------------|------|
| RET-5001 | 401(k) | USD 181,685 | 3% | up to 6% | **Under-matched** — capture the extra 3% |
| RET-5002 | Roth IRA | USD 45,300 | — | — | — |

**RET-5001 holdings:**

| Fund | Risk | Value (USD) | Allocation |
|------|------|-------------|------------|
| FND-001 Aggressive Growth Equity Fund | HIGH | 63,225 | 34.80% |
| FND-002 S&P 500 Index Fund | Medium | 70,720 | 38.92% |
| FND-003 Total Bond Market Fund | Low | 47,740 | 26.28% |

**Beneficiaries (outdated — names ex-spouse):**

| Policy | Beneficiary | Relationship | Share |
|--------|-------------|--------------|-------|
| POL-2026-1001 | Emily Carter *(ex-spouse)* | Spouse | 100% |
| POL-2026-1002 | Emily Carter *(ex-spouse)* | Spouse | 100% |

---

## Port Summary

| App | Port | Protocol |
|-----|------|----------|
| LifePensionsMCPServer | 9982 | HTTP (MCP), `/life-pensions` |
| LifePensionsA2AServers — update_beneficiary | 9983 | HTTP (A2A) |
| LifePensionsA2AServers — change_contribution | 9984 | HTTP (A2A) |
| LifePensionsA2AServers — fund_switch | 9985 | HTTP (A2A) |
| LifePensionsA2AServers — submit_claim | 9986 | HTTP (A2A) |
| LifePensionsA2AServers — adviser_callback | 9987 | HTTP (A2A) |
| LifePensionsA2AServers — send_confirmation_email | 9988 | HTTP (A2A) |
| LifePensionsAIOrchestrator | 9600 | WebSocket, `/lifepensions` |

**Start order:** MCP Server → A2A Servers → Orchestrator, then connect the chatbot UI.

---

## Supporting Files

| File | Description |
|------|-------------|
| `database.sql` | PostgreSQL schema with 10 tables and demo data |
| `reset_data.sql` | Data reset script (today-relative dates; clears agent-written rows) |
| `prompts.md` | Demo prompts organized by scenario |
| `manual-steps.md` | Step-by-step setup and deployment instructions |

---

## Security & Production Notes

This is the Phase-1 working demo. For production the design calls for: TLS on all endpoints (WebSocket + MCP + A2A), Bearer-token auth on the MCP Server, strong member authentication before any write action, API-gateway rate limiting, an on-premises LLM for data residency, and swapping the PostgreSQL-backed tools for real policy administration, pensions/investment platform and claims APIs.
