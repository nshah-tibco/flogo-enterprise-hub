# FDA build recipes — construct all 3 agentic apps with `fda` only

Exact `flogodesign-cli` (`fda`) command sequences to build the MCP Server, A2A Servers, and AI Orchestrator **from scratch, without hand-editing any `.flogo` JSON**. Verified end-to-end (build + live run: WebSocket chat → LLM → MCP tool → real PostgreSQL → reply written back over WS).

## Conventions & placeholders

Replace every `<…>` with the user's domain values. **Nothing here is domain-specific** — the examples use placeholders on purpose.

| Placeholder | Meaning | Example value (yours will differ) |
|---|---|---|
| `<UseCase>` / `<Prefix>` | Use-case name / app-name prefix | (from Phase 2) |
| `<db>`, `<pk>`, `<table>` | DB name / table primary key / table | (from `database.sql`) |
| `<Tool>`, `<toolDesc>`, `<SQL>` | MCP tool name / description / query | — |
| `<Agent>`, `<agentDesc>`, `<sysPrompt>` | A2A agent id / description / system prompt | — |
| `<*_PORT>`, `<*_URL>` | ports / URLs (always app properties) | — |
| `$FDA`, `$FLB` | resolved `fda` / `flogobuild` paths | from `config.md` (Phase 0) |

**Ground rules**
- Read all hosts, ports, creds, API key, model, base URL, SMTP creds, and CLI paths from `config.md` at build time (Phase 0). Never hardcode.
- Print `$FDA version` and `$FLB version` before running commands.
- On Windows/Git-Bash, prefix each `fda`/`flogobuild` call with `MSYS_NO_PATHCONV=1`, **or** drive `fda.exe` from a Python `subprocess` (which sidesteps MSYS path-mangling entirely — recommended for the A2A/orchestrator loops).
- Every `fda` call takes `-f <app>.flogo`. Detect failure by scanning combined stdout/stderr for `(ERROR)`.
- Secrets: load into variables from `config.md`; pass as `cap` values; never echo them. Prefer `SECRET:`-encoded values where the field supports it.

A tiny Python driver keeps long builds repeatable:

```python
import subprocess, os, sys
FDA = os.environ["FDA"]                 # resolved from config.md
FILE = "<Prefix>MCPServer.flogo"
def fda(*args, allow_fail=False):
    r = subprocess.run([FDA, *map(str, args), "-f", FILE],
                       capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    if "(ERROR)" in out and not allow_fail:
        print("FAILED:", " ".join(map(str, args))); print(out[-1000:]); sys.exit(1)
    return out

def conn_uuid(name):                 # gotcha 7: resolve a connection's conn:// ref
    import json                       #   (PostgreSQL activities need the LITERAL ref)
    conns = json.load(open(FILE))["connections"]
    items = list(conns.values()) if isinstance(conns, dict) else conns
    return "conn://" + next(c["id"] for c in items if c["name"] == name)
```

---

## § MCP Server (`<Prefix>MCPServer.flogo`)

Read-only tools, one per lookup. Trigger `tr_mcpserver`; each tool flow = `act_postgresql_query → act_default_actreturn`.

### 1. Project, properties, PostgreSQL connection

```bash
$FDA cp <Prefix>MCPServer "<UseCase> MCP Server" -f "$FILE"

# App properties (values from config.md; Password ideally SECRET:)
$FDA cap PostgreSQL.PostgresConn.Host          string <host>   -f "$FILE"
$FDA cap PostgreSQL.PostgresConn.Port          number <port>   -f "$FILE"   # DB connection Port field is NUMERIC — gotcha 8
$FDA cap PostgreSQL.PostgresConn.Database_Name string <db>     -f "$FILE"
$FDA cap PostgreSQL.PostgresConn.User          string <user>   -f "$FILE"
$FDA cap PostgreSQL.PostgresConn.Password      string <pwd>    -f "$FILE"
$FDA cap MCP_SERVER_PORT                        string <mcpPort> -f "$FILE"  # tr_mcpserver "HTTP Server Port" field is STRING — gotcha 8

# PostgreSQL connection, settings bound to the properties above
$FDA cc PostgresConn con_postgresql -f "$FILE"
# gotcha 7: read the connection's conn:// ref back NOW (needed by every query/insert below):
#   PG_REF = conn_uuid("PostgresConn")   (see driver above)
$FDA sa connection PostgresConn.settings.databaseType PostgreSQL -f "$FILE"
$FDA sa connection PostgresConn.settings.host         PostgreSQL.PostgresConn.Host          -C app-property -f "$FILE"
$FDA sa connection PostgresConn.settings.port         PostgreSQL.PostgresConn.Port          -C app-property -f "$FILE"
$FDA sa connection PostgresConn.settings.databaseName PostgreSQL.PostgresConn.Database_Name -C app-property -f "$FILE"
$FDA sa connection PostgresConn.settings.user         PostgreSQL.PostgresConn.User          -C app-property -f "$FILE"
$FDA sa connection PostgresConn.settings.password     PostgreSQL.PostgresConn.Password      -C app-property -f "$FILE"
```

