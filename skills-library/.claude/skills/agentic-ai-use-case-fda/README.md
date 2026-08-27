# Agentic AI Use Case Builder for Flogo — User Guide

> Scaffold a complete, runnable **Agentic AI demo** for any business vertical — built entirely with the **Flogo Design CLI (`flogodesign-cli`, aka `fda`)**, command by command. You describe the domain; the skill builds the database, the MCP server, the A2A action agents, and the WebSocket AI orchestrator, wires them together, and hands you a verified app set plus a checklist of the few things only you can configure.

This is a Claude Code **skill**. No manual JSON editing is involved; every part of every app is generated through `fda` commands.

---

## How to invoke it

The skill is **user-invocable**. Two ways:

1. **Slash command** — type `/agentic-ai-use-case-fda` in Claude Code, then describe your domain.
2. **Natural language** — just ask; the skill auto-activates on requests like *"build/create/scaffold an agentic AI use case / chatbot / MCP + A2A + orchestrator demo for &lt;domain&gt;, built via the FDA CLI."*

> Prefer to **clone a similar existing app** instead of building from scratch? Use the sibling skill `/agentic-ai-use-case` — see [its guide](../agentic-ai-use-case/README.md).

---

## What it does

Given a description of a business domain (e.g. *"a hospital patient-services assistant"* or *"an airline passenger-services agent"*), the skill produces a **three-app Agentic AI system** backed by PostgreSQL:

```
Chatbot UI --WebSocket--> AI Orchestrator --MCP (HTTP streamable)--> MCP Server --\
                                 |                                                 +--> PostgreSQL
                                 \-----------A2A (HTTP)-----> A2A Agents ----------/   (+ REST backends / SMTP)
```

| App | Role |
|-----|------|
| **MCP Server** | Read-only lookups. One tool per table/query; stateless and safe to retry. The LLM picks the right tool from its description. |
| **A2A Agents** | Action workflows — database writes, REST calls to backends, sending email. Each agent has its own trigger, port, and guardrails. |
| **AI Orchestrator** | The "brain." A WebSocket chat endpoint driven by an AI Agent activity that decides intent and routes to MCP tools or hands off to A2A agents. |

### What you get (generated files)

A new folder (default `demos/Agentic_AI/<UseCase>_Use_Case/`) containing:

| File | Purpose |
|------|---------|
| `database.sql` | PostgreSQL schema + demo data, engineered so each demo scenario works (one clean case + one exception case per action agent). |
| `reset_data.sql` | Truncate + reload to reset between demos; volatile dates are relative to today. |
| `<Prefix>MCPServer.flogo` | The MCP Server app — N read-only tools. |
| `<Prefix>A2AServers.flogo` | The A2A Agents app — M action agents. |
| `<Prefix>AIOrchestrator.flogo` | The AI Orchestrator app — WebSocket trigger + AI Agent routing. |
| `prompts.md` | Demo prompts grouped by scenario, to try against the running system. |
| `README.md` | Architecture, tool/agent tables, DB summary, demo scenarios, ports, troubleshooting, and the **"below things are not configured…"** manual checklist. |

---

## Prerequisites

Before running the skill, make sure you have:

1. **Flogo Design CLI (`flogodesign-cli` / `fda`)** and **`flogobuild`** installed (they ship with the TIBCO Flogo VS Code extension). The skill prints their path and version before running anything.
2. **PostgreSQL** — a reachable instance you can create a database in and load SQL into.
3. **An LLM provider** — an API key, a **real base URL** (e.g. `https://api.openai.com/v1`), and a model your key can access.
4. *(Optional)* **SMTP** credentials (e.g. a Gmail app password) if you want an email/notification agent.
5. **A configured `config.md`** — the skill reads all of the above from `skills-library/.claude/skills/config.md` at build time and **never hardcodes secrets**. Copy `config.example.md` to `config.md` and fill in your values. `config.md` is gitignored and must never be committed.

---

## How to use it

Ask Claude Code to build an agentic use case. Two ways to provide the domain:

### Option A — Interactive (just describe it)
Give a one-line domain description and let the skill ask you the clarifying questions:

> *"Build an agentic AI demo for a hospital patient-services assistant using the FDA method."*

