# Hospital Post-Discharge Coordination — Agentic AI Use Case

A spec-driven Hospital post-discharge assistant, generated **from
[`hospital.spec.md`](../../demos/Agentic_AI/Hospital_AI-Agent_Use_Case/hospital.spec.md)** using the
`agentic-ai-use-case` skill, and **built entirely with the `fda` (Flogo Design Assistant) CLI** — no
hand-edited `.flogo` JSON. A discharge coordinator chats in natural language; the orchestrator reads
patient data via MCP tools and performs write actions (appointment, pharmacy orders, bed turnover,
email) via A2A agents.

> Build method, `fda` command patterns, and a full gap analysis vs the hand-authored reference are in
> [`FDA_BUILD_NOTES.md`](FDA_BUILD_NOTES.md).

## Architecture (3 apps)

```
        Chatbot UI ──WebSocket ws://localhost:8082/ws/chat──► HospitalAIOrchestrator (agentactivity)
                                                                     │            │
                                              MCP (HTTP) ────────────┘            └──── A2A ────────┐
                                                     ▼                                              ▼
                                       HospitalMCPServer (7 read tools)          HospitalA2AServers (4 write agents)
                                                     │                                              │
                                                     └──────────────► PostgreSQL (hospital) ◄───────┘
                                                                              (+ Gmail SMTP for email)
```

## Apps

### `HospitalMCPServer.flogo` — MCP Server (port 9092, `/hospital-bss`)
Seven read-only tools, each `StartActivity → postgresql_query → actreturn`:

| Tool | Returns |
|------|---------|
| GetDischargeSummary | discharge (follow_up_required, specialty, date, ward/bed) joined with medications |
| GetPatientProfile | patient name, phone, email |
| GetBedStatus | bed_id, ward_id, patient_id, status, updated_at, estimated_ready |
| GetAppointments | patient_id, specialty, scheduled_date/time, status |
| GetMedicationCatalog | medication_code, medication_name, ready_hours |
| GetPharmacyOrders | patient_id, medication, days_supply, pickup, ready_by, status |
| GetSpecialties | specialty_code, specialty_name |

### `HospitalA2AServers.flogo` — A2A write agents (ports 9101–9104)

| Agent (tool) | Port | Action |
|--------------|------|--------|
| book_appointment_agent (`book_appointment`) | 9101 | INSERT into `appointments` (specialty, discharge_date + 7d, 10:30) |
| pharmacy_order_agent (`create_pharmacy_order`) | 9102 | INSERT into `pharmacy_orders` (one per medication) |
| bed_turnover_agent (`request_bed_cleaning`) | 9103 | UPDATE `beds` → CLEANING_REQUESTED + estimated ready |
| send_confirmation_email (`send_confirmation_email`) | 9104 | Gmail SMTP confirmation (invoked once, last) |

### `HospitalAIOrchestrator.flogo` — WebSocket brain (port 8082, `/ws/chat`)
`noop → agentactivity → wswritedata`. The AI Agent lists the MCP server under `mcpServers` and the four
agents under `remoteAgents`, classifies intent, and routes to tools/agents per the system prompt.

## Database (`hospital`, 8 tables)
`patients`, `patient_discharges`, `discharge_medications`, `appointments`, `medication_catalog`,
`pharmacy_orders`, `beds`, `specialties` — 10 demo patients with varied follow-up / medication / bed
states (see [`database.sql`](database.sql)).

```bash
psql -U postgres -d hospital -f database.sql      # schema + demo data
psql -U postgres -d hospital -f reset_data.sql    # reset to baseline (today-relative dates)
```

## Prerequisites & setup
- TIBCO Flogo Enterprise 2.26.5+, PostgreSQL 14+, an OpenAI (or on-prem) LLM key, a Gmail App Password.
- Create the `hospital` DB and load `database.sql`.
- Import the 3 `.flogo` apps. **Re-enter the secrets** (OpenAI API key, PG password, Gmail App Password)
  in Flogo Enterprise so they are stored encrypted — the CLI wrote them as plaintext placeholders (see
  FDA_BUILD_NOTES §1).
- Start order: **MCP (9092) → A2A (9101–9104) → Orchestrator (8082)**.
- Connect the chatbot UI (`demos/Agentic_AI/Chatbot`) to `ws://localhost:8082/ws/chat`.
- Demo prompts: [`prompts.md`](prompts.md). Reset between runs with `reset_data.sql`.

## Ports
| App | Port | Protocol |
|-----|------|----------|
| HospitalMCPServer | 9092 | HTTP (MCP), `/hospital-bss` |
| book_appointment / pharmacy / bed_turnover / email | 9101 / 9102 / 9103 / 9104 | HTTP (A2A) |
| HospitalAIOrchestrator | 8082 | WebSocket, `/ws/chat` |

## Verification performed
- All three apps pass `fda check-mappings` (23 rules) and are valid JSON.
- `database.sql`/`reset_data.sql` load into `hospital`; all 7 tool queries and the agent
  insert/update statements execute; bed turnover flips a bed to `CLEANING_REQUESTED`.
- Not run: `flogobuild` compile and a live LLM/WebSocket session (design-time + data-layer only).
