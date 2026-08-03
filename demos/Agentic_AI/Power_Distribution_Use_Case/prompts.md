# Electric Power Distribution — Demo Prompts

A residential electric power distribution utility self-service assistant. Residents are identified by
their **account number** (`ACCT-XXXXXXXX`), the **phone on file** (`+1-XXX-555-01XX`), or their
**service address**. The agent looks up the account, then uses it for every other tool. Currency is
**USD** (Taxes & Regulatory Fees ~7%).

Copy-paste any block into the chat client connected to `ws://localhost:9680/grid`.

---

## 1. Account & Profile Lookup (MCP Only)

```
Show me my account details. My account number is ACCT-50010001.
```
```
Look up my account. My phone number is +1-214-555-0178.
```
```
Am I on a smart meter or an analog meter? Account ACCT-50010006.
```

---

## 2. Bill Explanation & Line Items (MCP Only)

### Laura Bennett — summer AC spike (valid high bill)
```
Why is my electric bill so high this month? My account is ACCT-50010001.
```

### Tom Alvarez — Time-of-Use, heavy on-peak (highest bill)
```
Can you break down my June bill? Account ACCT-50010005.
```

### Priya Nair — solar net-metering credit
```
I have solar panels — how is my bill calculated? Account ACCT-50010003.
```

### Diane Foster — medical baseline credit
```
What is the medical baseline credit on my bill? Account ACCT-50010004.
```

### Grace Kim — estimated read (analog meter)
```
My bill says "estimated" — what does that mean? Account ACCT-50010006.
```

### Nathan Cole — budget billing
```
Explain the budget billing adjustment on my invoice. Account ACCT-50010013.
```

---

## 3. Energy Usage (MCP Only)

```
How much electricity did I use last month? Account ACCT-50010001.
```
```
Is my usage higher than last year? Account ACCT-50010001.
```

### Marcus Reed — EV owner, overnight charging
```
How much of my usage is overnight off-peak? Account ACCT-50010002.
```

---

## 4. Payment History (MCP Only)

```
Show me my recent payments. Account ACCT-50010001.
```
```
When did I last pay my bill? Account ACCT-50010005.
```

### Henry Wu — recent payment cleared a past-due balance
```
Did my last payment go through? Account ACCT-50010007.
```

---

## 5. Rate Plans (MCP Only)

```
What rate plan am I on? Account ACCT-50010001.
```
```
I have an electric vehicle — is there a better rate plan for me? Account ACCT-50010001.
```
```
Tell me about the solar net-metering plan.
```

---

## 6. Outages — Check Your Area (MCP Only: GetOutages)

### Storm outage in progress (Oakdale / Prairie View, zip 75004)
```
Is there a power outage in my area? Account ACCT-50010004.
```
```
Are there any outages near zip code 75004?
```

### Planned outage (Oakdale / Elm Hollow, zip 75010)
```
Why is my power scheduled to go out? Account ACCT-50010010.
```

### Equipment outage under investigation (Highland / Copperfield, zip 75017)
```
My power just went out — is it a known outage? Account ACCT-50010017.
```

---

## 7. Outage Ticket Status (MCP Only: GetOutageTickets)

### Ethan Mills — pre-seeded ticket OTKT-2026-0001 (CREW_DISPATCHED, CREW-07)
```
What's the status of my outage report? Account ACCT-50010015.
```
```
Has a crew been sent to my house yet? Account ACCT-50010015.
```

---

## 8. Report a New Outage (MCP + A2A: outage_dispatch_agent → report_outage)

### Laura Bennett — no active area outage, reports a fresh loss of power
```
Prompt 1: My power is completely out at my house and I don't see an outage listed. My account is ACCT-50010001.
Prompt 2: Yes, please report the outage and dispatch a crew.
```
The agent checks current area outages (none for zip 75001), then files a new ticket via
`report_outage` and returns a ticket ID with a crew ETA.

### Report an outage and request an email confirmation
```
Prompt 1: The whole street is dark and my lights are off. Account ACCT-50010008.
Prompt 2: Please log the outage and email me the confirmation.
```

---

