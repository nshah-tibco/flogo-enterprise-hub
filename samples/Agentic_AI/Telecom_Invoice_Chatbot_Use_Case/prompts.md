# Telecom Invoice Chatbot -- Demo Prompts

US telecom provider. Subscribers are identified by their `+1` mobile number; the agent looks up the customer ID from the number, then uses it for all other tools. Currency is **USD** (Taxes & Regulatory Fees ~10%).

## 1. Bill Explanation (MCP Only)

```
Why is my bill so high this month? My number is +1-415-555-0142.
```
```
Can you break down my June invoice? My mobile is +1-725-555-0193.
```
```
What am I being charged for? +1-512-555-0198
```

---

## 2. Usage (MCP Only)

```
How much data have I used this month? My number is +1-312-555-0163.
```
```
Am I close to my data limit? +1-773-555-0145
```

---

## 3. Plans (MCP Only)

```
What plan am I on? My number is +1-206-555-0119.
```
```
What add-ons do I have? +1-415-555-0142
```

---

## 4. Payment History (MCP Only)

```
Show me my last 3 payments. My number is +1-617-555-0187.
```
```
When did I last pay my bill? +1-305-555-0134
```

---

## 5. Billing Dispute (MCP + A2A: billing_dispute_agent)

### Emily Carter -- Roaming charged but never travelled (0 roaming days)
```
Prompt 1: I was charged for roaming in Mexico but I never left the country. My number is +1-212-555-0178.
Prompt 2: Yes, please file a dispute.
```

### Robert Johnson -- International calls charged but no intl minutes used
```
Prompt 1: There's an international calls charge to China on my bill but I never called overseas. My number is +1-404-555-0172.
Prompt 2: Please dispute it.
```

---

## 6. Recharge (MCP + A2A: recharge_agent)

### Michael Rodriguez -- near data limit (19.6 / 20 GB)
```
Prompt 1: I'm almost out of data. My number is +1-312-555-0163.
Prompt 2: What recharge packs do you have?
Prompt 3: Get me the Data Booster 10GB pack.
```

### Daniel Wilson -- business, near 100 GB
```
Prompt 1: I need more data on +1-773-555-0145.
Prompt 2: Add the Data Max 25GB pack please.
```

---

## 7. Dispute Status (MCP Only: GetDisputes)

### Jessica Williams -- pre-seeded dispute DSP-2026-0001 (UNDER_REVIEW)
```
What's the status of my dispute? My number is +1-305-555-0134.
```

### Matthew Miller -- resolved dispute DSP-2026-0002
```
Did my dispute get resolved? +1-215-555-0129
```

### Michael Rodriguez -- open dispute DSP-2026-0003 (data add-on charged twice)
```
Is there any update on my billing dispute? +1-312-555-0163
```

---

## 8. Full Workflow with Email (All Agents)

```
Prompt 1: I was charged USD 45.00 for roaming in Mexico but I didn't travel. My number is +1-212-555-0178.
Prompt 2: Yes, file the dispute and send me an email confirmation.
```

```
Prompt 1: I need more data. My number is +1-312-555-0163.
Prompt 2: Apply the Data Booster 10GB.
Prompt 3: Please send me a confirmation email.
```

---

## 9. Roaming Bill Explanations (MCP Only)

### Kevin Taylor (VIP) -- roaming to Japan (valid, highest bill)
```
Why is my bill so high? My number is +1-725-555-0193.
```

### Ashley Brown -- roaming Canada (valid)
```
Can you explain the roaming charge on my bill? +1-646-555-0110
```

### Stephanie Moore -- roaming Mexico (valid)
```
I see a roaming charge for Mexico -- is that correct? My number is +1-503-555-0181.
```

---

## 10. More Billing Disputes -- Wrong Charges (MCP + A2A: billing_dispute_agent)

These accounts carry an intentionally incorrect charge on their June invoice. Each is contradicted by the usage record, so the agent can confirm the discrepancy and file a dispute.

### Brian Hall -- Roaming Mexico charged, never traveled (0 roaming days)
```
Prompt 1: My bill has a roaming charge for Mexico but I never left the US. My number is +1-408-555-0102.
Prompt 2: Yes, please file a dispute.
```

### Laura Adams -- International calls to India charged, never called (0 intl minutes)
```
Prompt 1: I'm being charged for international calls to India but I never made any. My number is +1-619-555-0113.
Prompt 2: Please dispute this charge.
```

### Kevin Nguyen -- Monthly plan fee billed twice (duplicate charge)
```
Prompt 1: My monthly plan charge appears twice on this invoice. My number is +1-716-555-0124.
Prompt 2: Yes, file a dispute for the duplicate charge.
```

### Rachel Scott -- Premium content subscription never authorized
```
Prompt 1: There's a "Premium Content Subscription" charge on my bill that I never signed up for. My number is +1-813-555-0135.
Prompt 2: Please dispute it and remove the charge.
```

### Justin King -- Data overage charge but usage was under the limit
```
Prompt 1: I was charged a data overage fee but I never went over my data limit. My number is +1-901-555-0146.
Prompt 2: Yes, please file a dispute.
```

### Megan Wright -- Late payment fee applied though paid on time
```
Prompt 1: There's a late payment fee on my bill, but I paid last month's bill on time. My number is +1-303-555-0157.
Prompt 2: Please dispute the late fee.
```

---

## 11. Multi-Turn Conversation

```
Turn 1: Hi, my number is +1-415-555-0142. Why is my bill higher than usual?
Turn 2: Is the roaming charge correct?
Turn 3: What plan am I on again?
Turn 4: Show me my last 3 payments.
```

---

## 12. Edge Cases & Out of Scope

### Unknown subscriber
```
Why is my bill high? My number is +1-000-555-0000.
```

### Out of scope (agent should politely decline)
```
I want to swap my SIM card.
Can you port my number to another carrier?
Is there a network outage in my area?
I want to buy a new phone.
My home internet is down, can you fix it?
```
