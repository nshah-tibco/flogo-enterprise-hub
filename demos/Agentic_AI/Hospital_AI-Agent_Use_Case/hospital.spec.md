# Specification: Hospital Post-Discharge Coordination Assistant

> Worked example of the [agentic-ai-use-case spec template](../../../skills-library/.claude/skills/agentic-ai-use-case/references/use-case-spec-template.md),
> reverse-engineered from this use case. This is the **spec** (WHAT/WHY) you would hand to the
> `agentic-ai-use-case` skill to regenerate a Hospital use case as the standard 3-app pattern
> (MCP read tools + A2A write agents + WebSocket orchestrator). Technology choices (Flogo, MCP, A2A,
> ports, SQL) are intentionally **not** specified here — the skill owns those.

## 1. Intent (WHY)
A hospital discharge coordinator chats in natural language to run a patient's **post-discharge
workflow** end to end: retrieve the discharge summary, book a follow-up appointment, create pharmacy
orders for prescribed medications, initiate bed turnover/cleaning, and send the patient a confirmation
— replacing manual coordination across EMR, pharmacy, housekeeping, and scheduling systems.

## 2. Actors & identification
- **Primary actor:** hospital discharge coordinator / ward staff.
- **Identifier:** `patient_id` — format `P-YYYY-NNNNN` (e.g. `P-2024-00123`).
- **Locale:** en-SG; no currency (clinical workflow, not billing).

## 3. User scenarios (Given/When/Then)
- **S1 (read):** Given patient `P-2024-00123` (Cardiology, 3 meds, follow-up required), When staff asks *"Get the discharge summary for P-2024-00123"*, Then the assistant returns follow-up requirement, specialty, discharge date, ward/bed, and the medication list.
- **S2 (action + confirm):** Given a discharged patient requiring follow-up, When staff asks to book the follow-up, Then the assistant books an appointment for the discharge specialty **7 days after** discharge and confirms date/time.
- **S3 (per-item action):** Given a discharge with prescribed medications, When staff requests medication fulfillment, Then the assistant creates **one pharmacy order per medication** with pickup location and estimated ready time.
- **S4 (bed turnover):** Given a vacated bed, When staff says *"initiate bed cleaning for BED-2A-002 in WARD-2A"*, Then the assistant requests cleaning, sets the bed to CLEANING_REQUESTED, and returns the estimated-ready time.
- **S5 (end-to-end):** When staff asks to *"complete the full discharge process for P-2024-00123 including follow-up appointment, all medication orders, bed cleanup, and send a confirmation email"*, Then the assistant performs S2+S3+S4 and sends one confirmation email summarizing all of it.
- **S6 (edge):** Given `P-2024-00125` (no follow-up, 1 med) or `P-2024-00121` (no follow-up, no meds), Then the assistant skips the steps that don't apply and says so.

## 4. Functional requirements

### 4a. Information lookups (read-only) → MCP tools
| Lookup | Input | Returns | Source entity |
|---|---|---|---|
| Get discharge summary | patient_id | follow_up_required, specialty, discharge_date, ward_id, bed_id, medications[] | patient_discharges (+ discharge_medications) |
| Get patient profile | patient_id | name, phone, email | patients |
| Get bed status | ward_id / bed_id | status, patient_id, updated_at, estimated_ready | beds |
| Get appointments | patient_id | specialty, scheduled_date/time, status | appointments |
| Get medication catalog | medication_code | medication_name, ready_hours | medication_catalog |
| Get pharmacy orders | patient_id | medication, days_supply, pickup_location, ready_by, status | pharmacy_orders |
| Get specialties | — | specialty_code, specialty_name | specialties |

### 4b. Actions / workflows (state-changing) → A2A agents
| Action | Inputs | Validation / steps | Result | Guardrails |
|---|---|---|---|---|
| Book follow-up appointment | patient_id, specialty, date, time | only if follow_up_required; date = discharge_date + 7d | new appointment (CONFIRMED) | confirm; skip if not required |
| Create pharmacy orders | patient_id, medications[] (code, days_supply) | look up medication_name/ready time; one order per med; default pickup PHARMACY_A | pharmacy_orders rows with ready_by/status | one per medication; skip if none |
| Initiate bed turnover | bed_id, ward_id | set CLEANING_REQUESTED, clear patient, set estimated_ready | updated bed row | — |
| Send confirmation email | patient_id, subject, body | compose summary of appointment + meds | email dispatched | invoke once, last, only if requested |

