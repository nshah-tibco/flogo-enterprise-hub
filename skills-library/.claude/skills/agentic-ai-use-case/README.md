# Agentic AI Use Case Builder for Flogo — User Guide

> Scaffold a complete, runnable **Agentic AI demo** for any business vertical on TIBCO Flogo Enterprise. You describe the domain; the skill builds the database, an **MCP Server** (read-only lookup tools), an **A2A Agents** app (write/action agents), and a **WebSocket AI Orchestrator**, wires them together, and hands you a verified app set plus a checklist of the few things only you can configure.

This is a Claude Code **skill**. It supports **two build methods and asks which one you want** before it starts:

| | **FDA-CLI (recommended default)** | **Clone-and-adapt** |
|---|---|---|
| How apps are built | Built from scratch, command by command, with the **Flogo Design CLI (`flogodesign-cli` / `fda`)** — no manual JSON editing | **Clone an existing working `.flogo`** and swap in your domain fields |
| Best when | You want a clean, auditable build with no leftover UUIDs/secrets/`contrib` blobs, and no hand-assembled trigger/reply JSON | You have a **near-identical reference app** to copy, or the app needs **custom-extension activities the FDA recipes don't cover** (e.g. the OpenAI vector/RAG activities) |
| You must provide | Just the use case | Use case **+ a reference use case to clone** |

Both methods produce the **same three-app system**; only *how* the `.flogo` files are constructed differs. The skill recommends **FDA-CLI** and only clones when you choose it (or when a needed activity has no FDA recipe).

---

## How to invoke it

The skill is **user-invocable**. Two ways:

1. **Slash command** — type `/agentic-ai-use-case` in Claude Code, then describe your domain.
2. **Natural language** — just ask; the skill auto-activates on requests like *"build/create/scaffold an agentic AI use case / chatbot / MCP + A2A + orchestrator demo for &lt;domain&gt;."*

The **first thing the skill does is ask which build method you want** (FDA-CLI is recommended). You can state it up front — *"…build it with the FDA CLI"* or *"…clone the Telecom use case"* — and it will confirm and proceed.

---

## What it does

Given a description of a business domain (e.g. *"a hospital patient-services assistant"* or *"an airline passenger-services agent"*), the skill produces a **three-app Agentic AI system** backed by PostgreSQL:

```
Chatbot UI --WebSocket--> AI Orchestrator --MCP (HTTP streamable)--> MCP Server --\
                                 |                                                 +--> PostgreSQL
                                 \-----------A2A (HTTP)-----> A2A Agents ----------/   (+ SMTP for email)
```

| App | Role |
|-----|------|
| **MCP Server** | Read-only lookups. One tool per table/query; stateless and safe to retry. The LLM picks the right tool from its description. |
| **A2A Agents** | Action workflows — by default **write directly to PostgreSQL** (create/update) or **send email**. Each agent has its own trigger, port, and guardrails. *(A separate REST/backend service is built only if you explicitly ask for one.)* |
| **AI Orchestrator** | The "brain." A WebSocket chat endpoint driven by an AI Agent activity that decides intent and routes to MCP tools or hands off to A2A agents. |

### What you get (generated files)

