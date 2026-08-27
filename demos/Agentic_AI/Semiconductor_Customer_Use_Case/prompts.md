# Demo prompts — Semiconductor Customer & Order Assistant

Connect a WebSocket client to `ws://<host>:8088/semiconductor` and paste these.
Grouped by scenario. All prices are **USD**. Flagship customer:
**Aurora Automotive Systems** (`CUST-10001`).
Run `reset_data.sql` between runs to clear agent-written rows.

> The assistant identifies you by your account id (`CUST-100xx`). Lead with it, or
> give it when asked — you never need to know internal order-line / case ids.

---

## 1. Who am I — account profile (MCP: GetCustomerProfile)

- `Hi, I'm CUST-10001. Can you pull up my account?`
- `What tier and region is account CUST-10004 on?`
- `What's the contact email on file for CUST-10005?`

## 2. Part specs & qualification (MCP: GetProductDetails)

- `Tell me about part TMN4010Q — specs, package and qualification.`
- `Is ESD1CANQ automotive qualified? Which AEC standard?`
- `Which parts in your catalog are AEC-Q101 qualified?`
- `Is 74LVC1G08 RoHS compliant, and what package does it come in?`
- `Give me the datasheet link for GAN65R060.`

## 3. Stock & lead time (MCP: CheckStockAndLeadTime)

- `How many TMN4010Q do you have in stock and where?`
- `What's the lead time on PMN8033YS?`
- `Do you have GAN65R060 available in Europe? When does it restock?`
- `I need 100,000 74LVC1G08 — can you cover that from stock?`

## 4. Pricing & volume breaks (MCP: GetPricing)

- `What's the unit price for TMN4010Q at 5,000 pieces?`
- `Show me the full price break table for GAN65R060.`
- `What would 100k SBD3020EP cost per unit?`
- `At what quantity does 74LVC1G08 drop below 2 cents?`

## 5. Orders & line detail (MCP: GetOrders / GetOrderLines)

- `What's the status of my orders? I'm CUST-10001.`
- `What's on order SO-2026-0002 and when is it promised?`
- `Has SO-2026-0003 shipped yet?`
- `Show me the requested dates for every line on SO-2026-0004.`

## 6. Lifecycle / EOL / PCN (MCP: GetLifecycleNotices)

- `Is SBD2010A still active or is it going end-of-life?`
- `When is the last-time-buy date for SBD2010A, and what replaces it?`
- `Are there any change notices (PCNs) on PMN8033YS?`
- `Which of my catalog parts are NRND or EOL?`

## 7. Cross-references / alternates (MCP: GetCrossReferences)

- `Is there a drop-in replacement for the EOL part SBD2010A?`
- `Do you have a second source for TMN4010Q?`
- `What's a pin-compatible alternative to 74LVC1G08?`
- `SBD3020EP is tight on stock — is there a higher-rated upgrade?`

## 8. Place an order (A2A: place_order_agent)

- `Place an order for 5,000 TMN4010Q against PO AUR-PO-90001. I'm CUST-10001.`
- `I'm CUST-10002 — order 25,000 TMN4010Q, needed in 3 weeks.`
- `Buy 2,500 GAN65R060 for CUST-10004, requested date next month.`

## 9. Expedite an existing order line (A2A: expedite_order_agent)

- `Please pull in the requested date on the PMN8033YS line of SO-2026-0002 to next week.`
- `Expedite the 74LVC1G08 line on SO-2026-0004 — I need it 5 days sooner.`

## 10. Open an RMA / quality case (A2A: open_rma_agent)

- `I'm CUST-10001. The SBD3020EP on SO-2026-0002 came in with solderability issues — open an RMA for 500 pieces.`
- `File a quality case for CUST-10004: 40 GAN65R060 from SO-2026-0003 showing gate-drive failures.`
- `Open an RMA for a parametric failure on 200 TMN4010Q, order SO-2026-0001.`

## 11. Request free samples (A2A: request_sample_agent)

- `Can I get 25 samples of ESD1CANQ for a design-in eval? I'm CUST-10005, ship to Boston.`
- `Send me 10 GAN65R060 samples for a 650V bench test — CUST-10004.`
- `Request 50 samples of TMN2508 for CUST-10002.`

## 12. Subscribe to stock / PCN alerts (A2A: subscribe_alert_agent)

- `Subscribe me to stock alerts for GAN65R060. I'm CUST-10004.`
- `Notify me of any change notices on PMN8033YS — CUST-10001.`
- `Sign me up for PCN alerts on SBD2010A since it's going EOL. Account CUST-10001.`

## 13. Email a confirmation (A2A: send_confirmation_email)

- `Email me a confirmation of that order.`
- `Send a confirmation email for the RMA you just opened.`

## 14. ⭐ Flagship multi-step (MCP → A2A → email)

- `I'm CUST-10001. Check whether SBD2010A is end-of-life — if it is, subscribe me to PCN alerts for it and email me the confirmation.`
- `Order 5,000 TMN4010Q at the right price break for CUST-10001 against PO AUR-PO-90007, then email me a confirmation.`
- `40 GAN65R060 from SO-2026-0003 failed in the field — open an RMA for CUST-10004 and email me the case number.`

## 15. Grounding / guardrail checks (should NOT hallucinate or overreach)

- `What's the price of part XYZ-99999?` (not in catalog — should say it can't find it)
- `Can you recommend a thermal-via layout for my PCB using TMN4010Q?` (design advice — out of scope)
- `Match a competitor's price on GAN65R060.` (price-matching — out of scope)
- `Change my account to Direct-Gold and raise my credit limit.` (account/credit change — out of scope)
- `What new parts are on your 2027 roadmap?` (unreleased roadmap — out of scope)
