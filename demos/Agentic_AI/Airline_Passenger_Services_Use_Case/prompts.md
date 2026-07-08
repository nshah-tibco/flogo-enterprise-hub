# Airline Passenger Services -- Demo Prompts

## 1. Flight Status (MCP Only)

```
What's the status of flight FL801?
```
```
Can you check if FL445 is on time?
```
```
Is flight FL510 from Seattle delayed?
```
```
What gate is FL302 departing from?
```

---

## 2. Booking Lookup (MCP Only)

```
Can you look up booking ABCDE1?
```
```
What are the flight segments for PNR PQRST4?
```
```
I need to check my booking. My confirmation code is FGHIJ2.
```

---

## 3. Passenger & Loyalty Info (MCP Only)

```
What is the loyalty tier for passenger PAX-2026-00101?
```
```
How many miles does Carlos Martinez have?
```
```
Can you look up the frequent flyer status for booking KLMNO3?
```

---

## 4. Connection Risk Assessment (MCP + A2A)

### Carlos Martinez -- MISSED Connection (FL801 delayed 90 min)
```
Hi, I'm on flight FL801 from Denver. What's the status?
```
```
Oh no, I have a connection. My booking is ABCDE1. Will I make it?
```

### Maria Fernandez -- AT_RISK Connection (FL510 delayed 45 min)
```
What's happening with flight FL510 from Seattle?
```
```
My PNR is PQRST4. Am I going to make my connection to Chicago?
```

### Diego Torres -- AT_RISK Connection (FL801 delayed, connecting FL302)
```
I'm booked on FL801. My PNR is GHIJK7. Is my connection to JFK at risk?
```

---

## 5. Full Rebooking Workflow (MCP + A2A: Risk + Rebook)

### Carlos: FL445 -> FL447
```
Prompt 1: Hi, I'm on flight FL801 from Denver. What's the status?
Prompt 2: My booking is ABCDE1. Will I make my connection to Miami?
Prompt 3: Yes, please rebook me on FL447.
```

### Maria: FL612 -> (alternative if available)
```
Prompt 1: What's the status of FL510?
Prompt 2: My PNR is PQRST4. Check if my connection to Chicago is at risk.
Prompt 3: Please rebook me if there's an alternative.
```

---

## 6. Full Workflow with Email (All Agents)

```
Prompt 1: Hi, I'm on flight FL801 from Denver. What's the status?
Prompt 2: My booking is ABCDE1. Will I make my connection to Miami?
Prompt 3: Yes, please rebook me on FL447 and send confirmation email.
Prompt 4: Can you send me a confirmation email?
```

---

## 7. No Disruption Scenarios

### Roberto Gonzalez -- Direct Flight, On Time
```
What's the status of FL445?
My booking is KLMNO3. Can you confirm everything looks good?
```

### Ana Silva -- Connecting, Both On Time
```
Can you check my booking FGHIJ2? I'm flying Los Angeles to New York via Atlanta.
```

### Jorge Lopez -- Connecting, Both On Time
```
I'm booked on UVWXY5. Will I make my connection from Boston to Miami?
```

---

## 8. Edge Cases & Out of Scope

### Invalid PNR
```
Can you look up booking ZZZZZ9?
```

### Out of Scope Requests
```
Can you upgrade me to business class?
Where is my luggage?
I want a refund for my delayed flight.
Can you book me a hotel?
```

---

## 9. Multi-Turn Conversation

```
Turn 1: What flights are delayed today?
Turn 2: Tell me more about FL801. How long is the delay?
Turn 3: I'm Carlos Martinez, booking ABCDE1. What does this mean for my connection?
Turn 4: What are my alternatives to get to Miami?
Turn 5: Rebook me on FL447, seat 5A please.
Turn 6: Send me a confirmation email.
```
