# Specification: Retail Banking Self-Service Assistant

> Worked example of the [agentic-ai-use-case spec template](../../../skills-library/.claude/skills/agentic-ai-use-case/references/use-case-spec-template.md),
> reverse-engineered from this use case. This is the **spec** (WHAT/WHY) you would hand to the
> `agentic-ai-use-case` skill to (re)generate the Retail Banking use case as the standard 3-app pattern
> (MCP read tools + A2A write agents + WebSocket orchestrator). Technology choices (Flogo, MCP, A2A,
> ports, SQL) are intentionally **not** specified here — the skill owns those.

## 1. Intent (WHY)
A retail banking customer chats in natural language to **self-serve everyday banking** end to end:
check account balances and recent transactions, review cards and loans, **dispute a transaction they
do not recognize**, **block a lost or stolen card**, and optionally receive a **confirmation email** —
replacing a call to the contact center for routine inquiries and low-risk service actions.

## 2. Actors & identification
- **Primary actor:** retail banking customer (self-service).
- **Identifier:** `customer_id` — format `CUST-2026-NNNNN` (e.g. `CUST-2026-00101`).
- **Locale / currency:** en-US; **USD**.

## 3. User scenarios (Given/When/Then)
- **S1 (read):** Given customer `CUST-2026-00101` (Checking + Savings), When they ask *"What are my account balances?"*, Then the assistant returns each account's type, masked number, balance, and currency.
- **S2 (read):** Given a customer with recent activity, When they ask *"Show my recent transactions"*, Then the assistant lists date, merchant, amount, type, and status for their transactions.
- **S3 (action + confirm — exception path):** Given `CUST-2026-00101` has an **unrecognized** `QUICKPAY*XYZ` charge of $249.99, When they ask to dispute it, Then the assistant finds the exact transaction, shows merchant + amount, asks for confirmation, and on confirmation **files a dispute** (status OPEN, ~7 business-day resolution) and reports the new dispute reference.
- **S4 (action + confirm):** Given `CUST-2026-00101` has an active debit card, When they say *"I lost my card, block it"*, Then the assistant identifies the card, confirms, and **sets it to BLOCKED**, noting a replacement can be requested.
- **S5 (status read):** Given `CUST-2026-00104` has an existing open dispute, When they ask *"What's the status of my dispute?"*, Then the assistant returns the dispute reference, disputed transaction, status, and estimated resolution.
- **S6 (end-to-end + notification):** When the customer asks to *"dispute the charge and email me a confirmation"* (or *"block my card and email me"*), Then the assistant performs the action and sends **one** confirmation email summarizing it.
- **S7 (edge):** Given `CUST-2026-00105` whose card is already BLOCKED, or `CUST-2026-00107` whose card is EXPIRED, Then the assistant states the current status and takes no redundant action.

## 4. Functional requirements

### 4a. Information lookups (read-only) → MCP tools
| Lookup | Input | Returns | Source entity |
|---|---|---|---|
| Get customer profile | customer_id | first_name, last_name, phone, email | customers |
| Get accounts | customer_id | account_type, account_number, balance, currency, status | accounts |
| Get transactions | customer_id / account_id | txn_date, description, merchant, amount, type, category, status | transactions |
| Get cards | customer_id | card_number_masked, card_type, network, status, expiry, credit_limit | cards |
| Get loans | customer_id | loan_type, outstanding_balance, interest_rate, emi_amount, next_due_date, status | loans |
| Get disputes | customer_id / dispute_id | transaction_id, reason, status, estimated_resolution | disputes |
| Get branches | city / state | branch_name, address, city, state, phone, hours | branches |

### 4b. Actions / workflows (state-changing) → A2A agents
| Action | Inputs | Validation / steps | Result (output) | Guardrails |
|---|---|---|---|---|
| File a transaction dispute | customer_id, transaction_id, reason, generated dispute_id | look up the transaction; create a dispute record | new dispute (status OPEN, est. resolution ~7 business days) | confirm before writing; identify the exact transaction first |
| Block a card | card_id, customer_id, reason | set card status to BLOCKED | card can no longer be used; replacement can be requested | confirm before writing; identify the exact card first |
| Send confirmation email | subject, body (email optional) | compose a summary of the action taken | one email dispatched to the configured mailbox | invoke once, last, only if the customer asks |

