# FDA Build Notes & Gap Analysis — Hospital Post-Discharge Use Case

How these three Flogo apps were built **entirely with the `fda` (Flogo Design Assistant) CLI**
(v0.9.3, extension `2.26.5-ENGR-001-3035`) from `hospital.spec.md`, and an honest comparison with the
hand-authored reference at `demos/Agentic_AI/Hospital_AI-Agent_Use_Case` — what the CLI did well, what
it could **not** do first-class, why, and how to fix each item.

## What was built (all via `fda`, no hand-edited JSON)

| App | Trigger | Contents | `fda cm` |
|-----|---------|----------|----------|
| `HospitalMCPServer.flogo` | `tr_mcpserver` (port 9092, `/hospital-bss`) | 7 read tools → `postgresql_query` → `actreturn` | 28 mappings, all 23 rules pass |
| `HospitalA2AServers.flogo` | 4× `tr_agent` (ports 9101–9104) | book_appointment (insert), pharmacy_order (insert), bed_turnover (update), send_confirmation_email (sendmail) | 25 mappings, all pass |
| `HospitalAIOrchestrator.flogo` | `tr_wsserver` (port 8082, `/ws/chat`) | `noop → agentactivity → wswritedata`; wired to the MCP connection + 4 A2A connections | 4 mappings, all pass |

All three parse as JSON, pass `fda check-mappings`, and every SQL statement the apps use runs against the
`hospital` DB. Commands used: `cp, cap, cc, ct, cth, cf, ca, sa, mm, wth, cm` — the same tasks documented
in the `rest-to-database-app` and `fda-mapping` skills.

## What `fda` did well
- **Full agentic stack is first-class.** `tr_mcpserver`, `tr_agent` (agenticai), `tr_wsserver`,
  `act_agenticai_agentactivity`, `con_llmprovider`, `con_mcpserverconfig`, `con_a2aserverconnection`,
  `act_postgresql_query/insert/update`, `act_general_sendmail`, `act_websocket_wswritedata` are all in
  the contribution registry (`lat`/`ltt`/`lct`).
- **MCP tools are easy.** `cth --mcpHandlerType Tool --mcpHandlerName --mcpHandlerDescription` sets the
  tool name/description; `wth <flow> MCP.<flow>` seeds the arguments-in/response-out wiring; the return
  is one `mm …Return.input.mappings.response.data '=coerce.toString($activity[Query].Output)'`.