### 2. Trigger

```bash
$FDA ct <Prefix>MCPServer tr_mcpserver "<UseCase> MCP server" -f "$FILE"
$FDA sa trigger <Prefix>MCPServer.settings.serverType         HTTP  -f "$FILE"
$FDA sa trigger <Prefix>MCPServer.settings.serverPort         MCP_SERVER_PORT -C app-property -f "$FILE"
$FDA sa trigger <Prefix>MCPServer.settings.serverEndpointPath /<usecase>mcpserver -f "$FILE"
$FDA sa trigger <Prefix>MCPServer.settings.serverName         <UseCase> -f "$FILE"
$FDA sa trigger <Prefix>MCPServer.settings.serverVersion      1.0.0 -f "$FILE"
```

### 3. Shared tool schemas (create ONCE, reused by every tool) — **gotcha 1**

```bash
$FDA cs EmptyArgs   '{"type":"object","properties":{}}' -f "$FILE"
$FDA cs ToolResponse '{"type":"object","properties":{"data":{"type":"string"},"error":{"type":"string"}}}' -f "$FILE"
```

### 4. Per tool (repeat for each lookup)

`<flow>` = a unique flow name (e.g. `get<Table>`). `<Tool>` = the LLM-visible tool name.

```bash
$FDA cf <flow> "<toolDesc>" -f "$FILE"
$FDA ca <flow> PostgreSQLQuery act_postgresql_query "PostgreSQL Query" -C PostgresConn -f "$FILE"
$FDA ca <flow> Return          act_default_actreturn "Simple Return"    -f "$FILE"   # ca auto-links in creation order

# gotcha 7: input.Connection must be the LITERAL conn:// ref. Name-resolution
#   (`... input.Connection PostgresConn -C connection`) silently writes "" → the designer
#   dropdown is EMPTY and runtime fails with "Connection is required". Use PG_REF (read back
#   after `cc PostgresConn`); this is the SAME conn:// pattern as the orchestrator's arrays.
$FDA sa activity <flow>.PostgreSQLQuery.input.Connection "$PG_REF" -f "$FILE"
$FDA sa activity <flow>.PostgreSQLQuery.input.Query  "SELECT * FROM public.<table> ORDER BY <pk> ASC;" -f "$FILE"
$FDA sa activity <flow>.PostgreSQLQuery.input.Schema public -f "$FILE"

# Handler = one MCP tool
$FDA cth <flow> <Prefix>MCPServer "<toolDesc>" \
    --mcpHandlerType Tool --mcpHandlerName <Tool> --mcpHandlerDescription "<toolDesc>" -f "$FILE"
$FDA wth <flow> <Prefix>MCPServer.<flow> --force -f "$FILE"

# gotcha 1: attach input + output schemas or the MCP runtime panics
$FDA sa handler <Prefix>MCPServer.<flow>.schemas.output.arguments EmptyArgs   -C schema --force -f "$FILE"
$FDA sa handler <Prefix>MCPServer.<flow>.schemas.reply.response   ToolResponse -C schema --force -f "$FILE"

# gotcha 2: actreturn mapping uses the .mapping node
$FDA mm <flow>.Return.input.mappings.response.mapping.data '=coerce.toString($activity[PostgreSQLQuery].Output)' -f "$FILE"
```

> **Parameterized reads:** for a `WHERE <col> = ?p` query, set `input.Query` with a `?`-placeholder whose name does NOT equal a column name, then map values under `input.mapping.parameters` (e.g. `$FDA mm <flow>.PostgreSQLQuery.input.mapping.parameters.<p> '=$flow.<field>'`). See the sibling `postgres-activity-patterns.md`. Simple demos use `SELECT *` and let the LLM filter.