## 9. Service Appointment Status (MCP Only: GetServiceAppointments)

### Sophia Turner — pre-seeded appointment APPT-2026-0001 (METER_INSPECTION, SCHEDULED)
```
When is my meter inspection scheduled? Account ACCT-50010014.
```
```
Do I have any service appointments coming up? Account ACCT-50010014.
```

---

## 10. Schedule a New Appointment (MCP + A2A: service_appointment_agent → schedule_appointment)

### Grace Kim — analog meter, wants a smart-meter upgrade
```
Prompt 1: I'd like to upgrade my analog meter to a smart meter. Account ACCT-50010006.
Prompt 2: Yes, book me the earliest morning slot.
```

### Laura Bennett — request a meter inspection
```
Prompt 1: My lights keep flickering — can someone come inspect my meter? Account ACCT-50010001.
Prompt 2: Schedule it, please.
```

---

## 11. Service Request Status (MCP Only: GetServiceRequests)

### Maria Gonzalez — pre-seeded reconnect SRV-2026-0001 (IN_PROGRESS)
```
What's the status of my reconnection request? Account ACCT-50010016.
```
```
Is my power going to be turned back on soon? Account ACCT-50010016.
```

---

## 12. Submit a Reconnect (MCP + A2A: service_change_agent → submit_service_request)

### Henry Wu — disconnected, balance now cleared by recent payment
```
Prompt 1: My service is disconnected and I just paid what I owed. Can you turn my power back on? Account ACCT-50010007.
Prompt 2: Yes, please submit the reconnect request.
```
The agent verifies the account (connection is DISCONNECTED) and checks payment history — Henry's
recent **$142.50** payment cleared the past-due balance — so it submits a RECONNECT via
`submit_service_request` and returns a request ID with an effective date.

---

## 13. Guardrail — Reconnect Refused While Past Due

The `service_change_agent` will only submit a reconnect once the outstanding balance is cleared.
If an account is still past due, it declines and asks the resident to pay first.

```
Prompt 1: Turn my power back on right now. Account ACCT-50010007.
Prompt 2: I haven't paid the past-due balance yet, just do it anyway.
```
Expected behavior: the agent confirms the balance status from payment history. If the past-due
balance were still outstanding it refuses the reconnect and explains that payment must clear first;
because Henry's balance is now cleared, it proceeds only once the resident confirms.

---

## 14. Email Confirmation (A2A: send_confirmation_email)

Invoked once, after an action, when the resident asks for it.

```
Please email me a confirmation of that.
```
```
Send the outage ticket details to my email on file.
```

---

## 15. Full End-to-End Flow (read → write → email)

### Report an outage, dispatch a crew, and confirm by email
```
Prompt 1: My power is out and there's no outage showing for my area. Account ACCT-50010001.
Prompt 2: Report it and send a crew.
Prompt 3: Great — please email me the ticket confirmation.
```

### Schedule a meter upgrade and confirm by email
```
Prompt 1: I want to swap my old analog meter for a smart meter. Account ACCT-50010006.
Prompt 2: Book the first available morning slot.
Prompt 3: Email me the appointment details.
```

### Reconnect after payment and confirm by email
```
Prompt 1: I paid my balance — please reconnect my service. Account ACCT-50010007.
Prompt 2: Yes, submit the reconnect.
Prompt 3: Send me an email confirmation.
```

---

## 16. Multi-Turn Conversation

```
Turn 1: Hi, my account is ACCT-50010001. Why is my bill higher than usual this month?
Turn 2: Was my usage really that much higher than last year?
Turn 3: What rate plan am I on?
Turn 4: My lights keep flickering — can you schedule a meter inspection?
Turn 5: Please email me the appointment confirmation.
```

---

## 17. Edge Cases & Out of Scope

### Unknown account
```
Why is my bill so high? My account is ACCT-99999999.
```

### Out of scope (agent should politely decline)
```
Can you lower my electricity rate as a discount?
I want to switch to a different electricity retailer.
Can you tell me my neighbor's account balance?
Will you refund my whole bill?
Can you fix the wiring inside my house?
```