## 5. Domain entities & data → tables
| Entity | Key fields | Relationships | Read / written by |
|---|---|---|---|
| customers | customer_id (PK), first/last name, phone, email | — | profile lookup; email recipient |
| accounts | account_id (PK), customer_id, account_number, account_type, balance, currency, status | → customers | balance/account lookup |
| transactions | transaction_id (PK), account_id, customer_id, txn_date, description, merchant, amount, txn_type, category, status | → accounts, customers | history lookup; dispute source |
| cards | card_id (PK), customer_id, account_id, card_number_masked, card_type, network, status, expiry, credit_limit | → customers, accounts | card lookup; **block (write/update)** |
| loans | loan_id (PK), customer_id, loan_type, principal, outstanding_balance, interest_rate, emi_amount, next_due_date, status | → customers | loan lookup |
| disputes | dispute_id (PK), customer_id, transaction_id, reason, status, estimated_resolution, last_update | → customers, transactions | dispute status lookup; **file dispute (write/insert)** |
| branches | branch_id (PK), branch_name, address, city, state, zip, phone, hours | — | reference lookup |

## 6. Seed-data scenarios
- `CUST-2026-00101` James Miller — Checking + Savings, **active debit card**, HOME loan, and an
  **unrecognized `QUICKPAY*XYZ` $249.99 charge** → full workflow (S1/S2/S3/S4/S6).
- `CUST-2026-00102` Olivia Davis — Checking, active credit card, personal loan; clean transactions.
- `CUST-2026-00103` William Garcia — Savings only, debit card, no loans.
- `CUST-2026-00104` Sophia Martinez — **one pre-seeded OPEN dispute** on a `GLOBAL*DIGITAL` charge → dispute-status lookup (S5).
- `CUST-2026-00105` Benjamin Lee — card **already BLOCKED** (edge, S7), auto loan.
- `CUST-2026-00107` Michael Brown — card **EXPIRED** (edge, S7).
- Target: ~7 customers with a realistic spread of accounts/cards/loans; ~15 transactions incl. at least
  one clear "unrecognized charge"; ~5 branches across US cities; the disputes table pre-seeded with
  exactly one open dispute and otherwise filled by the agent.

## 7. Acceptance criteria
- [ ] Account balances for `CUST-2026-00101` return both Checking and Savings with USD amounts.
- [ ] Transaction history for `CUST-2026-00101` includes the `QUICKPAY*XYZ` $249.99 charge.
- [ ] Filing a dispute for that charge inserts a new dispute row with status OPEN and an estimated resolution date.
- [ ] Blocking `CUST-2026-00101`'s active card sets its status to BLOCKED.
- [ ] Dispute-status lookup for `CUST-2026-00104` returns the pre-seeded OPEN dispute.
- [ ] A card that is already BLOCKED / EXPIRED is reported as-is with no redundant write.
- [ ] Actions confirm before writing; the confirmation email is sent at most once and only when requested.

## 8. Out of scope
Approving or applying for loans/credit; investment, financial, tax, or legal advice; opening or closing
accounts; wire transfers or payments to external parties; and anything beyond retail self-service
inquiries and the two low-risk service actions (dispute, card block) — politely declined.

## 9. Non-functional & constraints
- Real-time streaming chat; multi-turn session memory.
- **Privacy:** reveal only the requesting customer's own data; card numbers are masked; no sensitive data in logs.
- **Tone:** warm, professional, reassuring; consumer-friendly (no jargon).
- **Termination:** max 3 attempts per action; on failure, report what completed and what failed.
- **Security (target):** TLS on endpoints, bearer-token auth, rate limiting, on-prem/data-residency LLM.
- Reuse existing OpenAI / PostgreSQL / SMTP connection settings; database name `banking`.

## 10. Assumptions & open questions
- Dispute reference format `DSP-2026-XXXX` and a 7-business-day estimated resolution unless specified — confirm.
- Card block is a status change only; ordering a physical replacement is assumed out of scope (handled at a branch) — confirm.
- Confirmation-email recipient is a preconfigured service mailbox rather than the customer's own inbox for the demo — confirm.
- No fund-transfer / bill-pay write action in this cut (read + dispute + card block only) — confirm if payments should be added.

---
**Handoff:** *"Build the Retail Banking Self-Service use case from `demos/Agentic_AI/Retail_Banking_Assistant_Use_Case/banking.spec.md`."*
The skill frames it back, clarifies §10, plans the 3 apps, then generates the MCP server (7 lookups),
A2A agents (dispute transaction, block card, send email), `database.sql`, `reset_data.sql`, `prompts.md`,
and `README`, and verifies them.