Rich `handlerDescription`s matter — the orchestrator LLM chooses tools from them.

---

## § A2A Servers (`<Prefix>A2AServers.flogo`)

One `tr_agent` trigger per action agent. **By default each agent's flow writes DIRECTLY to PostgreSQL** (`act_postgresql_query` to validate → `act_postgresql_insert` for the INSERT/UPDATE) **or sends email** (`act_general_sendmail`), and returns a result string. This is the pattern used by all the customer-facing reference use cases (Airline, Life & Pensions, Power Distribution, Retail Banking, Telecom). **Do NOT use `act_general_rest` / create a separate REST backend app unless the user explicitly asked for one** — the REST steps below are clearly marked *opt-in*. Because the loop is repetitive, drive it from Python `subprocess` (see driver above; point `FILE` at the A2A file).

### 1. Project, properties, LLM connection

```bash
$FDA cp <Prefix>A2AServers "<UseCase> A2A Servers"
# LLM properties (from config.md)
$FDA cap AgenticAI.OpenAIConn.LLM_Provider string <provider>            # e.g. OpenAI
$FDA cap AgenticAI.OpenAIConn.API_Key      string <apiKey>              # SECRET where supported
$FDA cap AgenticAI.OpenAIConn.LLM_Base_URL string <baseUrl>            # explicit endpoint — gotcha 4c
$FDA cap LLM_Model                         string <model>
# One PORT + URL property per agent, plus SMTP/recipient properties:
$FDA cap <Agent>_PORT string <port>          # tr_agent "A2A Server Port" field is STRING — keep string (gotcha 8)
$FDA cap <Agent>_URL  string http://localhost:<port>
#   Email agent: $FDA cap Email_Username string <user> ; Email_App_Password string <pwd> ; To_Email string <addr>
#   Opt-in REST agents ONLY (if the user explicitly asked): $FDA cap <Backend>_URL string <url-with-{pathParams}>

$FDA cc OpenAIConn con_llmprovider
$FDA sa connection OpenAIConn.settings.llmProvider    AgenticAI.OpenAIConn.LLM_Provider -C app-property
$FDA sa connection OpenAIConn.settings.apiKey         AgenticAI.OpenAIConn.API_Key      -C app-property
$FDA sa connection OpenAIConn.settings.llmProviderUrl AgenticAI.OpenAIConn.LLM_Base_URL -C app-property
# DEFAULT: action agents write to the DB, so create a PostgresConn here (same as MCP § 1),
#   then read its ref back: PG_REF = conn_uuid("PostgresConn")  — used by every query/insert (gotcha 7).
```

### 2. Per agent (repeat)

