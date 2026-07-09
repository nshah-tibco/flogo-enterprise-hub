# Telecom Invoice Chatbot -- Demo Prompts

Indonesian telecom provider. Subscribers are identified by their `+62` mobile number; the agent looks up the customer ID from the number, then uses it for all other tools. Currency is **IDR** (VAT/PPN 11%).

## 1. Bill Explanation (MCP Only)

```
Why is my bill so high this month? My number is +62-812-3456-7890.
```
```
Can you break down my June invoice? My mobile is +62-813-5678-9013.
```
```
What am I being charged for? +62-878-8901-2345
```

---

## 2. Usage (MCP Only)

```
How much data have I used this month? My number is +62-852-3456-7891.
```
```
Am I close to my data limit? +62-817-1234-5678
```

---

## 3. Plans (MCP Only)

```
What plan am I on? My number is +62-857-4567-8901.
```
```
What add-ons do I have? +62-812-3456-7890
```

---

## 4. Payment History (MCP Only)

```
Show me my last 3 payments. My number is +62-811-5678-9012.
```
```
When did I last pay my bill? +62-812-6789-0123
```

---

## 5. Billing Dispute (MCP + A2A: billing_dispute_agent)

### Siti Nurhaliza -- Roaming charged but never travelled (0 roaming days)
```
Prompt 1: I was charged for roaming in Thailand but I never left Indonesia. My number is +62-813-2345-6789.
Prompt 2: Yes, please file a dispute.
```

### Joko Susilo -- International calls charged but no intl minutes used
```
Prompt 1: There's an international calls charge to China on my bill but I never called overseas. My number is +62-856-9012-3456.
Prompt 2: Please dispute it.
```

---

## 6. Recharge (MCP + A2A: recharge_agent)

### Ahmad Wijaya -- near data limit (19.6 / 20 GB)
```
Prompt 1: I'm almost out of data. My number is +62-852-3456-7891.
Prompt 2: What recharge packs do you have?
Prompt 3: Get me the Data Booster 10GB pack.
```

### Bambang Kusuma -- business, near 100 GB
```
Prompt 1: I need more data on +62-817-1234-5678.
Prompt 2: Add the Data Max 25GB pack please.
```

---

## 7. Dispute Status (MCP Only: GetDisputes)

### Maya Sari -- pre-seeded dispute DSP-2026-0001 (UNDER_REVIEW)
```
What's the status of my dispute? My number is +62-812-6789-0123.
```

### Agus Salim -- resolved dispute DSP-2026-0002
```
Did my dispute get resolved? +62-822-3456-7801
```

### Ahmad Wijaya -- open dispute DSP-2026-0003 (data add-on charged twice)
```
Is there any update on my billing dispute? +62-852-3456-7891
```

---

## 8. Full Workflow with Email (All Agents)

```
Prompt 1: I was charged IDR 220,000 for roaming in Thailand but I didn't travel. My number is +62-813-2345-6789.
Prompt 2: Yes, file the dispute and send me an email confirmation.
```

```
Prompt 1: I need more data. My number is +62-852-3456-7891.
Prompt 2: Apply the Data Booster 10GB.
Prompt 3: Please send me a confirmation email.
```

---

## 9. Roaming Bill Explanations (MCP Only)

### Hendra Gunawan (VIP) -- Umrah roaming to Saudi Arabia (valid, highest bill)
```
Why is my bill so high? My number is +62-813-5678-9013.
```

### Putri Anggraini -- roaming Australia (valid)
```
Can you explain the roaming charge on my bill? +62-838-0123-4567
```

### Fitri Handayani -- roaming Malaysia (valid)
```
I see a roaming charge for Malaysia -- is that correct? My number is +62-812-4567-8902.
```

---

## 10. Multi-Turn Conversation

```
Turn 1: Hi, my number is +62-812-3456-7890. Why is my bill higher than usual?
Turn 2: Is the roaming charge correct?
Turn 3: What plan am I on again?
Turn 4: Show me my last 3 payments.
```

---

## 11. Edge Cases & Out of Scope

### Unknown subscriber
```
Why is my bill high? My number is +62-800-0000-0000.
```

### Out of scope (agent should politely decline)
```
I want to swap my SIM card.
Can you port my number to another operator?
Is there a network outage in Jakarta?
I want to buy a new phone.
My home internet is down, can you fix it?
```
