# Hospital Post-Discharge — Demo Prompts

Chat over `ws://localhost:8082/ws/chat`. Patients are identified by `patient_id` (e.g. P-2024-00123).
Reset with `reset_data.sql` between runs.

## 1. Discharge summary (MCP only)
```
Get the discharge summary for patient P-2024-00123.
```
```
What follow-up and medications does P-2024-00126 have?
```

## 2. Book a follow-up appointment (MCP + A2A: book_appointment)
```
Prompt 1: Show the discharge summary for P-2024-00123.
Prompt 2: Book the follow-up appointment (7 days out, Cardiology).
```

## 3. Pharmacy orders (MCP + A2A: create_pharmacy_order)
```
Prompt 1: What medications were prescribed at discharge for P-2024-00123?
Prompt 2: Create the pharmacy orders for all of them.
```

## 4. Bed turnover (A2A: request_bed_cleaning)
```
Patient has been discharged from BED-2A-002 in WARD-2A — please initiate bed cleaning.
```

## 5. Full discharge workflow (all agents)
```
Complete the full discharge for P-2024-00123: book the follow-up appointment, create all
medication orders, initiate bed cleaning for BED-4A-010 in WARD-4A, and send a confirmation email
with the details.
```

## 6. Edge cases (skips that don't apply)
```
Run the discharge process for P-2024-00125.   # no follow-up required (General) — should skip the appointment
```
```
Process discharge for P-2024-00121.           # no follow-up, no medications — bed turnover only
```

## 7. Lookups
```
What's the status of bed BED-3B-003 in WARD-3B?
```
```
Show the pharmacy orders for P-2024-00127.
```
```
List the follow-up appointments for P-2024-00124.
```

## 8. Out of scope (agent should decline)
```
What medication should I prescribe for chest pain?
How much is the bill for P-2024-00123?
This is an emergency — send an ambulance.
```