```bash
$FDA ct <Agent> tr_agent "<agentDesc>"
$FDA sa trigger <Agent>.settings.llmProviderConnection OpenAIConn -C connection
$FDA sa trigger <Agent>.settings.agentName           <Agent>
$FDA sa trigger <Agent>.settings.agentDescription    "<agentDesc>"
$FDA sa trigger <Agent>.settings.agentType           "A2A Server"
$FDA sa trigger <Agent>.settings.agentPort           <Agent>_PORT -C app-property
$FDA sa trigger <Agent>.settings.agentUrl            <Agent>_URL  -C app-property
$FDA sa trigger <Agent>.settings.model               LLM_Model    -C app-property
$FDA sa trigger <Agent>.settings.temperature         0.7  --type number
$FDA sa trigger <Agent>.settings.enableGuardrails    true --type boolean
$FDA sa trigger <Agent>.settings.redactSensitiveData true --type boolean
$FDA sa trigger <Agent>.settings.conversationStoreType Memory
$FDA sa trigger <Agent>.settings.memoryMaxSize       100  --type number
$FDA sa trigger <Agent>.settings.systemPrompt        "<sysPrompt>"

# --- flow: noop is created by cf; add the action activities in order (ca auto-links) ---
$FDA cf <Agent>_flow "<agentDesc>"
$FDA ca <Agent>_flow LogMessage act_general_log "Log" 
$FDA mm <Agent>_flow.LogMessage.input.message '=string.concat("Agent Invocation started:",$flowctx["FlowName"])'

# choose the action for this agent — (a) DB write and (b) email are the DEFAULTS:
#
#   (a) DEFAULT — DB write (direct to PostgreSQL). Optionally validate with a SELECT first,
#       then INSERT/UPDATE. This is the canonical pattern for all customer-facing use cases.
$FDA ca <Agent>_flow ValidateQuery act_postgresql_query  "PostgreSQL Query"  -C PostgresConn   # optional pre-check
$FDA sa activity <Agent>_flow.ValidateQuery.input.Connection "$PG_REF"   # gotcha 7: literal conn:// (see § MCP step 4)
$FDA sa activity <Agent>_flow.ValidateQuery.input.Query  "SELECT ... FROM public.<table> WHERE <col> = ?id;"
$FDA sa activity <Agent>_flow.ValidateQuery.input.Schema public
$FDA mm <Agent>_flow.ValidateQuery.input.mapping.parameters.id '=$flow.toolParams.<field>'
$FDA ca <Agent>_flow WriteRow act_postgresql_insert  "PostgreSQL Insert"  -C PostgresConn
$FDA sa activity <Agent>_flow.WriteRow.input.Connection "$PG_REF"   # gotcha 7: literal conn:// (see § MCP step 4)
$FDA sa activity <Agent>_flow.WriteRow.input.Query  "INSERT INTO public.<table> (<cols>) VALUES (?p1, ?p2);"
#       (act_postgresql_insert runs UPDATE too — e.g. "UPDATE public.cards SET status='BLOCKED' WHERE card_id=?p1;")
$FDA sa activity <Agent>_flow.WriteRow.input.Schema public
$FDA mm <Agent>_flow.WriteRow.input.mapping.parameters.p1 '=$flow.toolParams.<field1>'
$FDA mm <Agent>_flow.WriteRow.input.mapping.parameters.p2 '=$flow.toolParams.<field2>'
#
#   (b) DEFAULT — Email (the dedicated send_confirmation_email agent):
$FDA ca <Agent>_flow SendMail act_general_sendmail "Send Mail"
$FDA sa activity <Agent>_flow.SendMail.input.Server smtp.gmail.com
$FDA sa activity <Agent>_flow.SendMail.input.Port 465
#       Connection Security SSL; Username/Password/recipients from app properties; map subject/body from toolParams.
#
#   (c) OPT-IN — REST call to a backend. *** Use ONLY if the user explicitly asked for a REST
#       backend app. *** Default agents do (a)/(b) and never touch this.
# $FDA ca <Agent>_flow InvokeRESTService act_general_rest "Invoke REST"
# $FDA sa activity <Agent>_flow.InvokeRESTService.input.Method GET
# $FDA sa activity <Agent>_flow.InvokeRESTService.input.Uri <Backend>_URL -C app-property
# #   dynamic path/body: $FDA mm <Agent>_flow.InvokeRESTService.input.pathParams.mapping.<p> '=$flow.toolParams.<p>'
# #   ⚠️ REQUIRED — declare the response BODY output schema, or downstream mappings can't
# #     resolve `$activity[InvokeRESTService].responseBody`. The `#rest` activity ALWAYS
# #     exposes statusCode/responseTimeInMillis/headers, but `responseBody` only exists when
# #     you set schemas.output.responseBody. `ca`/`ct` do NOT create it → the Return mapper
# #     shows a red ✗ ("Map Outputs" invalid). Write the expected response shape (a
# #     draft-04 object schema of the fields the backend returns) to a file, then:
# $FDA sa activity <Agent>_flow.InvokeRESTService.schemas.output.responseBody --jsonFile <resp_schema.json> --force
# #     where <resp_schema.json> = {"type":"json","value":"<stringified draft-04 schema>","fe_metadata":"<sample JSON>"}
# #     (If the mapping only does coerce.toString(responseBody), the exact fields don't affect
# #      runtime — but the field must EXIST in schemas.output or the designer rejects the map.)

$FDA ca <Agent>_flow Return act_default_actreturn "Simple Return"
# DEFAULT return (DB write): map a confirmation string / the write output.
$FDA mm <Agent>_flow.Return.input.mappings.response.mapping.data '=coerce.toString($activity[WriteRow].Output)'
#   (email agent: map a "sent" confirmation; opt-in REST agent: coerce.toString($activity[InvokeRESTService].responseBody))

