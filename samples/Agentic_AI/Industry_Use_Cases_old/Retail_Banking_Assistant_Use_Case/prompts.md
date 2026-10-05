# Retail Banking Assistant - Test Prompts

> **Before testing:** run `reset_data.sql` so dates are current and the only dispute on file is the
> pre-seeded one (`DSP-2026-0001`). Connect the chatbot UI to `ws://localhost:8084/ws/chat`.
>
> **Agents:** dispute_transaction_agent | block_card_agent | send_confirmation_email
> **MCP tools:** GetCustomerProfile · GetAccounts · GetTransactions · GetCards · GetLoans · GetDisputes · GetBranches

---

## Read-only scenarios (MCP tools)

### Test 1: Account balances (GetAccounts)
**Customer:** CUST-2026-00101 (James Miller) — Checking + Savings
```
I'm CUST-2026-00101. What are my account balances?
```
**Expected:** Checking (****3401) $4,250.75 and Savings (****3402) $18,500.00, both USD.

### Test 2: Recent transactions (GetTransactions)
```
Show me my recent transactions for CUST-2026-00101
```
**Expected:** Lists James's transactions including the suspicious `QUICKPAY*XYZ 872-555` $249.99 charge (TXN-50003).

### Test 3: Card details (GetCards)
```
What cards do I have on CUST-2026-00101?
```
**Expected:** CARD-9001 debit VISA, status ACTIVE, ending 1123.

### Test 4: Loan summary (GetLoans)
```
What's the balance and next payment on my home loan? Customer CUST-2026-00101
```
**Expected:** LOAN-3001 HOME, outstanding $285,400.50, rate 6.25%, EMI $2,103.45, next due ~11 days out.

### Test 5: Branch lookup (GetBranches)
```
Is there a branch in Chicago and what are its hours?
```
**Expected:** BR-003 The Loop, 233 S Wacker Dr, Chicago IL, Mon-Fri 9:00-17:00.

### Test 6: Dispute status (GetDisputes) — uses the pre-seeded row
**Customer:** CUST-2026-00104 (Sophia Martinez)
```
What's the status of my dispute? I'm CUST-2026-00104
```
**Expected:** DSP-2026-0001 on TXN-50009 (GLOBAL*DIGITAL 900-555, $129.00), status OPEN.

---

## Write scenarios (A2A agents) — confirm before the action fires

### Test 7: Dispute a transaction (dispute_transaction_agent)
**Customer:** CUST-2026-00101 (James Miller) — the unrecognized $249.99 charge
```
I don't recognize a $249.99 charge from QUICKPAY on my account. I'm CUST-2026-00101 — please dispute it.
```
**Expected:** Assistant finds TXN-50003 (QUICKPAY*XYZ 872-555, $249.99), asks James to confirm, then files a
dispute (new DSP-2026-XXXX) with status OPEN and ~7 business-day resolution. A new row appears in `disputes`.

### Test 8: Block a lost/stolen card (block_card_agent)
**Customer:** CUST-2026-00101 (James Miller) — active debit card
```
I lost my debit card. Please block it. Customer CUST-2026-00101.
```
**Expected:** Assistant finds CARD-9001 (ACTIVE), confirms, then blocks it. `cards.status` for CARD-9001
becomes BLOCKED. Assistant notes a replacement can be requested at a branch.

### Test 9: Dispute + confirmation email (dispute_transaction_agent + send_confirmation_email)
**Customer:** CUST-2026-00101 (James Miller)
```
Dispute the $249.99 QUICKPAY charge on CUST-2026-00101 and email me a confirmation with the details.
```
**Expected:** Files the dispute, then sends exactly ONE confirmation email summarizing the dispute
(dispute ID, transaction, status OPEN, resolution timeframe).

### Test 10: Block card + confirmation email (block_card_agent + send_confirmation_email)
**Customer:** CUST-2026-00101 (James Miller)
```
My card was stolen — block CARD-9001 for CUST-2026-00101 and send me an email confirmation.
```
**Expected:** Blocks CARD-9001, then sends one confirmation email with the block details and replacement steps.

---

## Edge cases

### Test 11: Card already blocked
**Customer:** CUST-2026-00105 (Benjamin Lee) — CARD-9005 is already BLOCKED
```
Block my card CARD-9005, I'm CUST-2026-00105
```
**Expected:** Assistant notes the card is already BLOCKED (no change needed) or re-affirms the blocked status.

### Test 12: Expired card
**Customer:** CUST-2026-00107 (Michael Brown) — CARD-9007 is EXPIRED
```
Show my cards, customer CUST-2026-00107
```
**Expected:** CARD-9007 shown as EXPIRED (03/25); assistant may suggest requesting a renewal.

### Test 13: Transaction not found
```
Dispute transaction TXN-99999 for CUST-2026-00101
```
**Expected:** Assistant reports it could not find that transaction and does not file a dispute.

---

## Out-of-scope (assistant should politely decline)

### Test 14: Loan approval
```
Can you approve me for a $20,000 personal loan?
```
**Expected:** Declines — loan approvals/applications are out of scope. States what it can help with.

### Test 15: Investment advice
```
Which stocks should I buy this month?
```
**Expected:** Declines — investment/financial advice is out of scope.

### Test 16: External wire transfer
```
Wire $5,000 to an account at another bank for me.
```
**Expected:** Declines — external wires/payments are out of scope.

---

## Quick reference — agent coverage

| Test | GetAccounts | GetTransactions | GetCards | GetLoans | GetBranches | GetDisputes | dispute | block_card | email |
|------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | x | | | | | | | | |
| 2 | | x | | | | | | | |
| 3 | | | x | | | | | | |
| 4 | | | | x | | | | | |
| 5 | | | | | x | | | | |
| 6 | | | | | | x | | | |
| 7 | | x | | | | | x | | |
| 8 | | | x | | | | | x | |
| 9 | | x | | | | | x | | x |
| 10 | | | x | | | | | x | x |
| 11 | | | x | | | | | (noop) | |
| 12 | | | x | | | | | | |
| 13 | | x | | | | | (declined) | | |
| 14-16 | | | | | | | | | | (out of scope) |
