# Aerospace & Defense — MRO & AOG Operations Assistant — Demo Prompts

Talk to the orchestrator over WebSocket at `ws://<host>:8085/mro`. Prompts are grouped
**MCP-only** (read lookups) → **MCP + A2A** (actions) → the **flagship multi-step AOG resolution**.
All prompts are grounded in the seed data (`database.sql` / `reset_data.sql`), so answers are
deterministic. Run `reset_data.sql` between runs to undo agent writes.

---

## 1. Fleet & Airworthiness Lookup (MCP Only)

```
What's the status of tail AD-0142?
```
```
Which aircraft are AOG right now?
```
```
Show me everything that's grounded or in maintenance.
```
```
When is N738MA's next check due, and what type is it?
```
```
List the defense platforms in the fleet and their bases.
```

---

## 2. Open Work & Maintenance History (MCP Only)

```
What work orders are open on AD-0142?
```
```
Show me every work order that's awaiting parts.
```
```
What maintenance has been completed on AD-0177?
```
```
Who is assigned to WO-2026-00104, and what's its status?
```
```
What's the maintenance history on N738MA?
```

---

## 3. Parts & Technicians (MCP Only)

```
Do we have hydraulic pump PN-4471-A in stock?
```
```
Which parts are at or below their reorder level?
```
```
Is the main landing gear actuator PN-8830-C available, and what's the lead time?
```
```
Who's a hydraulics-certified technician available at Edwards AFB?
```
```
Is Marcus Reid (TECH-101) available right now?
```
```
Show me the status of part order PO-2026-0001.
```

---

## 4. Schedule Maintenance (MCP + A2A write → work_orders)

```
N738MA is coming up on its A-check — open a scheduled work order for it, due next Friday.
```
```
Open an unscheduled work order on N512MA for an oil-pressure sensor replacement, priority URGENT, due in 3 days.
```
```
AD-0203 needs a 100-hour inspection scheduled — routine priority, due in two weeks.
```

Expect the agent to validate the tail exists, then confirm a new `WO-2026-002xx` with status OPEN.

---

## 5. Order / Expedite a Part (MCP + A2A write → part_orders)

```
We're short on hydraulic pump PN-4471-A for AD-0142 — order 2 and expedite it.
```
```
Raise a routine order for one APU starter PN-3315-E for N738MA against WO-2026-00107.
```
```
Order a cabin pressurization controller PN-6621-G for N901MA, expedite.
```

Expect the agent to flag when quantity on hand is at/below reorder level, then confirm a new
`PO-2026-01xx` with status ORDERED.

---

## 6. Dispatch a Technician (MCP + A2A write → work_orders)

```
Assign Marcus Reid (TECH-101) to WO-2026-00101.
```
```
Dispatch a technician to the 100-hour inspection WO-2026-00103.
```
```
Put David Okafor (TECH-103) on WO-2026-00105.
```

Expect the agent to validate the technician is available, then move the work order to IN_PROGRESS.

---

## 7. Send a Confirmation Email (A2A → SMTP + notification_log)

```
Email operations a summary of the AD-0142 AOG status.
```
```
Send a confirmation that the hydraulic pump for AD-0142 has been expedited.
```

The email goes to the configured operations mailbox and is recorded in `notification_log`.

---

## 8. ⭐ Flagship — Full AOG Resolution (MCP + all A2A, multi-step)

One prompt, chained end to end. The orchestrator checks the AOG record and aircraft, checks pump
stock, expedites the part, dispatches a certified available technician, and emails ops a summary.

```
Tail AD-0142 is AOG at Edwards with a No.2 hydraulic system pump failure — figure out what we need and resolve it.
```

Or drive it turn by turn:

```
Turn 1: What's going on with AD-0142? Pull the AOG incident.
Turn 2: Do we have the hydraulic pump it needs in stock?
Turn 3: It's below reorder — expedite two of them against WO-2026-00101.
Turn 4: Who's hydraulics-certified and available at Edwards? Dispatch them to WO-2026-00101.
Turn 5: Email operations a summary of everything we just did.
```

Expected chain: `GetAOGIncidents` + `GetAircraft` → `GetPartsInventory` (PN-4471-A below reorder) →
`order_part_agent` (EXPEDITE) → `GetTechnicians` (TECH-101 Marcus Reid, AVAILABLE, C-130J/Hydraulics)
→ `dispatch_technician_agent` (WO-2026-00101 → IN_PROGRESS) → `send_confirmation_email_agent`.

---

## 9. Exception & Out-of-Scope (graceful failure)

### Part out of stock / long lead
```
Order the main landing gear actuator PN-8830-C for AD-0198 — expedite.
```
_(PN-8830-C is out of stock, 45-day lead; expect the agent to say so and suggest the in-transit order PO-2026-0001.)_

### Unknown tail / part / WO
```
What's the status of tail ZZ-9999?
```
```
Order 3 of part PN-0000-X for N738MA.
```
```
Assign a technician to WO-2026-99999.
```

### No suitable technician
```
Dispatch an avionics-certified technician who's available at Edwards right now.
```
_(Avionics techs are at Meridian Field / ON_SHIFT / OFF; expect the agent to report none available and suggest the next best option.)_

### Out of scope
```
Book me a flight to Edwards.
```
```
What's the weather at Palmdale tomorrow?
```
_(Expect a polite decline — outside fleet maintenance / MRO / AOG operations.)_

---

## 10. Multi-Turn Conversation (context carry-over)

```
Turn 1: Which aircraft are AOG or grounded right now?
Turn 2: Tell me more about AD-0142 — what's open on it?
Turn 3: Do we have the part its AOG work order is waiting on?
Turn 4: Expedite two of them against WO-2026-00101.
Turn 5: Dispatch Marcus Reid to that work order.
Turn 6: Email operations a summary of what we did for AD-0142.
```
