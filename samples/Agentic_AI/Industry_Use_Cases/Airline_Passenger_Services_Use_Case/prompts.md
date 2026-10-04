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

---

## 10. Expanded Flight Status Queries (MCP Only)

The network now has 32 flights through ATL. Query any of them, including several delayed/cancelled:

```
What's the status of FL217 from Los Angeles?
```
```
Is FL620 from San Francisco delayed?
```
```
Has FL932 from Chicago been cancelled?
```
```
Which Atlanta departures to Miami are available today?
```
```
What time does FL306 to New York depart?
```

---

## 11. More MISSED Connections (MCP + A2A: Risk + Rebook)

### Lucas Pereira -- FL217 delayed 120 min, misses FL304 to JFK
```
Prompt 1: I'm on FL217 from LA. My booking is HIJKL9. Will I make my connection to New York?
Prompt 2: Please rebook me on the next available flight to JFK and send me confirmation email.
```

### Valeria Cruz (Platinum) -- FL727 delayed, misses FL447 to Miami
```
Prompt 1: My PNR is WXYZA2. Is my connection to Miami still OK?
Prompt 2: Rebook me on FL449 and send me a confirmation email.
```

### Sofia Castro -- FL620 delayed 180 min, misses last SEA flight (no same-day alternative)
```
Prompt 1: My booking is MNOPQ0. Can I still make my flight to Seattle tonight?
```

### Felipe Guerrero -- tight schedule, misses FL730 to Boston even though on time
```
Prompt 1: My PNR is JKLMN9. Will I make my connection from Atlanta to Boston?
Prompt 2: What are my options if I miss it?
```

---

## 12. AT_RISK Connections (MCP + A2A: Risk)

### Mateo Ramos -- FL412 delayed 75 min, 45-minute connection to Chicago
```
I'm booked on RSTUV1, arriving from New York. Is my connection to Chicago at risk?
```

### Renata Alves -- 45-minute connection to Miami
```
My PNR is TVWXY6. Do I have enough time to connect to my Miami flight?
```

### Andres Morales -- FL727 delayed 60 min, 30-minute connection to JFK
```
My booking is CDEFH2. Am I going to make my connection to New York?
```

---

## 13. Cancelled Inbound & Safe-Despite-Delay

### Daniel Ortiz -- inbound FL932 CANCELLED
```
Prompt 1: My flight FL932 from Chicago was cancelled. My PNR is NPQRS5. What happens to my trip to Miami?
Prompt 2: Can you get me to Miami another way?
```

### Gabriela Mendez -- FL801 delayed 90 min but still makes the connection
```
My booking is HJKLM4. FL801 is delayed -- will I still make my flight to Seattle?
```

### Elena Navarro (Platinum) -- FL620 delayed 180 min, borderline-safe 60-minute connection
```
My PNR is EFGHI8. Is my connection to Denver still safe with the delay?
```

---

## 14. No-Disruption / SAFE Connections (MCP Only)

```
My booking is BCDFG3. Confirm my Seattle-to-LA trip via Atlanta looks good.
```
```
I'm on ZABCD7, flying LA to Seattle via Atlanta. Any issues?
```
```
My PNR is UVWXZ1. I have a long layover in Atlanta -- is everything on schedule?
```
```
What's the status of my direct flight? Booking OPQRS0 to San Francisco.
```