# --- handler = the agent's tool card ---
$FDA cth <Agent>_flow <Agent> "<agentToolDesc>"
$FDA sa handler <Agent>.<Agent>_flow.settings.agentToolName        <Agent>
$FDA sa handler <Agent>.<Agent>_flow.settings.agentToolDescription "<agentToolDesc>"
$FDA wth <Agent>_flow <Agent>.<Agent>_flow --force --input toolParams:object --output response:object   # tr_agent has no default wiring
# toolParams (input) + response (reply) schemas — describe the fields the orchestrator must pass:
$FDA cs <Agent>_ToolParams '{"type":"object","properties":{ "<field>":{"type":"string"} },"required":[]}'
$FDA sa handler <Agent>.<Agent>_flow.schemas.output.toolParams <Agent>_ToolParams -C schema --force
$FDA cs <Agent>_Resp '{"type":"object","properties":{"response":{"type":"string"}}}'
$FDA sa handler <Agent>.<Agent>_flow.schemas.reply.response   <Agent>_Resp -C schema --force

# gotcha 5 — the FLOW input needs the SAME toolParams schema as the handler, or the
#   designer's mapper can't resolve $flow.toolParams.<field>: the flow's Input tab shows
#   a red ✗ on every toolParams mapping (subject/body/email/…) and the app fails
#   validation. `wth --input toolParams:object` writes only a BARE object to
#   flow.metadata.input (no sub-schema). Reuse the tool schema on the flow input — write
#   [{"name":"toolParams","type":"object","schema":{"type":"json","value":"<same JSON string as <Agent>_ToolParams>"}}]
#   to a file, then:
$FDA sa flow <Agent>_flow.metadata.input --jsonFile <toolparams_flowinput.json>
#   ⚠️ CAVEAT — `metadata.input` alone is NOT durable in the designer. The designer treats
#   `metadata.fe_metadata.input` (a stringified draft-04 JSON schema — its cached "view") as
#   the SOURCE OF TRUTH and REGENERATES `metadata.input` FROM IT on the next Save. So a flow
#   whose fe_metadata is still empty gets your CLI-written schema WIPED back to a bare object
#   the first time the user saves the app. (Verified: two A2A flows we set via `sa flow` were
#   bare again after the user opened+saved the app in the designer.)
#   Two ways to make it stick — do ONE:
#   (a) SANCTIONED / always-correct: the user clicks "Sync" once on each trigger. Sync reads
#       the handler tool schema and writes BOTH metadata.input AND fe_metadata correctly.
#       This is the documented "Manual Sync for Non-OpenAPI Triggers" limitation
#       (tr_mcpserver/tr_agent/tr_wsserver are all non-OpenAPI) — keep it as the fallback
#       manual-config-gap step regardless.
#   (b) NO-SYNC bake (optional, for a clean first-open): also write fe_metadata to EXACTLY the
#       shape the designer produces after a Sync, so metadata.input survives regeneration and
#       the fields render with no Sync. Mirror this format per flow (fields = your
#       <Agent>_ToolParams properties):
#         metadata.input[toolParams].schema = {"type":"json",
#           "value":"{\"<f1>\":{\"type\":\"string\"},\"<f2>\":{\"type\":\"string\"}}"}
#         metadata.fe_metadata.input (stringified) =
#           {"type":"object","title":"<Agent>_trigger","properties":{"toolParams":
#             {"$schema":"http://json-schema.org/draft-04/schema#","type":"object",
#              "properties":{"<f1>":{"type":"string"},"<f2>":{"type":"string"}}}}}
#       (Do the same for output: metadata.output[response].schema value
#         {\"data\":{\"type\":\"string\"},\"error\":{\"type\":\"string\"}} and the matching
#        fe_metadata.output with title "Inputs".) Copy the exact format from a flow the user
#       has already Synced — it's the designer's own output, so it's the safest template.
#   (Flow input/output config is itself a documented FDA limitation — see fda-limitations.md.)

