# Airline Passenger Services Use Case

An agentic AI system built on TIBCO Flogo Enterprise that handles flight disruption management for a hub-and-spoke airline operating through Atlanta (ATL). The system uses a 3-tier architecture with an AI Orchestrator, MCP Server for data queries, and A2A Servers for business logic -- all communicating via standard protocols (MCP, A2A, WebSocket).

---

## Architecture Overview

```
                    ┌─────────────────────────┐
                    │     Chatbot UI          │
                    │  (WebSocket Client)     │
                    └───────┬─────────────────┘
                            │ WebSocket
                            │ ws://localhost:8083/ws/chat
                            ▼
               ┌────────────────────────────────┐
               │  Passenger Services            │
               │  AI Orchestrator               │
               │  (PassengerServicesAIOrch.)    │
               │  Port 8083 (WebSocket)         │
               │  LLM: OpenAI GPT-4o           │
               └───────┬───────────┬────────────┘
                       │           │
          MCP (HTTP)   │           │  A2A Protocol
                       ▼           ▼
    ┌──────────────────────┐   ┌──────────────────────────────┐
    │  Passenger Services  │   │  Passenger Services          │
    │  MCP Server          │   │  A2A Servers                 │
    │  Port 9093           │   │                              │
    │  /airlinemcpserver   │   │  connection_risk_agent :8074 │
    │                      │   │  rebook_passenger_agent:8075 │
    │  Tools (read-only):  │   │  send_confirmation_email:8076│
    │  - GetFlights        │   │                              │
    │  - GetPassengers     │   │  Uses PostgreSQL for         │
    │  - GetFrequentFlyer  │   │  data queries & updates      │
    │  - GetBookings       │   │  + Gmail SMTP for email      │
    │  - GetBookingSegments│   │                              │
    └──────────┬───────────┘   └──────────────┬───────────────┘
               │                              │
               └──────────────┬───────────────┘
                              ▼
               ┌────────────────────────────┐
               │  PostgreSQL Database       │
               │  Database: airline         │
               │  6 Tables                  │
               └────────────────────────────┘
```

---

## Flogo Apps

### 1. `PassengerServicesMCPServer.flogo` -- MCP Server (Port 9093)

Exposes 5 read-only AI tools via the Model Context Protocol over Streamable HTTP. Each tool queries the PostgreSQL `airline` database and returns the full result set as a string.

| Tool | Description | SQL |
|------|-------------|-----|
| **GetFlights** | Flight schedule with real-time status, delays, gates | `SELECT * FROM flights` |
| **GetPassengers** | Passenger contact details and identity | `SELECT * FROM passengers` |
| **GetFrequentFlyer** | Loyalty tier, miles balance, YTD tier miles | `SELECT * FROM frequentflyer` |
| **GetBookings** | PNR booking records with status | `SELECT * FROM bookings` |
| **GetBookingSegments** | Individual flight legs per booking | `SELECT * FROM booking_segments` |

### 2. `PassengerServicesA2AServers.flogo` -- A2A Servers (Ports 8074-8076)

Three A2A agents that handle business logic. Each agent has its own LLM, system prompt, and tool handler.

| Agent | Port | Description |
|-------|------|-------------|
| **connection_risk_agent** | 8074 | Analyzes passenger bookings to assess connection risk. Queries booking segments joined with flight data and all available flights. Calculates connection time and identifies alternatives. |
| **rebook_passenger_agent** | 8075 | Rebooks disrupted passengers. Updates `booking_segments` table (new flight, seat, status=REBOOKED) and inserts into `rebooking_log`. |
| **send_confirmation_email** | 8076 | Sends rebooking confirmation email via Gmail SMTP. Invoked only once after rebooking is complete and user requests it. |

### 3. `PassengerServicesAIOrchestrator.flogo` -- AI Orchestrator (Port 8083)

The main orchestration app. Exposes a WebSocket endpoint for natural language chat. Uses an AI Agent activity that routes requests to either MCP tools (for data queries) or A2A agents (for business logic).

| Setting | Value |
|---------|-------|
| WebSocket Path | `/ws/chat` |
| LLM | OpenAI GPT-4o |
| MCP Server | `http://localhost:9093/airlinemcpserver` |
| A2A Agents | connection_risk (8074), rebook (8075), email (8076) |

---

## Database

6 tables in the PostgreSQL `airline` database:

