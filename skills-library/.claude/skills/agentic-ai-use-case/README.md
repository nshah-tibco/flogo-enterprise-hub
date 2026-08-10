# Agentic AI Use Case Builder (clone method) — User Guide

> Scaffold a complete, runnable **Agentic AI demo** for any business vertical by **cloning a proven, working use case** and swapping in your domain. You describe what you want and point to a reference app; the skill copies its exact structure, re-points it at your tables/tools/agents, and hands you a verified app set plus a checklist of the few things only you can configure.

This is a Claude Code **skill**. It builds the **same three-app system** as its sibling [`agentic-ai-use-case-fda`](../agentic-ai-use-case-fda/README.md) — the difference is *how*:

| | **`agentic-ai-use-case` (this skill)** | `agentic-ai-use-case-fda` |
|---|---|---|
| How apps are built | **Clone an existing working `.flogo` and swap fields** | Build from scratch with `fda` CLI commands |
| Best when | You have a **near-identical reference app** to copy (fastest, most reliable) | You want a clean from-scratch build with no leftover UUIDs/blobs |
| You must provide | Use case **+ a reference use case to clone** | Just the use case |

**Use this skill when a similar reference app already exists** (e.g. you want a banking assistant and the Telecom or Retail Banking use case is close in shape). It's the fastest, most reliable path because the working `contrib` blobs, secrets, and wiring come over verbatim.

---

## How to invoke it

The skill is **user-invocable**. Two ways:

1. **Slash command** — type `/agentic-ai-use-case` in Claude Code, then describe your domain and which reference app to clone.
2. **Natural language** — just ask; the skill auto-activates on requests like *"build/create/scaffold an agentic AI use case / chatbot / MCP + A2A + orchestrator demo for &lt;domain&gt;."*

> For the from-scratch CLI method instead, use `/agentic-ai-use-case-fda`.

---

## What it does

Given a domain description **and a reference use case to clone**, the skill produces a **three-app Agentic AI system** backed by PostgreSQL:

```
Chatbot UI --WebSocket--> AI Orchestrator --MCP (HTTP)--> MCP Server --\
                                 |                                      +--> PostgreSQL
                                 \--------A2A-------> A2A Servers ------/   (+ SMTP for email)
```

| App | Role |
|-----|------|
| **MCP Server** | Read-only lookups. One tool per table/join; stateless. The LLM picks the tool by its description. |
| **A2A Servers** | Write workflows — create/update, plus optional email. Each agent has its own trigger, port, and guardrails. |
| **AI Orchestrator** | The "brain." A WebSocket chat endpoint whose AI Agent activity classifies intent and routes to MCP tools or A2A agents. |

### What you get (generated files)

A new folder `demos/Agentic_AI/<UseCase>_Use_Case/` containing:

| File | Purpose |
|------|---------|
| `database.sql` | PostgreSQL schema + demo data, engineered so each scenario works (one clean case + one exception case per write agent). |
| `reset_data.sql` | Truncate + reload to reset between demos; volatile dates relative to today. |
| `<Prefix>MCPServer.flogo` | The MCP Server app — N read-only tools. |
| `<Prefix>A2AServers.flogo` | The A2A Servers app — M write/action agents. |
| `<Prefix>AIOrchestrator.flogo` | The AI Orchestrator app — WebSocket trigger + AI Agent routing. |
| `prompts.md` | Demo prompts grouped by scenario. |
| `README.md` | Architecture, tool/agent tables, DB summary, demo scenarios, ports, troubleshooting, and the manual setup steps. |

---

## Prerequisites

1. **TIBCO Flogo Enterprise** (design-time + runtime) to import, configure, and run the `.flogo` apps.
2. **PostgreSQL** — a reachable instance you can create a database in and load SQL into.
3. **An LLM provider** — an API key, a **real base URL** (e.g. `https://api.openai.com/v1`), and an accessible model.
4. *(Optional)* **SMTP** credentials (e.g. a Gmail app password) if you want an email/notification agent.
5. **A configured `config.md`** — the skill reads the psql path and PostgreSQL host/port/user/password from `skills-library/.claude/skills/config.md` at build time and **never hardcodes secrets**. Copy `config.example.md` to `config.md` and fill it in. `config.md` is gitignored — never commit it.
6. **A reference use case to clone** — one of the working demos under `demos/Agentic_AI/` (see the list below).

