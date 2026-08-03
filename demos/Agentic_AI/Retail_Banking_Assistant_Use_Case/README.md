# Retail Banking Assistant — Agentic AI Use Case

An agentic AI system built on TIBCO Flogo that lets a **retail banking customer** self-serve in natural
language over a chat window. The customer can check balances, transactions, cards and loans, **dispute a
suspicious transaction**, **block a lost or stolen card**, and receive a **confirmation email** — with no
call-center agent. An orchestrator agent classifies intent and routes each request to read-only MCP tools
or to write-workflow A2A agents, all backed by PostgreSQL.

Modeled on the reference `Hospital_AI-Agent_Use_Case` / `Telecom_Invoice_Chatbot_Use_Case` and produced
by the `agentic-ai-use-case` skill.

---

## Architecture

```
                       ┌──────────────────────────┐
                       │   Agentic Chatbot UI      │
                       │  (demos/Agentic_AI/Chatbot)│
                       └────────────┬──────────────┘
                                    │ WebSocket  ws://localhost:8084/ws/chat
                                    ▼
                    ┌───────────────────────────────┐
                    │   BankingAIOrchestrator        │
                    │   (#wsserver + AI Agent)       │
                    │   Port 8084                     │
                    └───┬───────────────────────┬────┘
             MCP (HTTP) │                        │ A2A
                        ▼                        ▼
         ┌──────────────────────┐   ┌───────────────────────────────────────┐
         │  BankingMCPServer     │   │  BankingA2AServers                     │
         │  7 read-only tools    │   │  dispute_transaction_agent  :8710      │
         │  Port 9096            │   │  block_card_agent           :8711      │
         │  /retail-banking      │   │  send_confirmation_email    :8712      │
         └──────────┬───────────┘   └──────────────────┬────────────────────┘
                    │                                   │  (+ SMTP for email)
                    └───────────────┬───────────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │   PostgreSQL (banking)│
                         └─────────────────────┘
```

- **MCP Server** = read-only lookups. Stateless, safe to retry; the LLM picks a tool by intent and filters rows.
- **A2A Servers** = write workflows (file a dispute = INSERT, block a card = UPDATE, send email = SMTP).
- **Orchestrator** = the AI brain. WebSocket chat, decides intent, calls MCP tools or hands off to A2A agents, confirms before writes.

---

## Flogo Apps

### 1. `BankingMCPServer.flogo` — MCP Server (port 9096, path `/retail-banking`)

| Tool | Returns | Table |
|------|---------|-------|
| **GetCustomerProfile** | name, phone, email | `customers` |
| **GetAccounts** | account_type, balance, currency, status | `accounts` |
| **GetTransactions** | date, description, merchant, amount, type, category, status | `transactions` |
| **GetCards** | card_number_masked, type, network, status, expiry, credit_limit | `cards` |
| **GetLoans** | loan_type, outstanding_balance, interest_rate, emi_amount, next_due_date | `loans` |
| **GetDisputes** | transaction_id, reason, status, estimated_resolution | `disputes` |
| **GetBranches** | branch_name, address, city, state, phone, hours | `branches` |

Each tool is a flow `#noop → #query (SELECT * FROM <table>) → #actreturn`. All read-only.

### 2. `BankingA2AServers.flogo` — A2A Servers (write workflows)

| Agent | Port | Tool | Workflow |
|-------|------|------|----------|
| **dispute_transaction_agent** | 8710 | `file_transaction_dispute` | validate transaction (`#query`) → **INSERT** into `disputes` (status OPEN, +7 business days) |
| **block_card_agent** | 8711 | `block_card` | **UPDATE** `cards` SET status = 'BLOCKED' |
| **send_confirmation_email** | 8712 | `send_confirmation_email` | `#sendmail` (Gmail SSL:465) → sends one confirmation to the preconfigured mailbox |

### 3. `BankingAIOrchestrator.flogo` — Orchestrator (WebSocket port 8084, path `/ws/chat`)

`#wsserver → #agentactivity → #wswritedata`. The AI Agent lists the MCP server under `mcpServers` and
all three A2A agents under `remoteAgents`, with a system prompt that: identifies the customer by
`customer_id`, routes read questions to the right MCP tool, requires **confirmation before any write**,
generates a `DSP-2026-XXXX` id for disputes, sends the confirmation email **once, last, only if asked**,
and **declines out-of-scope** requests (loan approvals, investment advice, opening/closing accounts,
external wires).

---

## Database (`banking`, 7 tables)

| Table | Purpose | Rows (seed) |
|-------|---------|:-----------:|
| `customers` | master record keyed by `customer_id` (CUST-2026-NNNNN) | 7 |
| `accounts` | checking/savings/credit balances | 9 |
| `transactions` | transaction history (incl. the unrecognized charge) | 15 |
| `cards` | debit/credit cards — **block target** | 7 |
| `loans` | home/auto/personal loans | 3 |
| `disputes` | **write target** (INSERT); 1 pre-seeded OPEN dispute | 1 |
| `branches` | branch/ATM reference | 5 |

**Key demo personas**

| Customer | Name | Highlights |
|----------|------|-----------|
| CUST-2026-00101 | James Miller | Checking+Savings, ACTIVE debit card, HOME loan, **unrecognized $249.99 QUICKPAY charge (TXN-50003)** → dispute + block + full flow |
| CUST-2026-00102 | Olivia Davis | Checking, ACTIVE credit card, personal loan |
| CUST-2026-00103 | William Garcia | Savings only, debit card |
| CUST-2026-00104 | Sophia Martinez | **1 pre-seeded OPEN dispute (DSP-2026-0001)** → dispute-status lookup |
| CUST-2026-00105 | Benjamin Lee | Card **already BLOCKED** (edge), auto loan |
| CUST-2026-00106 | Emma Johnson | Checking+Savings |
| CUST-2026-00107 | Michael Brown | Card **EXPIRED** (edge) |