### Option B — Spec-driven (recommended for anything real)
Fill out the use-case spec template and hand it in. The skill treats it as the plan input:

> *"Here's my filled use-case spec — build the agentic AI app set with FDA: `my-usecase.spec.md`"*

The spec template lives at
[`../agentic-ai-use-case/references/use-case-spec-template.md`](../agentic-ai-use-case/references/use-case-spec-template.md).
It maps directly to the build: information lookups → MCP tools, actions/workflows → A2A agents, entities → tables, scenarios/seed data → `database.sql` + `prompts.md`, acceptance criteria → verification.

### What the skill does, in order
1. **Reads your environment** from `config.md`; prints tool paths + versions.
2. **Frames the use case** back to you (who chats, what problem is automated, the solution shape).
3. **Asks clarifying questions** (only the ones that change the build — see below).
4. **Presents a plan** for approval (tables, MCP tools, A2A agents, routing rules, ports, folder, and what will land in the manual-config section).
5. **Builds** every app with `fda` commands.
6. **Verifies** (SQL runs, JSON parses, mapping checks, connection/port consistency) and hands you the manual checklist.

> ⚠️ The skill **does not build executables/binaries by default.** It stops at design-time verification and hands off. Ask explicitly if you want it to `flogobuild` the `.exe` apps.

---

## Inputs it needs from you

The skill asks only what changes the build:

| Input | Drives |
|-------|--------|
| **Domain entities & scenarios** | The PostgreSQL tables and the MCP read tools. (It proposes a default set; you confirm or trim.) |
| **Action workflows / A2A agents** | Each state-changing action becomes an A2A agent. For each, is it a **DB write**, a **REST call to a backend**, or **email**? |
| **Email/notification agent?** | Whether to include an SMTP agent. |
| **LLM provider + model + base URL** | The orchestrator and A2A agents' AI config (defaults from `config.md`). The base URL **must** be a real endpoint. |
| **Locale / persona** | So demo data feels realistic. |
| **Ports & folder** | Distinct port per app/agent; default folder `demos/Agentic_AI/<UseCase>_Use_Case/`. |

Everything else (secrets, connection UUIDs, tool/handler schemas, orchestrator routing wiring) is handled automatically.

---

## Sample prompts

### Prompts to *invoke the skill* (build a new use case)

- *"Build an agentic AI demo for a **retail order-management** assistant: customers check order status and can request a return or reschedule delivery. Include an email confirmation agent."*
- *"Create an FDA-based agentic app set for a **bank customer-service** agent — look up accounts and recent transactions (MCP), and let it open a dispute or block a card (A2A, DB writes)."*
- *"Scaffold an **insurance claims** assistant: look up policies and claim status; A2A agents to file a new claim and to email the adjuster. LLM = OpenAI gpt-4o."*
- *"Build a **logistics/transport** dispatch assistant — track shipments, reassign a driver, and notify the customer by email. Put it in `demos/Agentic_AI/Logistics_Transport_Use_Case/`."*

### Prompts to *try the running system* (examples the skill also generates into `prompts.md`)

Once the three apps are running and you connect a chat/WebSocket client to `ws://<host>:<wsPort>/<usecase>`:

- *"What's the status of order 10432?"* → orchestrator calls an MCP lookup tool.
- *"Reschedule that delivery to Friday and email me the confirmation."* → orchestrator hands off to an A2A action agent (DB write + email).
- *"Show me all open claims for policy P-556 and file a new claim for a broken windshield."* → one MCP lookup + one A2A write in a single conversation.
- An **exception case** the seed data is engineered to trigger (e.g. *"cancel order 99999"* where the order doesn't exist) → so you can demo graceful failure.

---

## Manual configuration you must do at the end

`fda` builds the entire app graph, but a few things depend on **your** environment, **your** secrets, or a **running backend** — they can't be baked into a portable, secret-free app. The generated `README.md` ends with a full **"below things are NOT configured…"** section; here's the summary. The complete, authoritative checklist (with the exact reasons and error messages) is in
[`references/manual-config-gap.md`](references/manual-config-gap.md).

1. **LLM credentials & endpoint** — set the real `API_Key`, a **real** `LLM_Base_URL` (a blank one becomes the literal `New_value` and fails), and a `LLM_Model` your key can access.
2. **PostgreSQL** — create the DB, load `database.sql`, and set the connection Host/Port/Database/User/Password to your instance.
3. **Ports** — MCP, each A2A, and the orchestrator ports must be free; the orchestrator's MCP/A2A `serverUrl`s must match those ports.
4. **REST backends** *(only if a REST agent was requested)* — the target API must be running and reachable.
5. **Email / SMTP** *(only if an email agent is included)* — set `Email_Username`, the recipient, and **re-enter `Email_App_Password` in the designer's App Properties so it's stored as a `SECRET:` value. Leave its type as `string` — there is no `password` app-property type, and setting one makes the designer drop the property on save.**
6. **Chatbot / WebSocket client** — point your UI (or a WS test client) at `ws://<host>:<wsPort>/<usecase>`. No UI is bundled.
7. **Deploy-time secrets** *(if deploying to TIBCO Platform)* — provide `API_Key`, DB `Password`, and `Email_App_Password` as platform secrets at deploy time; don't ship them in the app.
8. **FDA Tech-Preview steps** *(the apps still build/run — these clear designer validation):*
   - **Sync every trigger** — FDA triggers are non-OpenAPI, so click **Sync** once on each (`tr_mcpserver`, `tr_agent`, `tr_wsserver`) to clear the red ✗ on input/tool-param mappings.
   - **Validate every connection** — FDA creates connections without testing them; open each (PostgreSQL, LLM, MCP, A2A) and click **Connect / Test**.
   - **Certificates, branches, activity loops, error handlers** — FDA can't create these; add them manually if your use case needs them.

### Pre-flight checklist

- [ ] DB created, `database.sql` loaded, row counts sane
- [ ] LLM `API_Key`, real `LLM_Base_URL`, and `LLM_Model` set
- [ ] All ports free; orchestrator MCP/A2A URLs match the MCP/A2A ports
- [ ] REST backends running (if any) / SMTP reachable (if email agent)
- [ ] Every trigger **Synced**; every connection **validated**; email password stored as `SECRET:`
- [ ] Start order: **MCP → A2A → Orchestrator**; each logs a clean start
- [ ] WebSocket client connects to `ws://<host>:<wsPort>/<usecase>` and gets a reply

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| MCP runtime panics with `missing input schema` | A tool handler is missing its input/output schema | The recipes attach both automatically — rebuild the tool via `fda`, don't hand-edit. |
| LLM call fails with `unsupported protocol scheme` / posts to `/New_value/...` | `LLM_Base_URL` was left blank | Set a real endpoint (e.g. `https://api.openai.com/v1`). |
| A2A **Connection dropdown is empty** / "Connection is required" | The connection UUID changed (e.g. the build was re-run) and activity `conn://` refs are dangling | Patch the affected `input.Connection` fields to the connection's **current** `id` — **do not** re-run the build driver on a designer-edited file (it regenerates UUIDs and wipes secrets). |
| SendMail: *"Type of field 'Password' (password) differs from bound app property (string)"* | `Email_App_Password` is a plaintext string, not a secret | Re-enter the value in App Properties so it becomes `SECRET:…`; **keep the type `string`.** |
| wsserver trigger nil-panics / "Configured connection is not a WebSocket Connection" | Handler schema / `wsconnection` typing | Handled by the recipes (headers schema + `wsconnection`/`content` = `any`); rebuild via `fda`. |

---

## Related

- **Sibling skill:** `agentic-ai-use-case` — same output, but builds by cloning an existing `.flogo` and swapping fields (best when you already have a near-identical reference app). This skill builds **from scratch with `fda`** for a clean, auditable app with no leftover UUIDs/secrets.
- **Skill internals:** [`SKILL.md`](SKILL.md) (workflow + gotchas), [`references/fda-build-recipes.md`](references/fda-build-recipes.md) (exact `fda` command sequences), [`references/manual-config-gap.md`](references/manual-config-gap.md) (full manual checklist).
- **Shared references:** [use-case spec template](../agentic-ai-use-case/references/use-case-spec-template.md), [data & docs conventions](../agentic-ai-use-case/references/data-and-docs.md), [PostgreSQL activity patterns](../agentic-ai-use-case/references/postgres-activity-patterns.md).