# gotcha 6 — email agents: the #sendmail `Password` field is type `password`. FDA `cap`
#   can only make a `string` property (no password type: `cap … password` errors
#   "Unknown Flogo Property Type") AND writes the value as PLAINTEXT (FDA can't
#   SECRET-encrypt). A `password` field only binds cleanly to a SECRET-valued property,
#   so a plaintext string one makes the designer flag:
#     Type of field "Password" (password) differs from bound app property (string).
#   *** DO NOT set the property's type to `password` to "fix" this. *** That type is
#   invalid; the designer DROPS the property on the next save, turning the warning into a
#   HARD error:  "Password" is bound to app property "..." which does not exist.
#   Correct fix (manual-config-gap): keep type=string; the user re-enters the value once in
#   the designer's App Properties panel so it is stored as SECRET:… (clears the ✗). It
#   builds and runs as a plaintext string either way.
```

---

## § AI Orchestrator (`<Prefix>AIOrchestrator.flogo`)

WebSocket trigger `tr_wsserver` → `act_agenticai_agentactivity` → `act_websocket_wswritedata`. This is where the three wsserver gotchas live.

### 1. Project, properties, connections (LLM + MCP + one A2A per agent)

```bash
$FDA cp <Prefix>AIOrchestrator "<UseCase> AI Orchestrator"
$FDA cap AgenticAI.OpenAIConn.LLM_Provider string <provider>
$FDA cap AgenticAI.OpenAIConn.API_Key      string <apiKey>
$FDA cap AgenticAI.OpenAIConn.LLM_Base_URL string <baseUrl>   # gotcha 4c: MUST be a real endpoint, never empty
$FDA cap LLM_Model                         string <model>
$FDA cap WebSocket_PORT                     number <wsPort>   # tr_wsserver "port" field is NUMERIC (unlike mcp/agent ports) — gotcha 8

$FDA cc OpenAIConn con_llmprovider
$FDA sa connection OpenAIConn.settings.llmProvider    AgenticAI.OpenAIConn.LLM_Provider -C app-property
$FDA sa connection OpenAIConn.settings.apiKey         AgenticAI.OpenAIConn.API_Key      -C app-property
$FDA sa connection OpenAIConn.settings.llmProviderUrl AgenticAI.OpenAIConn.LLM_Base_URL -C app-property

$FDA cc <Prefix>MCPServer con_mcpserverconfig
$FDA sa connection <Prefix>MCPServer.settings.serverType        http
$FDA sa connection <Prefix>MCPServer.settings.serverUrl         http://localhost:<mcpPort>/<usecase>mcpserver
$FDA sa connection <Prefix>MCPServer.settings.httpTransportType streamable

# one a2aserverconnection per A2A agent:
$FDA cc <Agent>A2AServer con_a2aserverconnection
$FDA sa connection <Agent>A2AServer.settings.serverUrl http://localhost:<agentPort>
```

### 2. Read `conn://` UUIDs back, then set the arrays — **gotcha 3**

```python
import json
d = json.load(open(FILE))
conns = d["connections"]
items = list(conns.values()) if isinstance(conns, dict) else conns
cid = {c["name"]: c["id"] for c in items}
MCP_REF  = f"conn://{cid['<Prefix>MCPServer']}"
A2A_REFS = [f"conn://{cid[name]}" for name in ["<Agent1>A2AServer", "<Agent2>A2AServer", ...]]
```

### 3. Trigger, flow, agent activity

```bash
$FDA ct WebsocketServer tr_wsserver "WebSocket server"
$FDA sa trigger WebsocketServer.settings.port WebSocket_PORT -C app-property

$FDA cf Orchestrator_Flow "<UseCase> orchestrator flow"
$FDA ca Orchestrator_Flow AIAgent            act_agenticai_agentactivity "AI Agent"
$FDA ca Orchestrator_Flow WebsocketWriteData act_websocket_wswritedata   "Write to websocket"

# AIAgent settings
$FDA sa activity Orchestrator_Flow.AIAgent.settings.llmProviderConnection OpenAIConn -C connection
$FDA sa activity Orchestrator_Flow.AIAgent.settings.model                LLM_Model  -C app-property
$FDA sa activity Orchestrator_Flow.AIAgent.settings.temperature          0.7  --type number
$FDA sa activity Orchestrator_Flow.AIAgent.settings.enableGuardrails     true --type boolean
$FDA sa activity Orchestrator_Flow.AIAgent.settings.redactSensitiveData  true --type boolean
$FDA sa activity Orchestrator_Flow.AIAgent.settings.responseType         Text
$FDA sa activity Orchestrator_Flow.AIAgent.settings.conversationStoreType Memory
$FDA sa activity Orchestrator_Flow.AIAgent.settings.memoryMaxSize        100 --type number
$FDA sa activity Orchestrator_Flow.AIAgent.settings.systemPrompt         "<routing sysPrompt>"

# gotcha 3: the conn:// arrays (read back in step 2)
$FDA sa activity Orchestrator_Flow.AIAgent.settings.mcpServers   --jsonValue '["'"$MCP_REF"'"]'
$FDA sa activity Orchestrator_Flow.AIAgent.settings.remoteAgents --jsonValue '<json array of A2A_REFS>'

# inputs
$FDA mm Orchestrator_Flow.AIAgent.input.userPrompt '=coerce.toString($flow.content)'
$FDA mm Orchestrator_Flow.WebsocketWriteData.input.message      '=$activity[AIAgent].response'
$FDA mm Orchestrator_Flow.WebsocketWriteData.input.wsconnection '=$flow.wsconnection'
```

