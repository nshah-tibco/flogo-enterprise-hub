# Demo Prompts — Real Estate Lead Engagement Assistant

Paste these into the chatbot UI connected to `ws://localhost:9590/realestate`.
Prompts are grouped by scenario. Run `reset_data.sql` before a fresh run so dates and
agent-written rows (bookings, tasks, stage changes) start clean.

> The assistant identifies the prospect by **lead id** (`LEAD-2026-NNNNN`), email, or phone,
> then routes to read-only **MCP tools** or write **A2A agents**. It **confirms before any write**.

---

## 0. Identify yourself (start every session here)

```
Hi, I'm lead LEAD-2026-00001. What do you have on file for me?
```
→ `GetLeadProfile`. The assistant greets Ava Thompson, recalls her saved criteria
(3bd/2ba, Austin 78704, $500k–$750k, 0–3 month timeline) and her assigned agent.

You can also identify by email or phone:
```
It's me, ava.thompson@example.com
```
```
My number is +1-512-555-1001
```

---

## 1. Profile & saved criteria  (read → GetLeadProfile / GetLeadActivity)

```
What search criteria do you have saved for me?
```
```
What have I been looking at recently?
```
→ `GetLeadActivity` (searches, viewed/saved listings, emails opened).

---

## 2. Search listings  (read → SearchListings, LLM filters)

```
Show me 3-bedroom single-family homes under $750k in Austin 78704.
```
→ `SearchListings` filtered to her area/budget → **512 Bouldin Ave ($689k)** and
**908 Live Oak St ($725k)**.

```
Tell me more about 512 Bouldin Ave.
```
```
Any condos under $450k in 78745?
```
→ 245 Sunset Trl #12 ($415k), 77 Riverside Dr #210 ($389k).

---

## 3. Market insight  (read → GetAreaMarketInsights)

```
How's the market in Austin 78704 right now?
```
→ median price, avg days on market, active inventory, $/sqft, YoY change.

```
Is 78745 a buyer's or seller's market?
```

---

## 4. Book a property showing — the full flow  (write → book_property_showing, then update_lead_stage)

```
I'd like to tour 512 Bouldin Ave this Saturday at 2pm.
```
The assistant finds the listing (Active), **confirms the details**, then on your OK:
1. calls **`book_property_showing`** → INSERT into `appointments` (status `Requested`,
   agent derived from the lead → AGT-001), returns an `APT-#####` id;
2. calls **`update_lead_stage`** → advances Ava `Nurturing → Active` and logs a `Stage Change`;
3. offers a **confirmation email**.

Confirm-before-write in action:
```
Yes, please book it — and email me a confirmation.
```
→ `send_confirmation_email` (subject + body composed from the booking).

Verify:
```
Do I have any showings scheduled?
```
→ `GetLeadAppointments` shows the new tour.

---

## 5. Recommendations by email  (write → send_property_recommendations + send_confirmation_email)

Identify as a buyer, then:
```
Email me a few homes that match what I'm looking for.
```
→ `send_property_recommendations` logs a `Recommendation Sent` activity with the curated
`listing_ids`, then `send_confirmation_email` sends them. Confirm first when asked.

---

## 6. Agent follow-up  (read GetAssignedAgent → write log_followup_task)

```
Can you have my agent call me tomorrow afternoon?
```
→ `GetAssignedAgent` (who the agent is) → confirm → **`log_followup_task`**
(`task_type = Call`, `due_date` = tomorrow, agent derived from the lead) → `TSK-#####`.

```
Text me next week about new listings in my price range.
```
→ `log_followup_task` (`task_type = Text`).

---

## 7. Appointment lookup for a lead who already has one  (read → GetLeadAppointments)

```
Hi, I'm LEAD-2026-00002. What tours do I have booked?
```
→ Marcus Reed already has a **Confirmed** showing at 1330 Forest Creek Dr (pre-seeded).

---

## 8. Activity lookup for a nurtured lead  (read → GetLeadActivity)

```
I'm LEAD-2026-00008 — what have you sent me lately?
```
→ Noah Bennett has a pre-seeded `Recommendation Sent` + `Email Opened`.

---

## 9. Edge cases & guardrails (should be handled gracefully)

**Lead under contract — don't casually book new tours:**
```
I'm LEAD-2026-00005. Book me three more showings this weekend.
```
→ Sofia is `Under Contract`; the assistant should note that and confirm intent rather than bulk-booking.

**Cold / lost lead — gentle, limited re-engagement:**
```
I'm LEAD-2026-00006. Show me luxury homes over $1M.
```
→ Liam is `Lost` and out of budget for the area; re-engage briefly, don't over-promise.

**Out of scope — politely declined (offer an agent follow-up instead):**
```
Can you lower the price on 512 Bouldin Ave for me?
```
```
Give me legal advice on the purchase contract.
```
```
What mortgage rate should I lock in?
```
```
Show me another buyer's file.
```
→ Declined: no price/offer commitments, no legal/mortgage/financial advice, no editing MLS
data, no access to other leads' records.

**Non-existent listing / lead — no hallucinated ids:**
```
Book me a tour of 999 Nowhere Ln.
```
→ The assistant should say it can't find that listing rather than invent one.

---

## Reset between runs

```bash
psql -U postgres -d realestate -f reset_data.sql
```
Restores the 8 leads / 12 listings / market stats, clears agent-written rows, resets the
`APT-#####` and `TSK-#####` sequences, and refreshes volatile dates to “today.”
