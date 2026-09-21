# Auto Insurance Policyholder Assistant — Demo Prompts

Chat prompts for the WebSocket orchestrator (`ws://localhost:9700/auto-insurance`).
They are grouped so you can show the **core idea of the demo**: structured *facts* come from
the PostgreSQL MCP tools, while policy *language* ("is X covered?", exclusions, definitions)
comes from **RAG** over the policy-wording PDFs (`search_policy_wording` → OpenAI vector store).

> Run order reminder: start the **RAG ingestion** app once (`POST http://localhost:9720/ingest`)
> **before** any policy-wording question, then start MCP → A2A → Orchestrator. See `README.md`.

Personas (give the assistant the **policy number**; it never needs internal ids):

| Policyholder | Policy | Tier | Notable state |
|---|---|---|---|
| Michael Carter | `POL-AUTO-100001` | Comprehensive | flagship, NCD protected, Windshield + Roadside |
| Sarah Johnson | `POL-AUTO-100002` | Comprehensive (monthly) | windshield claim `CLM-2026-5001` *Under Review*, a payment *Due* |
| David Martinez | `POL-AUTO-100003` | Third Party Fire & Theft | renewal in ~15 days, payment *Due* |
| Emily Chen | `POL-AUTO-100004` | Third Party Only | narrowest cover |
| James Wilson | `POL-AUTO-100005` | Comprehensive + add-ons | Zero Depreciation + Hire Car; *Pending Renewal* (~5 days); theft claim `CLM-2026-5003` *Approved* |
| Olivia Brown | `POL-AUTO-100006` | Comprehensive | *Lapsed*; a payment *Failed* |
| Daniel Lee | `POL-AUTO-100007` | Comprehensive | collision claim `CLM-2026-5002` *Settled* |

---

## 1. Structured facts — MCP DB tools (no RAG)

These should be answered from the database, not the PDFs.

- `Hi, I'm Michael Carter, policy POL-AUTO-100001. Can you give me a summary of my policy?`
  → `get_policy_details` (+ `get_vehicles`): Comprehensive, Active, premium, renewal date, NCD.
- `What car do I have insured and what's it valued at?`
  → `get_vehicles`: Toyota Camry 2021, reg 7ABC123, market value.
- `How much is my excess if I claim for own damage? And for the windshield?`
  → `get_coverages`: Own Damage excess $500, Windshield excess $100. *(Numbers = DB, not RAG.)*
- `When does my policy renew and what's my premium?`
  → `get_policy_details`.
- `I'm Sarah Johnson, POL-AUTO-100002 — do I have any payments due?`
  → `get_payments`: one *Due* installment.
- `What's the status of my claim?` (Sarah)
  → `get_claims`: `CLM-2026-5001` windshield, *Under Review*.
- `I'm James Wilson, POL-AUTO-100005. What add-ons do I have?`
  → `get_coverages`: Zero Depreciation, Hire Car, Windshield, Roadside Assistance.

## 2. Policy language — RAG (`search_policy_wording`)

These must trigger the RAG tool; the assistant should **quote/paraphrase the retrieved clause**
and append the policyholder's product tier to the search query.

- `Does my comprehensive policy cover a cracked windshield, and will it affect my no-claim discount?`
  → RAG: windshield/glass cover; glass-only excess ~$100; glass-only claims **don't** affect NCD.
- `If I drive through a flooded road and my engine is damaged, am I covered?`
  → RAG: flood/water-ingress **exclusion** for knowingly driving through flood water; Natural
     Catastrophe endorsement note.
- `Am I covered to drive a friend's car?`
  → RAG: **Driving Other Cars** extension — third-party only, no own-damage for the other car.
- `I'm going on a road trip to Canada — does my cover apply there?`
  → RAG: **Territorial limits** — US + Canada touring up to 60 days.
- `How does NCD protection work — how many claims can I make?`
  → RAG: up to 2 claims in any 3-year period without losing the discount; premium may still rise.
- `I'm James Wilson, POL-AUTO-100005 — what does zero depreciation actually pay for?`
  → RAG: waives depreciation on replaced parts, subject to excess; vehicle-age limit.
- `I'm Emily Chen, POL-AUTO-100004. Is accidental damage to my own car covered?`
  → RAG (Third Party Only / TPFT wording): **no** own-damage collision cover; suggest upgrade.
- `What documents do I need to file a theft claim and how long does it take?`
  → RAG: Claims Procedure Guide — documents + timelines (theft investigation up to ~30 days).

## 3. Facts + language together (the money shot)

One question that needs **both** a DB lookup and the wording:

- `I'm Michael Carter, POL-AUTO-100001. A stone cracked my windshield — how much will I pay out
   of pocket, and will it hurt my no-claim discount?`
  → `get_coverages` for the **$100 windshield excess** (DB) **and** `search_policy_wording` for the
     rule that glass-only claims **don't** affect NCD (RAG). Answer combines both.

## 4. Write actions — A2A agents (assistant confirms first)

- **file_claim**
  `I'm Michael Carter, POL-AUTO-100001. I need to file a claim — someone reversed into my rear
   bumper yesterday, damage looks about $1,800.`
  → assistant confirms details, then `file_claim` (derives policyholder_id from the policy number,
     generates `CLM-2026-XXXX`, status *Submitted*). Verify with: `What's the status of my new claim?`
- **request_callback**
  `Can someone call me back about protecting my no-claim discount? Tomorrow afternoon works.`
  → `request_callback` (topic + preferred time; new `CB-2026-XXXX`).
- **update_contact_details**
  `Please update my phone number to +1-415-555-0199.` (or email / address)
  → `update_contact_details` (UPDATE `policyholders` + audit row in `contact_change_log`).
- **send_confirmation_email** (only if asked, once, last)
  `Great — can you email me a confirmation of everything we just did?`
  → `send_confirmation_email` (subject + body summary).

## 5. Multi-step / combined

- `I'm James Wilson, POL-AUTO-100005. My renewal is coming up — remind me what I'm paying, what
   add-ons I have, whether zero depreciation is worth keeping, and then have an advisor call me
   Thursday morning. Email me a summary too.`
  → `get_policy_details` + `get_coverages` (facts) → `search_policy_wording` (zero-dep wording) →
     `request_callback` → `send_confirmation_email` (once, at the end).

## 6. Guardrail / scope checks (assistant should decline or clarify)

- `Give me a cheaper quote and switch me to that plan right now.` → out of scope (underwriting/pricing).
- `Change my brother's policy address.` → decline (only the requesting policyholder's own policy).
- `What stocks should I buy with my premium savings?` → decline (no financial/investment advice).
- `File 10 claims for me quickly.` → refuse looping; confirm each write; max 3 attempts per task.

---

### Notes for the presenter
- The split is the story: **"how much is my excess" (DB number) vs "does my policy cover it" (PDF
  language)**. Show one of each back-to-back, then the §3 combined question.
- After a write, re-run the matching read (`get_claims`, etc.) to show the new row.
- `reset_data.sql` restores the demo (undoes agent writes; preserves the ingested vector store id).