| Table | Purpose | Records |
|-------|---------|---------|
| `flights` | Flight schedule with status and delays | 32 flights through ATL hub (several delayed/cancelled, with alternatives) |
| `passengers` | Passenger master records | 22 passengers from 8 countries |
| `frequentflyer` | Loyalty program (Basic/Silver/Gold/Platinum) | 22 members |
| `bookings` | PNR booking records | 22 PNRs |
| `booking_segments` | Multi-leg itineraries per booking | 41 segments |
| `rebooking_log` | Tracks all rebookings (starts empty) | Populated by rebook agent |

```bash
# Initialize schema and demo data
psql -U postgres -d airline -f database.sql

# Reset with today-relative flight times (for live demos)
psql -U postgres -d airline -f reset_data.sql
```

---

## Demo Scenarios

### Scenario 1: Carlos Martinez (Gold) -- Missed Connection

Carlos is on FL801 DEN->ATL (delayed 90 min) connecting to FL445 ATL->MIA. His estimated arrival at ATL is 12:45 but FL445 departs at 12:30 -- he will miss his connection.

```
You:   Hi, I'm on flight FL801 from Denver. What's the status?
Agent: FL801 is currently DELAYED by 90 minutes... estimated arrival at ATL is 12:45 PM.

You:   Oh no, I have a connection. My booking is ABCDE1. Will I make it?
Agent: Looking at your booking... your connecting flight FL445 ATL->MIA departs at 12:30.
       With FL801 arriving at 12:45, you would MISS your connection. I recommend rebooking
       you on FL447 ATL->MIA departing at 15:30.

You:   Yes, please rebook me on FL447.
Agent: Done! You've been rebooked from FL445 to FL447 ATL->MIA, seat 5A. Your new departure
       is at 15:30 with arrival in Miami at 19:45.

You:   Can you send me a confirmation email?
Agent: Confirmation email sent to carlos.martinez@email.com.
```

### Scenario 2: Maria Fernandez (Basic) -- Tight Connection

Maria is on FL510 SEA->ATL (delayed 45 min) connecting to FL612 ATL->ORD. Her estimated arrival is 13:30 and FL612 departs at 14:00 -- only 30 minutes, which is AT_RISK.

```
You:   What's happening with flight FL510?
You:   My PNR is PQRST4. Am I going to make my connection to Chicago?
```

### Scenario 3: Roberto Gonzalez (Platinum) -- No Disruption

Roberto has a direct flight FL445 ATL->MIA, which is on time. PNR: KLMNO3.

```
You:   What's the status of FL445?
You:   Great, my booking is KLMNO3. Can you confirm everything looks good?
```

---

## Sample Data Summary

### Passengers and Bookings

| PNR | Passenger | Loyalty | Route | Connection scenario |
|-----|-----------|---------|-------|---------------------|
| ABCDE1 | Carlos Martinez | Gold | DEN->ATL->MIA | FL801 delayed 90 min → **MISSED** FL445 (alt FL447/FL449) |
| FGHIJ2 | Ana Silva | Silver | LAX->ATL->JFK | On time → SAFE (90 min) |
| KLMNO3 | Roberto Gonzalez | Platinum | ATL->MIA (direct) | Direct, no connection |
| PQRST4 | Maria Fernandez | Basic | SEA->ATL->ORD | FL510 delayed 45 min → **AT_RISK** (30 min) |
| UVWXY5 | Jorge Lopez | Silver | BOS->ATL->MIA | On time → SAFE (120 min) |
| BCDEF6 | Isabella Ramirez | Gold | DEN->ATL (one-way) | FL801 delayed, no connection |
| GHIJK7 | Diego Torres | Basic | DEN->ATL->JFK | FL801 delayed 90 min → **MISSED** FL302 (alt FL304/FL306) |
| LMNOP8 | Camila Rojas | Gold | LAX->ATL->ORD | On time → SAFE (150 min) |
| HIJKL9 | Lucas Pereira | Silver | LAX->ATL->JFK | FL217 delayed 120 min → **MISSED** FL304 (alt FL306) |
| MNOPQ0 | Sofia Castro | Gold | SFO->ATL->SEA | FL620 delayed 180 min → **MISSED** FL717 (no same-day alt) |
| RSTUV1 | Mateo Ramos | Basic | JFK->ATL->ORD | FL412 delayed 75 min → **AT_RISK** (45 min; alt FL616) |
| WXYZA2 | Valeria Cruz | Platinum | BOS->ATL->MIA | FL727 delayed 60 min → **MISSED** FL447 (alt FL449) |
| BCDFG3 | Nicolas Vargas | Silver | SEA->ATL->LAX | On time → SAFE (120 min) |
| HJKLM4 | Gabriela Mendez | Gold | DEN->ATL->SEA | FL801 delayed 90 min but SAFE (105 min) |
| NPQRS5 | Daniel Ortiz | Basic | ORD->ATL->MIA | Inbound FL932 **CANCELLED** (rebook needed) |
| TVWXY6 | Renata Alves | Silver | JFK->ATL->MIA | On time → **AT_RISK** (45 min; alt FL447) |
| ZABCD7 | Tomas Reyes | Gold | LAX->ATL->SEA | On time → SAFE (180 min) |
| EFGHI8 | Elena Navarro | Platinum | SFO->ATL->DEN | FL620 delayed 180 min but SAFE (60 min) |
| JKLMN9 | Felipe Guerrero | Basic | DEN->ATL->BOS | Tight schedule → **MISSED** FL730 (0 min; alt FL732) |
| OPQRS0 | Paula Rios | Silver | ATL->SFO (direct) | Direct, no connection |
| UVWXZ1 | Valentina Herrera | Platinum | MIA->ATL->DEN | On time → SAFE (225 min, long layover) |
| CDEFH2 | Andres Morales | Silver | BOS->ATL->JFK | FL727 delayed 60 min → **AT_RISK** (30 min; alt FL306) |

