# TIBCO Flogo® Agentic AI — Industry Use Cases

End-to-end, **industry-specific Agentic AI demos** built on **TIBCO Flogo® Enterprise**. Each use case shows the same reusable pattern — an **MCP Server** for read-only data tools, an **A2A Agents** app for guarded write workflows, and a **WebSocket AI Orchestrator** as the conversational brain — applied to a different vertical (banking, insurance, healthcare, telecom, utilities, aerospace, manufacturing, retail, real estate, and more).

New here? Read **[The Three-App Pattern](#the-three-app-pattern)**, browse the **[Use-Case Catalog](#use-case-catalog)** by industry, check the **[Prerequisites](#prerequisites)**, then follow the **[Quick Start](#quick-start)**. Every WebSocket use case is driven from the shared browser **[Chatbot](#chatbot--browser-test-client)**.

> **Looking for the connector fundamentals instead?** The [`samples/Agentic_AI/`](../../samples/Agentic_AI/) folder teaches the individual Agentic AI building blocks (LLM Client Activity, AI Agent Activity, AI Agent Trigger, custom guardrails, custom conversation stores, A2A protocol). This folder applies them to complete, PostgreSQL-backed business scenarios.

---

## The Three-App Pattern

Most use cases here ship the same **standard trio** of Flogo apps plus a PostgreSQL database. Understand it once and every use case reads the same way:

| App | Role | Trigger | Talks to |
|---|---|---|---|
| **`*MCPServer.flogo`** | Exposes **read-only** business data as MCP tools (query customers, policies, invoices, tickets…). Returns all rows; the orchestrator filters. | HTTP (streamable MCP) | PostgreSQL |
| **`*A2AServers.flogo`** | One **A2A agent per guarded write action** (open a ticket, submit a claim, schedule a visit, send email…). Each agent runs on its own port. | A2A server (one port each) | PostgreSQL / SMTP |
| **`*AIOrchestrator.flogo`** | The **conversational brain**: classifies intent, calls MCP read tools, hands off to A2A write agents, and enforces confirm-before-write guardrails. | WebSocket (`wsserver`) | LLM · MCP · A2A |

```
   Browser Chatbot  ──ws──▶  AI Orchestrator  ──▶  LLM (OpenAI / Gemini / Anthropic)
                                   │  ├──▶ MCP Server   ──▶ PostgreSQL   (reads)
                                   │  └──▶ A2A Agents   ──▶ PostgreSQL / SMTP  (guarded writes)
```

A few use cases deliberately vary this shape — see the **Variant** column and the [status legend](#status-legend). BusinessWorks (BW6) and REST-tier variants ship their own detailed READMEs.

---

## Use-Case Catalog

Grouped by **industry vertical**. Click a use case to open its folder and full README. Ports are the defaults baked into each app (all configurable). "Endpoints" reads *WebSocket · MCP · A2A range*.

### Aerospace & Defense

| Use Case | What it does | Endpoints | Database | Status |
|---|---|---|---|---|
| [Aerospace MRO & AOG Operations](./Aerospace_Defense_MRO_Use_Case/) | Maintenance/repair/overhaul + aircraft-on-ground assistant — check work orders & parts, then schedule/dispatch. | WS `:8085` `/mro` · MCP `:9095` · A2A `8091–8094` | `aerospace_mro` | ✅ Complete |

### Banking, Financial Services & Insurance

| Use Case | What it does | Endpoints | Database | Status |
|---|---|---|---|---|
| [Retail Banking Assistant](./Retail_Banking_Assistant_Use_Case/) | Balances, transactions, cards & payments self-service with guarded write actions. | WS `:8088` `/banking` · MCP `:9096` · A2A `8710–8712` | `banking` | ✅ Complete · 🖼️ deck |
| [Life & Pensions Member Assistant](./Life_And_Pensions_Use_Case/) | Pension pots, holdings, contributions, beneficiaries, claims & adviser callbacks; email confirmations. | WS `:9600` `/lifepensions` · MCP `:9982` · A2A `9983–9988` | `life_pensions` | ✅ Complete |
| [Auto Insurance Policyholder Assistant](./Auto_Insurance_Assistant_Use_Case/) | Policy, coverage & claims assistant, **grounded on policy documents via RAG**. | WS `:9700` `/auto-insurance` · MCP `:9701` · A2A `9711–9714` | `auto_insurance` (+ vector store) | 🔍 RAG |

### Healthcare

| Use Case | What it does | Endpoints | Database | Status |
|---|---|---|---|---|
| [Hospital Post-Discharge Assistant](./Hospital_AI-Agent_Use_Case/) | Post-discharge coordination — care instructions, appointments, refills, follow-ups. | WS `:8652` `/hospital` · MCP `:9092` · A2A `8070–8073` | `hospital` | 🔌 REST-tier |
| [Hospital — FDA CLI Rebuild](./Hospital_FDA_Rebuild/) | The same hospital demo rebuilt **entirely via the `fda` CLI**, shipping runnable Windows binaries. | WS `:8652` `/hospital` · MCP `:9092` · A2A `8070–8073` | `hospital` (parent's) | 📦 Prebuilt binaries |

### Telecommunications

| Use Case | What it does | Endpoints | Database | Status |
|---|---|---|---|---|
| [Telecom Invoice Chatbot](./Telecom_Invoice_Chatbot_Use_Case/) | Explain invoices, usage & charges; dispute, adjust and email confirmations. | WS `:9500` `/telecom` · MCP `:9882` · A2A `9883–9885` | `telecom` | ✅ Complete |

### Utilities & Energy

| Use Case | What it does | Endpoints | Database | Status |
|---|---|---|---|---|
| [Electric Power Distribution](./Power_Distribution_Use_Case/) | Residential self-service — bills, usage, outages; report outage, schedule visit, reconnect (past-due guardrail). | WS `:9680` `/grid` · MCP `:9682` · A2A `9683–9686` | `power_distribution` | ✅ Complete · 🖼️ deck |
| [Residential Water Utility](./Water_Utility_Use_Case/) | Water customer self-service (bills, usage, service requests). | WS `:9780` `/water` · MCP `:9782` · A2A `9783–9786` *(intended)* | `water_utility` *(intended)* | 📄 Stub |

### Manufacturing & Industrial

| Use Case | What it does | Endpoints | Database | Status |
|---|---|---|---|---|
| [Semiconductor Customer & Order Assistant](./Semiconductor_Customer_Use_Case/) | Parts catalog, orders, RMAs & lead times for a semiconductor supplier. | WS `:8088` `/semiconductor` · MCP `:9098` · A2A `8730–8735` | `semiconductor` | ✅ Complete |
| [Predictive Maintenance & Asset Monitoring](./Predictive_Maintenance_Use_Case/) | Asset health, sensor readings & failure prediction with a REST backend and a single chat agent. | WS `:8083` `/ws/chat` · MCP `:9093` · REST api `:9095` | `predictive_maintenance` | 🔌 REST-tier |
| [Air Liquide — Smart Operations](./air_liquide_demo/) | Gas-cylinder logistics assistant on **TIBCO BusinessWorks 6.12** — agentic MCP tool-calling + document RAG (no Flogo trio). | BW REST `:8080` · BW MCP `:18000` · RAG `:5000`/`:7312` · proxy `:3001` | *(none — BW6 vector store)* | 🏛️ BW6 · 🔍 RAG |

### Transportation, Travel & Logistics

| Use Case | What it does | Endpoints | Database | Status |
|---|---|---|---|---|
| [Airline Passenger Services](./Airline_Passenger_Services_Use_Case/) | Flights, bookings, seats & baggage passenger assistant. | WS `:8083` `/airline` · MCP `:9093` · A2A `8074–8076` | `airline` | 🔌 REST-tier |
| [Logistics / Transport Shipper Assistant](./Logistics_Transport_Use_Case/) | Shipment tracking, quotes & bookings; ships runnable binaries + FDA build script. | WS `:9690` `/logistics` · MCP `:9790` · A2A `9791–9794` | `logistics` | 📦 Prebuilt binaries |
| [Maritime Container Shipping](./Container_Shipping_Use_Case/) | Container-shipping customer self-service. **MCP + DB done; A2A/Orchestrator still being converted.** | MCP `:9720` `/shipping-bss` (real) · WS/A2A *stale* | `container_shipping` | 🚧 WIP |

### Retail & Consumer

| Use Case | What it does | Endpoints | Database | Status |
|---|---|---|---|---|
| [Retail — BW & Flogo, Better Together](./Retail_AI_BW_Flogo/) | Retail assistant where **BW6 apps expose domain REST/MCP** and a Flogo **REST** orchestrator drives the LLM. | Flogo REST `:18085` `/api/query` · BW6 MCP `:18000` | *(inside BW6 apps)* | 🏛️ BW6 |

### Real Estate

| Use Case | What it does | Endpoints | Database | Status |
|---|---|---|---|---|
| [Real Estate Lead Engagement Assistant](./Real_Estate_Lead_Assistant_Use_Case/) | MLS search & lead engagement; trio generated via `fda` CLI build scripts. | WS `:9590` `/realestate` · MCP `:9592` · A2A `9593–9597` | `realestate` | ✅ Complete |

### Status Legend

| Badge | Meaning |
|---|---|
| ✅ **Complete** | Standard MCP + A2A + Orchestrator trio, ready to run out of the box. |
| 🔍 **RAG** | Adds retrieval-augmented generation (a document ingestion app + vector store) on top of the trio. |
| 🏛️ **BW6** | Built on **TIBCO BusinessWorks 6** rather than (or alongside) the Flogo trio — different runtime; see its own README. |
| 🔌 **REST-tier** | Includes legacy REST API / single-agent apps alongside (or instead of) the standard trio. |
| 📦 **Prebuilt binaries** | Ships compiled `.exe` executables so you can run without building. |
| 🚧 **WIP** | Work in progress — some apps are unconverted copies; read the in-folder "Build status" note first. |
| 📄 **Stub** | README documents the intended design, but the runnable apps are not present yet. |
| 🖼️ **deck** | Includes an architecture slide deck. |

> **Port collisions — don't run these pairs at once (defaults overlap):**
> Retail Banking & Semiconductor both use WS `:8088`; Airline & Predictive Maintenance both use WS `:8083`; Life & Pensions and Container Shipping both use WS `:9600` + A2A `9983–9988`. Hospital's two variants share the same ports because they are the same demo built two ways. Change a port in the app properties to run overlapping demos simultaneously.

---

## Prerequisites

All standard-trio use cases need:

- **TIBCO Flogo® Enterprise 2.26.x or later** with the [Flogo VS Code extension](https://marketplace.visualstudio.com/items?itemName=tibco.flogo) — see the [Agentic AI documentation](https://docs.tibco.com/pub/flogo/latest/doc/html/Default.htm#connectors/agentic-AI/agentic-AI-overview.htm).
- **PostgreSQL 14+** (local or remote) — each use case creates its own database.
- An **LLM API key** for your provider (OpenAI, Gemini, or Anthropic). The default model referenced in the demos is `gpt-5.6`; substitute any model your account can access. On-prem / OpenAI-compatible endpoints work via the connection's base-URL field.
- A **WebSocket client** — the included [Chatbot](#chatbot--browser-test-client) (Node.js 16+) or [websocat](https://github.com/vi/websocat).

Some use cases have extra prerequisites — check the **Status** column and each folder's README:

- **🔍 RAG** (Auto Insurance, Air Liquide): a document set + vector store; Auto Insurance ingests policy PDFs.
- **🏛️ BW6** (Air Liquide, Retail_AI_BW_Flogo): **TIBCO BusinessWorks 6.12** and Node.js for the MCP proxy.
- **SMTP** (Life & Pensions, Telecom, Power Distribution and others with an email agent): an SMTP account — e.g. Gmail with an App Password over SSL (port 465).

> **Credentials are not shipped.** Every app property that held a secret is reset to a placeholder (`SECRET:YOURKEY` for connection API keys). Set your own OpenAI key, PostgreSQL password, and SMTP credentials before running — see each use case's README / `manual-steps.md`.

---

## Quick Start

Using a standard-trio (✅) use case — the steps are identical for each; only the database name, ports, and WebSocket path change (see the [catalog](#use-case-catalog)).

**1. Create and load the database** (example uses Life & Pensions):

```bash
cd demos/Agentic_AI/Life_And_Pensions_Use_Case
createdb life_pensions                          # or: psql -U postgres -c "CREATE DATABASE life_pensions;"
psql -U postgres -d life_pensions -f database.sql
psql -U postgres -d life_pensions -f reset_data.sql   # optional: refresh demo dates relative to today
```

**2. Import the three apps** into Flogo Enterprise (VS Code Flogo extension): the `*MCPServer.flogo`, `*A2AServers.flogo`, and `*AIOrchestrator.flogo` for that use case.

**3. Set the app properties** — PostgreSQL host/port/database/user/password, your **OpenAI API key** and model, ports, and (if the use case has an email agent) SMTP settings. The exact property names are in each README / `manual-steps.md`.

**4. Start the apps in order** (the orchestrator needs the others running first):

```
1) *MCPServer          → HTTP MCP port ready first
2) *A2AServers         → all A2A agent ports
3) *AIOrchestrator     → WebSocket port (needs MCP + A2A up)
```

**5. Connect the Chatbot** and start chatting:

```bash
cd demos/Agentic_AI/Chatbot
npm install
npm start                 # http://localhost:3000
# In the UI, set the WebSocket URL for your use case and click Connect, e.g.:
#   ws://localhost:9600/lifepensions
```

**6. Run the demo** using the prompts in that use case's `prompts.md`. After a run that performed writes, re-run `reset_data.sql` to restore the seeded data.

> 🏛️ **BW6** and 📦 **prebuilt-binary** use cases start differently (TIBCO Business Studio / running the `.exe` directly) — follow their own READMEs.

---

## Chatbot — Browser Test Client

A ready-to-use, domain-agnostic chat UI in [`Chatbot/`](./Chatbot/) drives every use case that exposes a WebSocket endpoint. It supports multiple concurrent sessions, an editable WebSocket URL, and a live connection indicator.

```bash
cd demos/Agentic_AI/Chatbot
npm install
npm start
# Open http://localhost:3000, set the WebSocket URL for your use case
# (ws://localhost:<orchestrator-port><path>), and click Connect.
```

---

## Feedback

Please contact us at [integration-pm@tibco.com](mailto:integration-pm@tibco.com) with any queries, feedback, or comments.

<!-- SEO Keywords: TIBCO Flogo, Agentic AI, AI Agents, MCP, MCP Server, Model Context Protocol, A2A, Agent-to-Agent, LLM Orchestration, WebSocket, PostgreSQL, RAG, Retrieval Augmented Generation, BusinessWorks, Industry Use Cases, Banking, Insurance, Healthcare, Telecom, Utilities, Aerospace, Manufacturing, Retail, Real Estate, Low-Code, iPaaS, Enterprise AI -->

**Topics:** `Agentic AI` · `MCP Server` · `A2A` · `LLM Orchestration` · `Industry Demos` · `Low-Code`
