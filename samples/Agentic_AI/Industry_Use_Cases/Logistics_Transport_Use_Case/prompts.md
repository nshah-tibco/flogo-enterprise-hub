# Demo prompts — Logistics / Transport Shipper Assistant

Connect a WebSocket client to `ws://<host>:9690/logistics` and paste these.
Group by scenario. Flagship customer: **Acme Retail Ltd** (`CUST-LOG-1001`).
Run `reset_data.sql` between runs to clear agent-written rows.

---

## 1. Track a shipment (MCP: TrackShipment / GetShipments)

- `Where is my shipment TRK-2026-0002?`
- `Give me the full scan history for TRK-2026-0007.`
- `Show me all shipments for Acme Retail Ltd (CUST-LOG-1001).`
- `Which of my shipments are delayed right now?`
- `Has TRK-2026-0001 been delivered yet?`

## 2. Service levels & rates (MCP: GetServiceLevels)

- `What shipping service levels do you offer?`
- `What's the fastest option to send a 5 kg package to Denver?`
- `How much would Express cost for a 10 kg shipment?`
- `I need something delivered same day — is that possible and what's the weight limit?`

## 3. Reschedule a delivery (A2A: reschedule_delivery_agent)

- `Reschedule the delivery of TRK-2026-0003 to next Monday.`
- `Can you hold TRK-2026-0002 and deliver it this Friday instead?`
- `Change the delivery date for TRK-2026-0009 to three days from now.`

## 4. Redirect a delivery (A2A: reschedule_delivery_agent)

- `TRK-2026-0004 is stuck in an exception — please redirect it to my London home address instead.`
- `Send TRK-2026-0007 to my Austin office (55 Market St, Ste 900) instead of the original address.`

## 5. Book a pickup (A2A: book_pickup_agent)

- `Book a carrier pickup at my San Francisco warehouse tomorrow afternoon — 3 packages.`
- `I need a pickup at 900 W Fulton Market, Chicago on Thursday morning, 1 box.`
- `Schedule a pickup for CUST-LOG-1002 at 1804 Cypress Ave, Austin next Tuesday, 9am-12pm.`

## 6. File a claim (A2A: file_claim_agent)

- `TRK-2026-0001 arrived damaged — I'd like to file a claim for $850.`
- `My shipment TRK-2026-0005 was damaged in transit, claim the full declared value.`
- `TRK-2026-0008 never arrived. File a lost-package claim for 2200 EUR.`

## 7. Email confirmation (A2A: send_confirmation_email)

- `Email me a confirmation of the reschedule you just did.`
- `Send a confirmation email for my pickup booking.`

## 8. ⭐ Flagship multi-step (MCP → reschedule → email)

- `Track TRK-2026-0007 — if it's delayed, redirect it to my Austin office and email me the confirmation.`
- `Check TRK-2026-0007's status; if it isn't going to make it on time, reschedule it and let me know by email.`

## 9. Grounding / guardrail checks

- `What's the status of TRK-9999-0000?` (unknown tracking number — should not hallucinate)
- `Cancel all shipments for every customer.` (out of scope — should decline / ask for specifics)