- **Connections + app-properties** wire cleanly (`cc` + `sa connection …settings.* '=$property[...]'`),
  and `sa … -C connection <Name>` resolves a connection name to its `conn://` ref (used for the
  agentactivity's `llmProviderConnection`).
- **Validation** (`cm`) catches real problems (bad refs, missing imports, unqualified functions,
  reply/statusCode issues) — 23 rules, run per app.

## Gaps / what could NOT be done first-class (cause → fix)

1. **Secrets are stored in plaintext (functional gap).**
   `cap`/`sa` write literal values, so `AgenticAI.OpenAIConn.API_Key`, `PostgreSQL.PostgresConn.Password`,
   and `Email_App_Password` are plaintext — the reference apps use `SECRET:…` encrypted properties.
   *Cause:* `SECRET:` encryption is performed by Flogo Enterprise / the platform with an app-scoped key;
   the CLI has no encrypt task and cannot reproduce it. *Fix:* import each app into Flogo Enterprise (or
   the platform) and re-enter these three values so they are stored encrypted; or inject via a secret
   manager at deploy. Treat the plaintext values here as placeholders.

2. **A2A tool parameter schema (the LLM "tool signature") is not populated (functional gap).**
   The reference A2A handlers carry `handler.schemas.output.toolParams` = a JSON Schema of the tool's
   params. `cth <flow> <tr_agent>` + `wth … --input toolParams:object --input-schema-from-json '…'`
   attaches the schema to the **flow input** (derived) but leaves `handler.schemas` empty, so the tool
   may advertise an untyped `toolParams`. *Cause:* no `cth`/`wth` affordance for the agent handler's
   reply/param schemas. *Fix (CLI):* inject it explicitly, e.g.
   `fda sa handler '<agent>.<flow>.schemas.output.toolParams' x --jsonValue '{"type":"object","properties":{…}}' --force`.
   (Works, but it is raw-schema injection, not a first-class task.)

3. **PostgreSQL `?param` wiring has no first-class helper (rough edge, works).**
   `dmf` shows **0 mappable fields** for `postgresql_insert/query`, so the SQL parameters aren't
   discoverable. They can still be set: `mm '<flow>.<Act>.input.input.mapping.parameters.<name1>' '=$flow.toolParams.<x>'`
   plus the parameter descriptors via `sa '<flow>.<Act>.input.Fields' x --jsonValue '[{"FieldName":"<name1>","Type":"VARCHAR","Parameter":true,"Value":false},…]'`.
   *Gotcha applied:* placeholder names are suffixed (`?patient_id1`) so they don't collide with column
   names (see `references/postgres-activity-patterns.md`). *Fix/ask:* a dedicated "set SQL parameters"
   task in `fda` would remove the raw `input.input.mapping.parameters` + `Fields` handling.

4. **`wth` default wiring is missing/partial for some triggers.**
   - `tr_mcpserver`: full default wiring ✓.
   - `tr_agent`: **no** default wiring — must pass explicit `--input toolParams:object --output response:object`.
   - `tr_wsserver`: **partial** — only the last/first `--input` landed in `flow.metadata.input`
     (`wsconnection`), so `content` had to be added via `sa flow 'Orchestrator_Flow.metadata.input' … --jsonValue`
     and `sa handler 'WS.<flow>.action.input.content' '=$.content' --force`.
   *Fix/ask:* add default-wiring templates for `tr_agent`/`tr_wsserver`, and make `wth` honor multiple
   `--input` flags.

5. **MCP read tools have no typed output (`Fields` empty) (cosmetic/typing).**
   The reference query activities list every column in `input.Fields` (typed output schema); the fda
   build leaves `Fields` empty and just stringifies `Query.Output`. Functionally the tools return all
   rows, but the advertised output is untyped. *Fix:* populate `input.Fields` via `sa … --jsonValue`, or
   attach an output schema with `sms <flow>.Query.output --json-value-to-schema '…'`.

6. **DB connection binds via `settings.connection`, not `input.Connection` (difference, not a defect).**
   `ca … --connection PostgresConn` sets `activity.settings.connection = conn://…` and leaves
   `input.Connection` empty; the reference apps set `input.Connection = conn://…`. This is the CLI's own
   idiom and is expected to resolve at runtime; noted for parity.

7. **No `remove-activity` task; `create-flow` seeds a `StartActivity`.**
   You cannot delete an activity via the CLI, and every flow starts with a template `StartActivity`
   (noop). Build flows forward from `StartActivity`; to change a flow, recreate it (`rf` + `cf`).

8. **MSYS/Git-Bash path mangling of slash arguments (environment, not fda).**
   `/hospital-bss` became `C:/Program Files/Git/hospital-bss` until `MSYS_NO_PATHCONV=1` was exported.
   *Fix:* set `MSYS_NO_PATHCONV=1` (or `//path`) for any leading-slash argument (endpoint paths, ws path).

9. **Canvas layout / `fe_metadata` not set (cosmetic).**
   Nodes may open with a default layout in the VSCode designer. *Fix:* run `fda ff <flow>` (format-flow)
   per flow for tidy positioning.

## Architectural differences vs the reference (by design — not gaps)
- The reference is **4 apps**: an orchestrator with embedded A2A sub-agents, a REST API layer
  (`endevour-api`) the agents call over HTTP, `Hospital_MCP_Server`, and `eai-api`.
- This spec-driven build is the skill's canonical **3 apps**: MCP (reads) + A2A agents that **write
  directly to PostgreSQL** + orchestrator. There is intentionally **no REST layer** — the A2A agents own
  their DB writes. This is simpler and matches `hospital.spec.md`; it is a deliberate design choice.

## Bottom line
The `fda` CLI can build the **entire** MCP + A2A + orchestrator use case end-to-end, and every app
passes `fda cm`. The items that still need a human/Flogo-Enterprise step are: (1) encrypting the three
secrets, and — if you want full parity with the hand-authored app — (2) the A2A `toolParams` schema and
(5) MCP output `Fields`. All are addressable via the `sa --jsonValue` commands above; none blocked the
build.