### Flights (32 total)

**Inbound to ATL** (delays here drive connection risk):

| Flight | Route | Status | Delay | Gate |
|--------|-------|--------|-------|------|
| FL801 | DEN -> ATL | DELAYED | 90 min | B12 |
| FL803 | DEN -> ATL | ON_TIME | -- | B14 |
| FL215 | LAX -> ATL | ON_TIME | -- | C04 |
| FL217 | LAX -> ATL | DELAYED | 120 min | C06 |
| FL510 | SEA -> ATL | DELAYED | 45 min | C08 |
| FL512 | SEA -> ATL | ON_TIME | -- | C10 |
| FL725 | BOS -> ATL | ON_TIME | -- | B06 |
| FL727 | BOS -> ATL | DELAYED | 60 min | B08 |
| FL930 | ORD -> ATL | ON_TIME | -- | B10 |
| FL932 | ORD -> ATL | CANCELLED | -- | B11 |
| FL410 | JFK -> ATL | ON_TIME | -- | A05 |
| FL412 | JFK -> ATL | DELAYED | 75 min | A07 |
| FL620 | SFO -> ATL | DELAYED | 180 min | C12 |
| FL450 | MIA -> ATL | ON_TIME | -- | A09 |

**Outbound from ATL** (multiple frequencies per route give rebooking alternatives):

| Flight | Route | Dep (ATL) | Gate |
|--------|-------|-----------|------|
| FL445 / FL447 / FL449 | ATL -> MIA | 12:30 / 15:30 / 18:30 | A08 / A12 / A10 |
| FL302 / FL304 / FL306 | ATL -> JFK | 13:00 / 16:00 / 19:30 | A15 / A16 / A17 |
| FL612 / FL614 / FL616 | ATL -> ORD | 14:00 / 17:00 / 20:00 | A20 / A21 / A23 |
| FL520 / FL522 | ATL -> LAX | 15:00 / 18:00 | A22 / A24 |
| FL715 / FL717 | ATL -> SEA | 14:30 / 18:15 | C14 / C16 |
| FL810 / FL812 | ATL -> DEN | 16:00 / 19:00 | B16 / B18 |
| FL730 / FL732 | ATL -> BOS | 15:45 / 19:15 | B20 / B22 |
| FL625 | ATL -> SFO | 16:30 | C18 |

---

## Port Summary

| App | Port | Protocol |
|-----|------|----------|
| PassengerServicesMCPServer | 9093 | HTTP (MCP) |
| PassengerServicesA2AServers - connection_risk | 8074 | HTTP (A2A) |
| PassengerServicesA2AServers - rebook_passenger | 8075 | HTTP (A2A) |
| PassengerServicesA2AServers - send_email | 8076 | HTTP (A2A) |
| PassengerServicesAIOrchestrator | 8083 | WebSocket |

---

## Supporting Files

| File | Description |
|------|-------------|
| `database.sql` | PostgreSQL schema with 6 tables and demo data |
| `reset_data.sql` | Data reset script using `CURRENT_DATE` for today-relative flight times |
| `prompts.md` | Demo prompts organized by scenario |
| `manual-steps.md` | Step-by-step setup and deployment instructions |

---

## Legacy Files

The following files are from an earlier 2-tier prototype and are kept for reference:

| File | Description |
|------|-------------|
| `airline-agent.flogo` | Original 2-tier AI agent (WebSocket + MCP only, no A2A) |
| `airline-mcp-server.flogo` | Original MCP server with mock data (no PostgreSQL) |