```sql
-- create the database, then load schema + data
psql -U postgres -d banking -f database.sql
-- reset to a clean, current-dated baseline before each demo run
psql -U postgres -d banking -f reset_data.sql
```

---

## Prerequisites

- **TIBCO Flogo Enterprise** v2.26.5 (to import/build the three `.flogo` apps).
- **PostgreSQL** 14+ with a database named `banking`.
- An **OpenAI API key** (the apps ship configured for `gpt-5.5`; the key is an app property).
- A **Gmail App Password** for the confirmation-email agent (SMTP `smtp.gmail.com:465` SSL).
- The **chatbot UI** in `demos/Agentic_AI/Chatbot`.

---

## Setup & Run

### 1. Database
```sql
CREATE DATABASE banking;
psql -U postgres -d banking -f database.sql
psql -U postgres -d banking -f reset_data.sql
```

### 2. Import & configure the three apps
Import each `.flogo` into Flogo Enterprise and set its app properties:

**BankingMCPServer** (start first)
| Property | Value |
|---|---|
| `PostgreSQL.PostgresConn.Host/Port/User/Password` | your PostgreSQL connection |
| `PostgreSQL.PostgresConn.Database_Name` | `banking` |
| `MCP_SERVER_PORT` | `9096` |

**BankingA2AServers** (start second)
| Property | Value |
|---|---|
| `AgenticAI.OpenAIConn.API_Key` | your OpenAI API key |
| `LLM_Model` | `gpt-5.5` |
| `PostgreSQL.PostgresConn.*` | your PostgreSQL connection, DB `banking` |
| `Email_Username` / `Email_App_Password` / `To_Email` | Gmail sender / app password / recipient mailbox |
| `DisputeTransaction_A2AServer_PORT` / `BlockCard_A2AServer_PORT` / `SendEmail_A2AServer_PORT` | `8710` / `8711` / `8712` |

**BankingAIOrchestrator** (start last)
| Property | Value |
|---|---|
| `AgenticAI.OpenAIConn.API_Key` | your OpenAI API key |
| `LLM_Model` | `gpt-5.5` |
| WebSocket port (trigger) | `8084` |

> The orchestrator's connections point at `http://localhost:9096/retail-banking` (MCP) and
> `http://localhost:8710|8711|8712` (A2A). If you change any port, update the matching connection URL.

### 3. Start order
**MCP (9096) → A2A (8710/8711/8712) → Orchestrator (8084).**

### 4. Chatbot UI
```bash
cd demos/Agentic_AI/Chatbot
npm install
npm start
```
Open http://localhost:3000, paste the orchestrator WebSocket URL, and click **Connect**:
```
ws://localhost:8084/ws/chat
```

### 5. Run the demo
Use the prompts in [prompts.md](prompts.md). Reset between runs with `reset_data.sql`.

---

## Demo scenarios (headline walkthroughs)

1. **Balance & history:** *"I'm CUST-2026-00101, what are my balances and recent transactions?"* → GetAccounts + GetTransactions.
2. **Dispute a charge:** *"I don't recognize a $249.99 QUICKPAY charge, dispute it."* → assistant finds TXN-50003, confirms, files a new dispute (OPEN, +7 days).
3. **Block a card:** *"I lost my debit card, block it."* → assistant finds CARD-9001, confirms, sets it BLOCKED.
4. **Action + email:** *"Dispute the charge and email me a confirmation."* → dispute filed, then one confirmation email.
5. **Dispute status:** *"What's the status of my dispute?"* (CUST-2026-00104) → GetDisputes returns DSP-2026-0001 OPEN.
6. **Out of scope:** *"Approve me for a loan / which stocks should I buy?"* → politely declined.

---

## Ports

| App | Port(s) | Path |
|-----|---------|------|
| BankingMCPServer | 9096 | `/retail-banking` |
| BankingA2AServers | 8710 (dispute), 8711 (block card), 8712 (email) | — |
| BankingAIOrchestrator | 8084 | `/ws/chat` |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Orchestrator can't reach tools/agents | Confirm MCP (9096) and A2A (8710-8712) apps are running **before** the orchestrator; check the connection `serverUrl`s match the ports. |
| MCP tool returns nothing | Verify the `banking` DB is loaded and `PostgreSQL.PostgresConn.Database_Name = banking`. |
| Dispute/block "fails" | Check the A2A app's PostgreSQL connection; confirm the `transaction_id` / `card_id` exists (run `reset_data.sql`). |
| No email received | Verify `Email_Username` + `Email_App_Password` (Gmail App Password) and that `To_Email` is set; port 465 SSL. |
| Dispute status shows stale dates | Re-run `reset_data.sql` (dates are relative to today). |

---

## Notes & production considerations

- Demo data is fictional (USD / US personas). Card numbers are masked; no real PII.
- For production: put TLS on all endpoints, add bearer-token auth and rate limiting, use an on-prem/data-residency LLM, and replace the direct PostgreSQL access with the bank's core-banking APIs. Add a fund-transfer/bill-pay A2A agent if payment write-flows are needed (intentionally out of scope here).