### 4. Handler + wiring + the two remaining wsserver fixes — **gotcha 4a/4b**

```bash
$FDA cth Orchestrator_Flow WebsocketServer "<UseCase> orchestrator handler"
$FDA sa handler WebsocketServer.Orchestrator_Flow.settings.path   /<usecase>
$FDA sa handler WebsocketServer.Orchestrator_Flow.settings.mode   Data
$FDA sa handler WebsocketServer.Orchestrator_Flow.settings.format String
# wth: params survives; content/wsconnection come back as object and are fixed below
$FDA wth Orchestrator_Flow WebsocketServer.Orchestrator_Flow --force \
    --input content:any,wsconnection:any,pathParams:params,queryParams:params,headers:object --inputs-only

# gotcha 4a: wsserver handler needs schemas.output present or it nil-panics on first request
$FDA cs OrcWsHeaders '{"type":"object","properties":{"Accept":{"type":"string","visible":false},"Accept-Charset":{"type":"string","visible":false},"Accept-Encoding":{"type":"string","visible":false},"Content-Type":{"type":"string","visible":false},"Content-Length":{"type":"string","visible":false},"Connection":{"type":"string","visible":false},"Cookie":{"type":"string","visible":false},"Pragma":{"type":"string","visible":false},"Sec-Websocket-Key":{"type":"string","visible":false},"Sec-Websocket-Version":{"type":"string","visible":false},"Upgrade":{"type":"string","visible":false}},"required":[]}'
$FDA sa handler WebsocketServer.Orchestrator_Flow.schemas.output.headers OrcWsHeaders -C schema --force

# gotcha 4b: force wsconnection + content back to `any` (wth downgraded them to object).
#   write this array to a file, then apply it:
#   [{"name":"pathParams","type":"params"},{"name":"queryParams","type":"params"},
#    {"name":"headers","type":"object"},{"name":"content","type":"any"},{"name":"wsconnection","type":"any"}]
$FDA sa flow Orchestrator_Flow.metadata.input --jsonFile <meta_input.json>
```

---

## Build + verify

```bash
$FLB version                                   # print path+version first (Phase 0)
$FLB build-exe -f "<app>.flogo" -c <context>   # per app; <context> from config.md/flogobuild skill
# Note: build-exe exits 1 with a cosmetic path error ("…\engine\C:\…\X.exe: syntax is incorrect")
#       but the .exe IS produced next to the .flogo — verify by `ls -la --time-style=full-iso <app>.exe`.
$FDA cm -f "<app>.flogo"                        # check-mappings: refs, imports, scopes
```

### Live run (order matters: MCP → A2A → Orchestrator)

```bash
./<Prefix>MCPServer.exe      &   # listens on <mcpPort>
./<Prefix>A2AServers.exe     &   # listens on each <agentPort>; discovers MCP tools
./<Prefix>AIOrchestrator.exe &   # WS on <wsPort>; connects to MCP + all A2A on startup
```
On startup the orchestrator log should show it discovered the MCP tool list and connected to every A2A agent card. Then connect a WebSocket client to `ws://localhost:<wsPort>/<usecase>` and send a natural-language prompt; a healthy run logs `Executing tool[toolName:<Tool>]`, `Agent execution completed … used_tools:[<Tool>]`, `Flow Instance … completed`, and returns the answer as a WS frame.

Minimal Python WS client (needs `pip install websocket-client`):

```python
import sys, websocket
ws = websocket.create_connection(f"ws://localhost:{sys.argv[1]}/{sys.argv[2]}", timeout=90)
ws.send(sys.argv[3]); print(ws.recv()); ws.close()
```

If the LLM call fails with `unsupported protocol scheme ""` or a `/New_value/...` URL → the base URL is empty/placeholder (gotcha 4c). If `Configured connection is not a WebSocket Connection` → `wsconnection` isn't typed `any` (gotcha 4b). If the trigger nil-panics on connect → the handler is missing `schemas.output` (gotcha 4a). If the MCP server panics on start with `missing input schema` → a tool handler lacks its schemas (gotcha 1).