A new folder (default `<FLOGO_APPS_DIR>/<UseCase>_Use_Case/`, or `samples/Agentic_AI/<UseCase>_Use_Case/` if you're contributing a demo to the hub catalogue — the skill confirms the target) containing:

| File | Purpose |
|------|---------|
| `database.sql` | PostgreSQL schema + demo data, engineered so each demo scenario works (one clean case + one exception case per action agent). |
| `reset_data.sql` | Truncate + reload to reset between demos; volatile dates are relative to today. |
| `<Prefix>MCPServer.flogo` | The MCP Server app — N read-only tools. |
| `<Prefix>Agents.flogo` | The A2A Agents app — M action agents. |
| `<Prefix>AIOrchestrator.flogo` | The AI Orchestrator app — WebSocket trigger + AI Agent routing. |
| `prompts.md` | Demo prompts grouped by scenario, to try against the running system. |
| `_rebuild/` *(FDA method only)* | The kept `fda` driver scripts (`build_mcp.py`, …) — replay the same build into an empty folder (e.g. after an FDA upgrade); secrets are read at run time, never stored. |
| `README.md` | Architecture, tool/agent tables, DB summary, demo scenarios, ports, troubleshooting, and the **"below things are not configured…"** manual checklist. |

---

## Prerequisites

1. **TIBCO Flogo Enterprise** (design-time + runtime) to import, configure, and run the `.flogo` apps.
2. **PostgreSQL** — a reachable instance you can create a database in and load SQL into.
3. **An LLM provider** — an OpenAI API key and a model your key can access (default `gpt-5-nano`). The base URL stays **empty** for OpenAI (the connector uses the OpenAI default); you need one only for Azure OpenAI, a gateway/proxy, or another provider. Default temperature `0`.
4. *(Optional)* **SMTP** credentials (e.g. a Gmail app password) if you want an email/notification agent.
5. **A configured `config.md`** — the skill reads the psql path, PostgreSQL host/port/user/password, the LLM key/model/base-URL, the SMTP creds, and (FDA method) the `fda`/`flogobuild` paths from `skills-library/.claude/skills/config.md` at build time and **never hardcodes secrets**. Copy `config.example.md` to `config.md` and fill it in. `config.md` is gitignored — never commit it.
6. **FDA method only:** **Flogo Design CLI (`flogodesign-cli` / `fda`)** and **`flogobuild`** installed (they ship with the TIBCO Flogo VS Code extension). The skill prints their path and version before running anything.
7. **Clone method only:** **a reference use case to clone** — one of the working demos under the reference folder (default `samples/Agentic_AI/`). If none is available on disk, the skill asks you where the reference apps live.
8. **Connector prerequisites** — in VS Code, **Flogo** sidebar → **Help And Feedback** → **Install Prerequisites for Flogo Connectors…** (PostgreSQL at minimum), then reload; required for design-time metadata fetching (schemas/tables and connection validation). See [connector-prereqs.md](references/connector-prereqs.md).

> Token/cost/time estimates and a lean prompt template for cheaper builds are in [build-cost-and-time.md](references/build-cost-and-time.md) — shown only if you ask.

---

## How to use it

### 1. Pick the build method (the skill asks)
FDA-CLI is the recommended default. Choose **clone** when a near-identical reference app exists, or when the app needs a custom-extension activity the FDA recipes don't cover (e.g. the OpenAI vector/RAG activities). You can state your choice in the request or answer the prompt.

### 2. Describe the domain — two ways to provide it

**Option A — Interactive (just describe it).** Give a one-line domain description and let the skill ask you the clarifying questions:
> *"Build an agentic AI demo for a hospital patient-services assistant."*

**Option B — Spec-driven (recommended for anything real).** Fill out the use-case spec template and hand it in; the skill treats it as the plan input:
> *"Here's my filled use-case spec — build the agentic AI app set: `my-usecase.spec.md`"*

The spec template lives at [`references/use-case-spec-template.md`](references/use-case-spec-template.md). It maps directly to the build: information lookups → MCP tools, actions/workflows → A2A agents, entities → tables, scenarios/seed data → `database.sql` + `prompts.md`, acceptance criteria → verification.

### What the skill does, in order
1. **Asks the build method** (FDA-CLI default vs clone).
2. **Reads your environment** from `config.md` (and, in FDA mode, prints tool paths + versions).
3. **Frames the use case** back to you (who chats, what problem is automated, the solution shape).
4. **Asks clarifying questions** (only the ones that change the build — see below).
5. **Presents a plan / README** for approval (tables, MCP tools, A2A agents, routing rules, ports, target folder, and what will land in the manual-config section).
6. **Builds** every app — via `fda` commands (FDA mode) or by cloning and adapting a reference app (clone mode).
7. **Verifies** (SQL runs, JSON parses, mapping checks, connection/port consistency, connector prerequisites detected) and hands you the manual checklist.

> ⚠️ The skill **does not build executables/binaries by default.** It stops at design-time verification and hands off. Ask explicitly if you want it to `flogobuild` the `.exe` apps.

---

## Inputs it needs from you

The skill asks only what changes the build:

| Input | Drives |
|-------|--------|
| **Build method** | FDA-CLI (default) vs clone. *(Clone also needs a reference app to copy.)* |
| **Persona / end user** | Whether it's a customer self-service assistant or an operator/back-office tool — this shapes the tables, tone, and available actions. |
| **Domain entities & scenarios** | The PostgreSQL tables and the MCP read tools. (It proposes a default set; you confirm or trim.) |
| **Action workflows / A2A agents** | Each state-changing action becomes an A2A agent. Default action is a **direct DB write** or **email**; a REST-backend agent is built only if you ask. |
| **Email/notification agent?** | Whether to include one SMTP agent. |
| **Locale / persona details** | Names, IDs, currency so demo data feels realistic. |
| **Ports & folder** | Distinct port per app/agent; default folder as above. |

The LLM config comes from `config.md` (fallback `gpt-5-nano`, empty base URL, temperature `0`) — you're only asked if you use Azure OpenAI, a gateway, or another provider. Everything else (secrets, connection UUIDs, tool/handler schemas, orchestrator routing wiring) is handled automatically.

---

## Reference use cases

Several Agentic AI use cases live under the reference folder (default `samples/Agentic_AI/`). In **clone mode**, pick the closest in shape to what you're building; in **FDA mode**, they're worth studying to match structure, README shape, and the direct-Postgres action pattern. The canonical references:

| Use case (`samples/Agentic_AI/…`) | Good starting point when you want… | Action pattern |
|---|---|---|
| `Telecom_Invoice_Chatbot_Use_Case` | A billing/invoice/account-lookup assistant with dispute/recharge write agents | Direct PostgreSQL |
| `Airline_Passenger_Services_Use_Case` | Booking/status lookups + rebooking/cancellation actions | Direct PostgreSQL |
| `Retail_Banking_Assistant_Use_Case` | Account/transaction lookups + dispute/card actions | Direct PostgreSQL |
| `Life_And_Pensions_Use_Case` | Pension member self-service + claim/update actions | Direct PostgreSQL |
| `Power_Distribution_Use_Case` | Outage lookups + report-outage actions | Direct PostgreSQL |
| `Hospital_AI-Agent_Use_Case` | Patient/appointment lookups + scheduling/update actions (includes email) | **REST backend — the documented outlier**, not the default |

> Tip (clone mode): match first on **whether it has an email agent** and the **number of write agents** — that's what saves the most rework. The five customer-facing use cases above are the canonical templates for the default **direct-Postgres** action pattern; only Hospital uses a REST backend (do not copy that pattern unless you specifically want a REST backend).

---

## Sample prompts

### Prompts to *invoke the skill* (build a new use case)

- *"Build an agentic AI demo for a **retail order-management** assistant: customers check order status and can request a return or reschedule delivery. Include an email confirmation agent."* (FDA method)
- *"Create an agentic app set for a **bank customer-service** agent — look up accounts and recent transactions (MCP), and let it open a dispute or block a card (A2A, DB writes)."*
- *"Scaffold an **insurance claims** chatbot by **cloning** the `Hospital_AI-Agent_Use_Case` (it has the email agent I want): look up policies/claims, file a new claim, and email the adjuster."*
- *"Build a **utilities/power outage** assistant based on `Power_Distribution_Use_Case` — look up outages by area and let users report a new outage. Put it in the apps folder."*

### Prompts to *try the running system* (also generated into `prompts.md`)

Once the three apps are imported, configured, and running, connect a chat/WebSocket client to `ws://<host>:<wsPort>/<usecase>`:

- *"What's the status of order 10432?"* → orchestrator calls an MCP lookup tool.
- *"Reschedule that delivery to Friday and email me the confirmation."* → orchestrator hands off to an A2A action agent (DB write + email).
- *"Show me all open claims for policy P-556 and file a new claim for a broken windshield."* → one MCP lookup + one A2A write in a single conversation.
- An **exception case** the seed data is engineered to trigger (e.g. *"cancel order 99999"* where the order doesn't exist) → so you can demo graceful failure.

---

## Manual configuration you must do at the end

The skill builds the entire app graph, but a few things depend on **your** environment, **your** secrets, or a **running backend** — they can't be baked into a portable, secret-free app. The generated `README.md` ends with a full **"below things are NOT configured…"** section; here's the summary. The complete, authoritative checklist (with exact reasons and error messages) is in [`references/manual-config-gap.md`](references/manual-config-gap.md).

1. **LLM credentials & endpoint** — set the real `API_Key` (the only required LLM value) and confirm `LLM_Model` (default `gpt-5-nano`) is available to your key. Leave `LLM_Base_URL` empty for OpenAI; set it only for Azure OpenAI, a gateway, or another provider. *(RAG apps: `OPENAI_API_ENDPOINT_URL` stays `https://api.openai.com/v1`, and run the ingestion app first.)*
2. **PostgreSQL** — create the DB, load `database.sql` (then `reset_data.sql` to reset between demos), and set the connection Host/Port/Database/User/Password to your instance.
3. **Ports** — MCP, each A2A, and the orchestrator ports must be free; the orchestrator's MCP/A2A `serverUrl`s must match those ports.
4. **REST backends** *(only if a REST agent was requested)* — the target API must be running and reachable. By default no REST backend exists (agents write directly to PostgreSQL).
5. **Email / SMTP** *(only if an email agent is included)* — set `Email_Username`, the recipient, and **re-enter `Email_App_Password` in the designer's App Properties so it's stored as a `SECRET:` value. Leave its type as `string` — there is no `password` app-property type, and setting one makes the designer drop the property on save.**
6. **Import & run in Flogo Enterprise** — open each connection and click **Connect / Test** to validate it; re-enter secrets if importing to a different environment. **FDA method:** also click **Sync** once on each trigger (`tr_mcpserver`, `tr_agent`, `tr_wsserver` are non-OpenAPI) to clear any red ✗ on input/tool-param mappings.
7. **Chatbot / WebSocket client** — point your UI (or a WS test client) at `ws://<host>:<wsPort>/<usecase>`. No UI is bundled. All clients share **one** conversation memory (the orchestrator's `conversationId` is empty → a constant) until it restarts — restart the orchestrator between demos; simultaneous users see each other's context.
8. **Deploy-time secrets** *(if deploying to TIBCO Platform)* — provide `API_Key`, DB `Password`, and `Email_App_Password` as platform secrets at deploy time; don't ship them in the app.

### Pre-flight checklist

- [ ] Connector prerequisites installed and VS Code reloaded
- [ ] DB created, `database.sql` loaded, row counts sane
- [ ] LLM `API_Key` set, `LLM_Model` available to the key, `LLM_Base_URL` empty for OpenAI
- [ ] All ports free; orchestrator MCP/A2A URLs match the MCP/A2A ports
- [ ] REST backends running (if any) / SMTP reachable (if email agent)
- [ ] Every connection **validated**; email password stored as `SECRET:`; (FDA) every trigger **Synced**
- [ ] Start order: **MCP → A2A → Orchestrator**; each logs a clean start
- [ ] WebSocket client connects to `ws://<host>:<wsPort>/<usecase>` and gets a reply; orchestrator restarted between demos (shared memory)

---

## Troubleshooting

**Shared (both methods)**

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| PostgreSQL insert mapping shows a red ✗ / "mappings vanished" | The `Fields[].Value` flag and the mapping/schema container disagree (a hybrid), or a `?param` name matches a column name | Make both containers agree with `Fields[].Value`; name params so they don't match columns (append a digit), set `Parameter:true`, map via `input.mapping.parameters` — see [postgres-activity-patterns.md](references/postgres-activity-patterns.md). |
| Designer: `syntax error at or near "$5p5"` (SQLSTATE 42601) on a PostgreSQL activity | A `?param` is followed by a character the connector won't accept (e.g. `?p5::date`), so it's never substituted — this also fails at runtime | Write `CAST(?p5 AS date)` (the placeholder must be followed by a space or `; ) , < > + - * % /`); `references/validate_flogo_apps.py` flags it. |
| LLM call fails / posts to a bad URL | Base URL holds a placeholder or wrong endpoint | For OpenAI set it to empty `""` (connector default); use a real URL only for Azure/gateway/other. |
| SendMail: *"Type of field 'Password' (password) differs from bound app property (string)"* | `Email_App_Password` is a plaintext string, not a secret | Re-enter the value in App Properties so it becomes `SECRET:…`; **keep the type `string`.** |
| A connection dropdown is empty / "Connection is required" | A `conn://` UUID doesn't match a connections-map key | Ensure every `conn://<uuid>` resolves to a key in that app's `connections` map. |
| Designer can't list schemas/tables or validate a connection | Connector prerequisite (e.g. PostgreSQL) not installed | Install via the Flogo sidebar → Help And Feedback → Install Prerequisites for Flogo Connectors…, then reload VS Code. |

**FDA method**

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| MCP runtime panics with `missing input schema` | A tool handler is missing its input/output schema | The recipes attach both automatically — rebuild the tool via `fda`, don't hand-edit. |
| LLM call fails with `unsupported protocol scheme` / posts to `/New_value/...` | `LLM_Base_URL` holds the literal `New_value` (what `fda cap … ""` writes) | Make it truly empty for OpenAI (or a real URL for Azure/gateway/other) — see the recipe's base-URL fix. |
| A2A PostgreSQL activity is bound to **OpenAIConn** (or another wrong connection) | `input.Connection` was re-set with `fda sa activity …` after `ca -C` — on fda 0.9.3 that rebinds it to the **first** connection in the file | Bind only with `fda ca … -C PostgresConn` (the recipes do). To repair, patch the literal `conn://<PostgresConn id>` into the field, or re-select in the designer. |
| A2A **Connection dropdown is empty** after re-running the build | The connection UUID changed and activity `conn://` refs are dangling | Patch the affected `input.Connection` fields to the connection's **current** `id`; **do not** re-run the build driver on a designer-edited file (it regenerates UUIDs and wipes secrets). |
| wsserver trigger nil-panics / "Configured connection is not a WebSocket Connection" | Handler schema / `wsconnection` typing | Handled by the recipes (headers schema + `wsconnection`/`content` = `any`); rebuild via `fda`. |

**Clone method**

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Import fails / app won't load after cloning | A `contrib` blob or `SECRET:` value was regenerated by hand | Carry `contrib` + `SECRET:` values **verbatim** from the reference app; only change the DB name and domain fields. |
| Email/API/DB fails only after moving environments | Cloned `SECRET:` values don't decrypt under the new app-key | Re-enter those secrets in App Properties so they re-encrypt for your environment (keep types `string`). |
| A cloned base URL posts to a wrong endpoint | The base URL was left as the literal `New_value` or a stale value | Write a real `""` for OpenAI (a real URL only for Azure/gateway/other). |

---

## Related

- **Skill internals:** [`SKILL.md`](SKILL.md) (workflow + gotchas), [`references/flogo-app-templates.md`](references/flogo-app-templates.md) (exact JSON structure of all 3 apps), [`references/postgres-activity-patterns.md`](references/postgres-activity-patterns.md) (the #1 source of errors), [`references/data-and-docs.md`](references/data-and-docs.md), [`references/use-case-spec-template.md`](references/use-case-spec-template.md).
- **FDA method references:** [`references/fda-build-recipes.md`](references/fda-build-recipes.md) (exact `fda` command sequences), [`references/fda-limitations.md`](references/fda-limitations.md) (Tech-Preview limitations → manual steps), [`references/manual-config-gap.md`](references/manual-config-gap.md) (full manual checklist).
- **Connector prerequisites:** [`references/connector-prereqs.md`](references/connector-prereqs.md).
- **Cost & tokens:** [`references/build-cost-and-time.md`](references/build-cost-and-time.md) — token/cost/time estimates and a lean prompt template (shown on request).