---

## Inputs it needs from you

Because this skill *clones*, the two most important inputs are **what to build** and **what to clone from**:

| Input | Why it's needed |
|-------|-----------------|
| **1. The use case to build** | The domain, the entities/scenarios the chatbot must handle, and the actions it should perform. Provide it as a one-line description, an interactive answer, or (recommended) a filled spec — see the [spec template](references/use-case-spec-template.md). |
| **2. The reference use case to clone** | Point to the closest working demo under `demos/Agentic_AI/`. Pick one whose **shape** matches — similar number of write agents, and whether it includes an email agent. The skill copies its structure and `contrib`/`SECRET:` values verbatim, so the closer the shape, the less rework. |

Then the skill asks only what changes the build:

| Clarifying question | Drives |
|---|---|
| **Domain entities & scenarios** | The PostgreSQL tables and the MCP read tools. |
| **Write workflows / A2A agents** | Each state-changing action becomes an A2A agent (confirm count + scope). |
| **Email/notification agent?** | Whether to include an SMTP agent. |
| **Locale / currency / persona** | So demo data feels realistic. |
| **Ports & folder** | Distinct port per app; default folder `demos/Agentic_AI/<UseCase>_Use_Case/`. |

### What the skill does, in order
1. **Reads your environment** from `config.md`.
2. **Frames the use case** back to you (who chats, what problem is automated, the solution shape).
3. **Asks clarifying questions** (only the ones that change the build).
4. **Presents a plan** for approval (tables, MCP tools, A2A agents, routing rules, ports, folder, scenarios).
5. **Builds** by cloning the chosen reference app's JSON shape and swapping in your tables, tool/agent names, SQL, system prompts, ports, and **fresh** connection UUIDs — carrying over `contrib` blobs and `SECRET:` values verbatim.
6. **Verifies** (SQL runs, JSON parses, connection/port consistency) and tells you what still needs a Flogo import + live run.

---

## Reference use cases available to clone

Pick the closest in shape to what you're building:

| Reference (`demos/Agentic_AI/…`) | Good starting point when you want… |
|---|---|
| `Telecom_Invoice_Chatbot_Use_Case` | A billing/invoice/account-lookup assistant with dispute/recharge write agents. |
| `Airline_Passenger_Services_Use_Case` | Booking/status lookups + rebooking/cancellation actions. |
| `Hospital_AI-Agent_Use_Case` | Patient/appointment lookups + scheduling/update actions (includes email). |
| `Retail_Banking_Assistant_Use_Case` | Account/transaction lookups + dispute/card actions. |
| `Logistics_Transport_Use_Case` | Shipment tracking + reassign/notify actions (includes email). |
| `Life_And_Pensions_Use_Case`, `Power_Distribution_Use_Case`, `Predictive_Maintenance_Use_Case` | Other verticals with the same 3-app pattern. |

> Tip: match on **whether it has an email agent** and the **number of write agents** first — that's what saves the most rework.

---

## Sample prompts

### Prompts to *invoke the skill* (build a new use case by cloning)

- *"Build an agentic AI demo for a **retail banking** assistant — clone the `Retail_Banking_Assistant_Use_Case`. Customers check balances/transactions and can dispute a charge or block a card."*
- *"Create an agentic AI **insurance claims** chatbot by cloning the `Hospital_AI-Agent_Use_Case` (it has the email agent I want): look up policies/claims, file a new claim, and email the adjuster."*
- *"Scaffold a **utilities/power outage** assistant based on `Power_Distribution_Use_Case` — look up outages by area and let users report a new outage."*
- *"Clone `Telecom_Invoice_Chatbot_Use_Case` into a **broadband ISP** support assistant: invoice lookups + a plan-change agent + a payment-dispute agent. Put it in `demos/Agentic_AI/ISP_Support_Use_Case/`."*

### Prompts to *try the running system* (also generated into `prompts.md`)

Once the three apps are imported, configured, and running, connect a chat/WebSocket client to `ws://<host>:<wsPort>/<usecase>`:

- *"What's my current balance and last 3 transactions?"* → MCP lookup tool.
- *"Dispute the $90 charge from yesterday and email me a confirmation."* → A2A write agent (+ email).
- *"Report a power outage at 12 Main St and tell me the ticket number."* → A2A write agent returning a new record.
- An **exception case** the seed data triggers (e.g. a lookup for a record that doesn't exist) → to demo graceful failure.

---

## Manual configuration you must do at the end

The clone carries the working `contrib` blobs and encrypted `SECRET:` values over verbatim, but a few things depend on **your** environment and can't be baked in. Configure these before an end-to-end run (the generated `README.md` also lists them, tailored to your use case):

1. **PostgreSQL** — create the database, load `database.sql` (then `reset_data.sql` to reset between demos), and update the connection's `Database_Name` (and Host/Port/User/Password) to your instance.
2. **LLM credentials & endpoint** — set your real `API_Key`, a **real** base URL (e.g. `https://api.openai.com/v1`), and a `LLM_Model` your key can access.
3. **Secrets in a different environment** — the cloned `SECRET:` values are encrypted for the app-key of the environment they came from. If you import into a **different** Flogo Enterprise instance, re-enter the API key, DB password, and email app password in **App Properties** so they re-encrypt for your environment. Keep property types as `string` (there is no `password` type).
4. **Ports** — the MCP, each A2A, and the orchestrator ports must be free; the orchestrator's MCP `serverUrl` and each A2A `serverUrl` must match those ports.
5. **Email / SMTP** *(only if an email agent is included)* — set `Email_Username`, the recipient, and the app password; confirm outbound SMTP (Gmail: `smtp.gmail.com:465`, SSL) is allowed from your host.
6. **Import & run in Flogo Enterprise** — import each app; if any trigger shows unrendered fields or a red ✗, click **Sync** on it; open each connection and **Test/Connect** to validate.
7. **Chatbot / WebSocket client** — point your UI (or a WS test client) at `ws://<host>:<wsPort>/<usecase>`. No UI is bundled.

### Pre-flight checklist

- [ ] DB created, `database.sql` loaded, row counts sane
- [ ] LLM `API_Key`, real base URL, and `LLM_Model` set (re-entered if a new environment)
- [ ] DB password + email app password re-entered as secrets if importing to a new environment
- [ ] All ports free; orchestrator MCP/A2A URLs match the MCP/A2A ports
- [ ] SMTP reachable (if email agent)
- [ ] Start order: **MCP → A2A → Orchestrator**; each logs a clean start
- [ ] WebSocket client connects to `ws://<host>:<wsPort>/<usecase>` and gets a reply

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Import fails / app won't load after cloning | A `contrib` blob or `SECRET:` value was regenerated by hand | Carry `contrib` + `SECRET:` values **verbatim** from the reference app; only change the DB name and domain fields. |
| PostgreSQL insert mapping shows a red ✗ | A `?param` name matches a column name | Name params so they don't match columns (append a digit), set `Parameter:true`, and map via `input.mapping.parameters` — see [postgres-activity-patterns.md](references/postgres-activity-patterns.md). |
| LLM call fails / posts to a bad URL | Base URL blank or wrong | Set a real endpoint (e.g. `https://api.openai.com/v1`). |
| A connection dropdown is empty / "Connection is required" | A `conn://` UUID doesn't match a connections-map key | Ensure every `conn://<uuid>` resolves to a key in that app's `connections` map. |
| Email/API/DB fails only after moving environments | Cloned `SECRET:` values don't decrypt under the new app-key | Re-enter those secrets in App Properties so they re-encrypt for your environment. |

---

## Related

- **Sibling skill:** [`agentic-ai-use-case-fda`](../agentic-ai-use-case-fda/README.md) — same output, built from scratch with the `fda` CLI (no clone needed).
- **Skill internals:** [`SKILL.md`](SKILL.md) (workflow + gotchas), [`references/flogo-app-templates.md`](references/flogo-app-templates.md) (exact JSON structure of all 3 apps), [`references/postgres-activity-patterns.md`](references/postgres-activity-patterns.md) (the #1 source of errors), [`references/data-and-docs.md`](references/data-and-docs.md), [`references/use-case-spec-template.md`](references/use-case-spec-template.md).