## 5. Domain entities & data → PostgreSQL tables
| Entity | Key fields | Relationships | Read/written by |
|---|---|---|---|
| patients | patient_id (PK), name, phone, email | — | profile lookup; email |
| patient_discharges | discharge_id (PK), patient_id, discharge_date, ward_id, bed_id, follow_up_required, specialty_code | → patients, specialties, beds | discharge summary |
| discharge_medications | discharge_id, medication_code, days_supply | → patient_discharges, medication_catalog | discharge summary; pharmacy |
| appointments | appointment_id (PK), patient_id, specialty, scheduled_date/time, status | → patients | book appointment (write) |
| medication_catalog | medication_code (PK), medication_name, ready_hours | — | pharmacy |
| pharmacy_orders | order_id (PK), patient_id, medication_code/name, days_supply, pickup_location, ready_by, status | → patients | create orders (write) |
| beds | bed_id, ward_id, patient_id, status, updated_at, estimated_ready | → patients | bed status; turnover (write) |
| specialties | specialty_code (PK), specialty_name | — | reference |

## 6. Seed-data scenarios
- `P-2024-00123` John Tan — Cardiology, follow-up **required**, **3** meds (Aspirin, Metoprolol, Atorvastatin), BED-4A-010 → full workflow (S1/S5).
- `P-2024-00124` Mary Lim — Orthopedics, follow-up required, 2 meds → appointment + pharmacy.
- `P-2024-00125` David Wong — General, **no** follow-up, 1 med → skip appointment (S6).
- `P-2024-00126` Sarah Chen — Neurology, follow-up required, 2 meds.
- `P-2024-00121` Alice Ng — no follow-up, no meds → bed-only / minimal (S6).
- Target: ~10 patients with varied follow-up/medication/bed configurations; medication catalog of ~10 drugs; beds across several wards with mixed statuses (OCCUPIED / AVAILABLE / CLEANING).

## 7. Acceptance criteria
- [ ] Discharge summary for `P-2024-00123` returns follow_up_required=true, CARDIOLOGY, and 3 medications.
- [ ] Booking for a follow-up patient inserts an appointment dated discharge_date + 7 days with the discharge specialty.
- [ ] Full workflow for `P-2024-00123` creates **3** pharmacy orders, one appointment, one bed cleaning request, and sends one email.
- [ ] `P-2024-00125` (no follow-up) does **not** create an appointment and the assistant says why.
- [ ] Bed turnover sets the target bed to CLEANING_REQUESTED with an estimated-ready time.
- [ ] Actions confirm before writing; no action is invoked more than 3 times.

## 8. Out of scope
Diagnosis or treatment advice; billing/insurance inquiries; emergency services; anything beyond
post-discharge coordination — politely declined.

## 9. Non-functional & constraints
- Real-time streaming chat; multi-turn session memory.
- **PHI privacy:** redact patient identifiers in responses (e.g. `P-2024-XXXXX`); no PHI in logs; partially mask medication names if needed.
- **Tone:** professional, empathetic, healthcare-appropriate; no jargon/slang.
- **Termination:** max 3 attempts per action; on failure, report what completed and what failed.
- **Security (target):** TLS, bearer-token auth, rate limiting, on-prem/data-residency LLM.
- Reuse existing OpenAI / PostgreSQL / SMTP connection settings; database name `hospital`.

## 10. Assumptions & open questions
- Default appointment time 10:30 and pickup location PHARMACY_A unless specified — confirm.
- Confirm whether bed "mark available" (post-clean) is in scope as a second bed action or external.
- Confirm email recipient source (patient record vs preconfigured service mailbox).

---
**Handoff:** *"Build the Hospital Post-Discharge use case from `demos/Agentic_AI/Hospital_AI-Agent_Use_Case/hospital.spec.md`."*
The skill frames it back, clarifies §10, plans the 3 apps, then generates the MCP server (7 lookups),
A2A agents (book appointment, pharmacy orders, bed turnover, send email), `database.sql`,
`reset_data.sql`, `prompts.md`, and `README`, and verifies them.
