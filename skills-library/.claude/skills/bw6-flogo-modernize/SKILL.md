---
name: bw6-flogo-modernize
description: >
  Modernize a TIBCO BusinessWorks 6 (BW6) REST application as a TIBCO Flogo 2.x app: same REST API,
  same MCP tools, verified side by side against the running BW6 app. Analyzes the BW6 module, presents a
  modernization plan (1:1 triggers/activities/connections/properties, mapping translation, gaps and
  workarounds) for approval, builds only after approval, and ends with a hand-over summary and manual run
  steps. Use when the user gives a BW6 project/module path and asks to rebuild, re-implement, modernize or
  "convert" it in Flogo, or asks how a BW6 process maps to Flogo. Say "modernize", never "migrate".
metadata:
  version: "0.7.0"
  last-updated-date: "2026-11-17"
---

# Modernize a BW6 REST app as a Flogo app

**Wording:** this is *modernization* (BW6 and Flogo run side by side; the Flogo app is a modern equivalent),
never "migration" — in code, docs, READMEs and replies. Human overview: [README.md](README.md).

**Input:** the path of one BW6 module folder (the one holding `META-INF/module.bwm`) — see
[Required inputs](#required-inputs--check-them-ask-never-guess). **Output:**
`<FLOGO_APPS_DIR>/<AppName>.flogo` exposing the same REST operations and MCP tools, an approved plan, a parity
report against the BW6 app, and a hand-over with the manual run steps.

**Two approval gates — never skip them:**
1. After analysis, present the **modernization plan** and build nothing until the user approves it.
2. At the end, present the **hand-over summary** (what was built, how it was verified, what is not modernized,
   manual steps) — never just "done".

Read [`references/gotchas.md`](references/gotchas.md) before building — every item there broke a real build.

## Prerequisites

- Resolve `fda` exactly as in `AGENT.md` → *Resolving the fda CLI* (Flogo **2.x**; this skill does not target
  3.x yet) and `export FDA=<path>`. Read `.claude/skills/config.md` for `FLOGO_APPS_DIR`, `FLOGOBUILD_PATH`,
  `FLOGOBUILD_CONTEXT_NAME`. Never hardcode those values.
- Python 3.9+ (scripts are stdlib only). On Windows run them with `python -I -X utf8`. Node.js only for the
  optional `--designer-js` cross-check.
- For parity the BW6 app must be running, with its MCP server enabled if it has MCP tools (BW 6.12 HF-002+:
  JVM arg `-Dbw.enable.mcp.server=true`; one endpoint serves all running modules, at the host/port set with
  `bwdesign setHttpMcpServerEnabled`).
- **User (repo-local) Flogo extensions** (e.g. `extensions/openAI` for RAG): fda doesn't know their activities.
  Run `scripts/extend_fda_catalog.py <extension-dir> --out <work>/fda-config.json` and
  `export FLOGO_DESIGN_CONFIG_FILE=<work>/fda-config.json` before scaffolding/logic. Build with a flogobuild
  context created with the extensions folder: `flogobuild create-context -n <name-without-dots> -v <flogo-vsix>
  -u <repo>/extensions`.

## Conventions

| Item | Rule |
|---|---|
| Ports | Flogo REST = BW HTTP port **+1000** (`--port-offset`); Flogo MCP = Flogo REST **+100** (`--mcp-port-offset`); app properties `REST_PORT` (number), `MCP_PORT` (string) — BW keeps running as the live baseline |
| Flows | one flow per REST operation, named `<operationId>_<METHOD>`; operationId = the BW MCP tool name when there is one |
| MCP | one `mcp_server` trigger per app, endpoint `/mcp`; each tool is a thin flow `mcp_<tool>` that calls the REST flow as a subflow and returns `{data: <body JSON>, error}` |
| MCP exposure | only operations configured as MCP tools in BW (`tool="true"` / `<restMcpTool>`); `--mcp all` reproduces BW's expose-everything default for modules without MCP config — ask first, it can expose admin/write operations to agents |
| Errors | BW answers bad input with HTML pages or Java stack traces; the Flogo app answers JSON `{error, message}` (400/403/404/409/422/500, extend with `--error-codes`). They show up as **IMPROVED** in the parity report |
| Runtime | run with `FLOGO_MAPPING_OMIT_NULLS=true` so absent inputs are omitted like BW does |
| Secrets | `SECRET:` (encrypted) only for fields the contribution declares as **password** (DB connections, LLM connections). A plain-string key field (e.g. the openAI extension's apiKey) gets a placeholder property and the real value at run time via `FLOGO_APP_PROPS_ENV=auto <PROPERTY>=<value>`. Passwords never go on a command line |
| Changes | `fda` only; never hand-edit a `.flogo` and never write one that is open in the designer |

## Required inputs — check them, ask, never guess

Nothing in this skill is specific to one BW6 workspace: every module name, path, port, model, store name and
credential comes from the user, from `config.md`, or from the BW6 sources. Before step 1, check each input below.
**If a REQUIRED input is missing or ambiguous, or a conditional one applies and is unanswered, STOP and ask** —
one message with all open questions, each with your recommended default. Never invent a value (URL, credential,
model, store name, module choice). User-facing version: README.md → *What you need to provide*.

| Input | Required? | Default / source | How to check |
|---|---|---|---|
| **BW6 module folder(s)** (holds `META-INF/module.bwm`; a `<Name>.application` with exactly one app module also works) | **yes** | — | `analyze_bw6.py <path> --list` lists the modules at/below a path with their REST operation count and the palettes that need extra inputs |
| **Target apps folder** | **yes** | `FLOGO_APPS_DIR` in `.claude/skills/config.md` (relative to config.md); the scaffold reads it when `--apps-dir` is omitted | config.md exists and sets it |
| **Which modules, in which order** | **yes**, when the path holds more than one module | propose: skip shared modules (0 REST operations), simplest first (fewest operations, no JDBC/AI), callers last | `--list` output |
| `fda` CLI | **yes** | `$FDA`, resolved as in `AGENT.md` (ask when several 2.x extensions are installed) | `"$FDA" version` |
| Flogo app name | no | module name without dots (`--app-name`); `--rename OLD=NEW` drops brand/customer names from everything generated | letters, digits, `_` |
| Ports | no | REST = BW HTTP port **+1000** (`--port-offset`), MCP = REST **+100** (`--mcp-port-offset`), browser-blocked ports skipped; `--bw-port` when BW's port is property-bound without a default | the plan shows them |
| MCP exposure | no — **ask** when the module has no MCP configuration | `explicit` (only BW-configured tools); `--mcp all` exposes every operation (may include admin/write ones) | plan section 1 |
| MCP endpoint path | no | `/mcp` (`--mcp-path`) | — |
| Error reply format | no | JSON `{error, message}`, or the API's own `ErrorResponse` schema when it declares one; codes 400/403/404/409/422/500, more with `--error-codes` | plan section 9 |
| **Database** (host/port/db, user, password; same DB as BW or a copy; may tests write/reset) | **only when the module uses JDBC** | host/port/database from the BW JDBC URL; user + password from the user (BW's password is obfuscated); password via env var, never on a command line | `--list` says `JDBC`; plan section 5 |
| **LLM provider / model / API key** | **only when the module uses AI/RAG palettes** | `LLM_Provider` / `LLM_Model` from config.md; key supplied at run time (`FLOGO_APP_PROPS_ENV=auto <PROPERTY>=<key>`), never stored in the `.flogo` | `--list` says `AI/RAG` |
| **Vector store name** | **only for RAG** | propose `<AppName>Docs`; must be identical in every app that shares the store (e.g. an ingest and a query module) | — |
| **Called services** (base URL, auth) | **only when the module calls other services** | stored as app properties | `--list` / plan section 9 |
| **Running BW6 instance**: base URL (+ BW MCP endpoint when the module has MCP tools) | for parity (step 6) | none — without it the app is built and gated, and the hand-over says parity was **not run** | `parity_check.py` refuses placeholder URLs |
| Build and run, or generate only | no | generate only (build only when asked) | — |
| AI orchestrator `.flogo` that uses the BW tools | no | — | only for step 7 |

**Stop and ask when** (batch these; offer the recommended default):
- the path does not exist, or `analyze_bw6.py` exits 2 (no `module.bwm`, several modules, an `.application` with
  several modules) — show the candidates it printed and ask which modules, in which order;
- `config.md` or its `FLOGO_APPS_DIR` is missing (offer `cp config.example.md config.md`);
- `$FDA` is unset or several Flogo 2.x extensions are installed (`AGENT.md`);
- the module uses JDBC and the database, user/password or "may tests write" decision is unknown;
- the module uses AI/RAG and the LLM provider/model, the key handling or the vector store name is not decided;
- the module calls other services and their base URLs/auth are unknown;
- the module has no MCP configuration (explicit vs `--mcp all`);
- it is unknown whether a BW6 instance is running for parity (ask for its base URL, or confirm parity is skipped).
The plan (step 2, section 9) repeats the open module-specific questions; ask them again there if still open.

## Workflow

### 0. Collect the inputs
Check every row of *Required inputs* above. `python -I -X utf8 scripts/analyze_bw6.py <path> --list` shows which
modules a path holds and which of them need DB / LLM / called-service inputs. Ask in one batch, then continue.

### 1. Analyze the BW6 module
```bash
python -I -X utf8 scripts/analyze_bw6.py <bw6-module-dir> --out <work>/analysis \
    [--port-offset 1000] [--mcp-port-offset 100] [--bw-port <port>] [--error-codes 401:Unauthorized,...] \
    [--rename OLD=NEW]
```
Exit code 2 = the path is not exactly one BW6 module: the message names the expected `META-INF/module.bwm` and
lists the candidate module folders it found — ask the user which (see *Required inputs*). A module with no REST
binding (shared module) is analyzed with a warning; there is nothing to scaffold for it.
Writes `<Module>.bw6spec.json` (operations, params, MCP tools, shared resources, module properties with
substvar values, per-operation activities with **decoded XSLT**, literals, XSLT constructs/functions used,
BPEL constructs such as fault handlers/loops/outbound calls, dead activities, and a `warnings` list of every
gap), `<Module>.openapi.json` (Flogo-ready spec) and `<Module>.report.md` (per-operation decoded logic).
Activities marked **not used by the reply** need no Flogo equivalent (the analyzer follows XSLT params,
configuration `$refs`, transition conditions and BW's `<task><endingVariables>`; side-effect activities are
never dead; Java invokes are only flagged for review).

### 2. Present the modernization plan — APPROVAL GATE
```bash
python -I -X utf8 scripts/modernization_plan.py <work>/analysis/<Module>.bw6spec.json [--app-name <Name>] [--mcp explicit|all]
```
Writes `<Module>.plan.md`: scope and ports; **triggers**, **flows**, **activities**, **connections**, **app
properties** one to one (BW6 → Flogo, with status *verified* / *planned* / *decide* / *manual* /
*unsupported*); how the **XSLT mappings** translate (constructs and functions found in this module → Flogo
expressions); **what Flogo has no direct equivalent for and the workaround**; the **inputs/decisions needed**;
and how it will be verified. Show the user the plan's key tables in the chat (not only the file path), ask the
section-9 questions, and **stop**. Proceed only on an explicit approval. If they change something (name,
exposure, workaround), re-run with the new options and show the changed parts.

### 3. Capture the parity cases (BW running)
Write `<work>/cases.json` for `scripts/parity_check.py`: every operation's happy path **and** edge cases —
missing/empty parameters, unknown ids, empty body, extra fields — plus one call per MCP tool **including
not-found calls**. Per-case/global `headers` are supported.
**Write operations**: use the database the user agreed on. Seed one identical, clearly tagged fixture per side,
point each side at its own fixture (`flogoBody`/`flogoPath` + `normalize`), `ignore` generated ids, compare the
rows each side wrote and delete the fixtures. Run destructive operations last, in a separate cases file.
See `examples/operations_logic.py`.

### 4. Build the Flogo app (fda only)
```bash
python -I -X utf8 scripts/scaffold_flogo_app.py --analysis <work>/analysis --work <work> \
    [--module <Module_slug>] [--app-name <AppName>] [--apps-dir <FLOGO_APPS_DIR>] [--mcp explicit|all] \
    [--mcp-path /mcp] [--force]
```
Defaults: `--module` = the only spec in `--analysis`, `--app-name` = the plan's app name, `--apps-dir` =
`FLOGO_APPS_DIR` from config.md. Pass the values the user approved in the plan. The scaffold checks its inputs
(spec present, REST operations, app name, apps folder, `$FDA`) before it creates or deletes anything.
Generic part: project, spec, `cas` skeleton, port properties, the query/path-parameter fixes, the MCP trigger
and `mcp_<tool>` flows; `plan.json` records the spec path. Then write `<work>/<app>_logic.py` with
[`scripts/flogo_logic_lib.py`](scripts/flogo_logic_lib.py), translating each operation's decoded XSLT
(**mappings**: README.md → *How mappings are handled*). Take every environment value (DB user, hosts, model,
store name, directories) from the user's answers or app properties — never from the examples. Worked examples
(they contain sample-specific names, data and defaults on purpose; copy the pattern, not the values):
[`promotions`](examples/promotions_logic.py) (lookup), [`orders`](examples/orders_logic.py) (joins, variables,
dates), [`inventory`](examples/inventory_logic.py) (several outcomes, body lookups, dead code skipped),
[`operations`](examples/operations_logic.py) (SQL Server reads/writes, role check, branch join),
[`policy`](examples/policy_logic.py) (RAG with a user extension, subflows, an iterator),
[`gas_cylinder`](examples/gas_cylinder_logic.py) (hardcoded XML data, top-level JSON array reply),
[`gas_docs_ingestion`](examples/gas_docs_ingestion_logic.py) (multipart file upload, binary write, MCP over multipart),
[`gas_docs_query`](examples/gas_docs_query_logic.py) (RAG with images: LLM Client for text, Invoke REST + json.jq for vision),
[`gas_ops_orchestrator_build`](examples/gas_ops_orchestrator_build.py) (an AI orchestrator over the Flogo MCP tools, no BW source).
`Logic.finish()` re-stores links in designer-safe order, runs `fda cm` (accepted failures:
`FOREACH_SCOPE_UNDEFINED` from a filtered `@foreach`; with subflows also `RESOLVER_UNKNOWN` for `$iteration` and
`ACTIVITY_OUTPUT_LEAF_UNKNOWN` for subflow/extension outputs) and the **designer-load gate**; it must end with
`designer load check: OK`. Re-running: `scaffold --force` then the logic script rebuilds from scratch; never
patch half-built apps.

### 5. Build and run (only when the user asked to build/run or verify end to end)
```bash
flogobuild build-exe -f <FLOGO_APPS_DIR>/<AppName>.flogo -c <FLOGOBUILD_CONTEXT_NAME> -o <FLOGO_APPS_DIR>/../bin
FLOGO_MAPPING_OMIT_NULLS=true <FLOGO_APPS_DIR>/../bin/<AppName>[.exe]   # wait for "MCP HTTP Server ... reachable on"
```
Stop it with Ctrl+C; a background exe on Windows needs `taskkill /PID <pid> /F` (`netstat -ano | findstr :<port>`),
on macOS/Linux `kill <pid>`. If `-o` misbehaves, see gotchas F12.

### 6. Verify parity
```bash
python -I -X utf8 scripts/parity_check.py <work>/cases.json --report <work>/parity_report.md [--timeout 60]
```
It refuses a cases file whose BW/Flogo URLs are missing or placeholders: get the BW base URL from the user. No
BW6 instance available → skip this step and state in the hand-over that parity was not run. Done = **0 MISMATCH**. MATCH = identical; EQUIVALENT = only null-vs-absent; IMPROVED = BW failed (5xx /
non-JSON) and Flogo answered a JSON error (a JSON 4xx from BW is compared normally); SEMANTIC = outputs that
cannot be identical (LLM answers, vector ids/scores): same status + shape + declared facts; ACCEPTED = a
deliberate difference declared with `"accept": "<why>"`.

**After the user opens the app in the designer**, run `scripts/designer_load_check.py <app.flogo> --designer-js`
and re-run the parity cases (at least the MCP not-found calls). Designer-only problems the runtime and `fda cm`
don't catch are listed in gotchas (F37: the designer deletes activities on open when links are stored out of
order — filed FLOGO-20730; F38: it removes empty-object literals such as `{}` / `[{}]` on save, so those replies change — the gate prints a WARN with the exact fields; tell the user). Repair with `restore_branch_returns.py` / `designer_load_check.py --fix` (app closed).

### 7. End to end with the agent (when an AI orchestrator uses the BW6 tools)
```bash
python -I -X utf8 scripts/rewire_orchestrator.py --source <orchestrator.flogo> --out <FLOGO_APPS_DIR>/<Orch>Modernized.flogo \
    [--port <free port>] --flogo-mcp <Name>=http://localhost:<MCP_PORT>/mcp [--flogo-mcp ...] [--bw-mcp <conn>] \
    [--flogo-only] [--api-key <key>]
```
Makes a **copy** (the source is never touched) that serves each tool name exactly once (Flogo tools from the
new MCP connections, the rest still from BW, or Flogo only). Build, run, replay the use case's scenarios and
confirm in the Flogo app log (`Executing Tool [mcp_<tool>]`) that the agent used the Flogo tools. Restart
orchestrators after restarting any MCP server (stale MCP sessions).

### 8. Hand over — FINAL SUMMARY
```bash
python -I -X utf8 scripts/handover_summary.py <app.flogo> --spec <work>/analysis/<Module>.bw6spec.json \
    --parity <work>/parity_report.md [--context <FLOGOBUILD_CONTEXT_NAME>] [--extensions-dir <repo>/extensions]
```
Present it in the chat: what was built (triggers, ports, operations, MCP tools, connections, properties —
secrets are never printed), verification (designer gate, parity counts with every IMPROVED/ACCEPTED/SEMANTIC
row), what was **not** modernized or needs attention, and the **manual steps** to run end to end (open in the
designer, set properties/credentials, build, run with env vars, smoke test, stop, scrub secrets before commit).
Apps in `Flogo_Apps/` are gitignored; scrub secrets before copying one into `samples/`.

## Maintaining this skill

After every module you modernize, before calling it done:

1. Fold any new pattern into the shared scripts (`analyze_bw6.py`, `scaffold_flogo_app.py`, `flogo_logic_lib.py`,
   `modernization_plan.py`), not only into that module's logic script. No sample-specific names, paths, ports,
   hosts, models, store names or data in `scripts/`, SKILL.md, README.md or `references/`: make it an argument
   with a documented default (or a config.md value) and add it to *Required inputs* when the user must supply it.
   Sample-specific values belong only in `examples/`, and examples take paths, users and keys as arguments/env.
2. In `references/bw6-to-flogo-patterns.md` (and the status maps in `modernization_plan.py`), mark a pattern
   **verified** only after a parity run proved it.
3. Add every new trap to `references/gotchas.md` (symptom, cause, fix).
4. Keep the module's logic script under `examples/` as another worked example.
5. Regression: after changing a shared script, rebuild every example module from scratch
   (`scaffold_flogo_app.py --force` + its example), run the designer-load gate and the parity check — 0 MISMATCH.
6. Bump `metadata.version`, update the Status table below and README.md *Limitations*.

## Status

| BW6 feature | Status |
|---|---|
| REST GET with query params, POST JSON body | **verified** (lookup module, 11 MATCH / 4 IMPROVED) |
| Path params, joins across datasets, XSLT variables, choose/when, date arithmetic | **verified** (19 MATCH / 4 IMPROVED / 1 ACCEPTED) |
| Dead Java/XML steps skipped, body-field lookups, several outcomes per operation, synthetic "not found" records, non-MCP REST operations | **verified** (41 MATCH / 8 IMPROVED) |
| SQL Server JDBC (query/insert/update/delete), branching write flow with a role check, branch join, writes verified row by row | **verified** (16 MATCH / 1 EQUIVALENT / 8 IMPROVED / 2 ACCEPTED; written rows 5/5) |
| Embedded JSON data (JsonParser over literals), for-each with predicate, conditional replies | **verified** |
| MCP tools (explicit), tool descriptions and input schemas identical to BW, MCP not-found calls | **verified** |
| BW AI-plugin RAG (chunk/ingest/query) -> OpenAI vector store via the repo-local `extensions/openAI` + Agentic AI LLM Client; static resource lookups; subflows incl. an iterator; MCP resource tools | **verified** (RAG ops = SEMANTIC parity) |
| AI orchestrator rewired to the Flogo MCP tools (BW stopped) | **verified** (all scenarios answered from Flogo tools) |
| Hardcoded XML data (ParseXml over a literal), top-level JSON array replies, API-declared error schema, MCP tools with path + body arguments | **verified** (`examples/gas_cylinder_logic.py`: 12 MATCH / 6 IMPROVED / 2 ACCEPTED; agent 3/3) |
| multipart/form-data uploads (files byte-for-byte, names via an extra field), File write Binary, MCP tool over a multipart operation, OpenAI vector store ingest | **verified** (`examples/gas_docs_ingestion_logic.py`; BW side failed - see its header) |
| RAG answers with images: vector search + LLM Client (text) / Invoke REST to the OpenAI chat API with images (json.jq request) | **verified** (`examples/gas_docs_query_logic.py`: grounded citations, PNG + JPEG labels read, SEMANTIC vs BW) |
| Other JDBC databases, BW outbound REST calls (`invoke`; Invoke REST itself is verified), fault handlers, module properties, headers, non-200 success codes, non-JSON bodies | **planned** — the plan flags them with the intended workaround; verify with parity before relying on it |
| Non-REST starters (JMS, timers, file pollers), SOAP bindings, event handlers, compensation, Swagger 2.0 descriptors, several HTTP connectors per module | **not supported** — flagged in the plan as *unsupported* / *decide* |

The verified rows come from the modules rebuilt in `examples/` (the BW6 sample workspaces under
`samples/Agentic_AI/BW6_Flogo_Samples/`). Analysis and planning were also exercised on other BW6 modules (REST and
SOAP samples, a Kafka-to-DB app); one of them (a REST module whose descriptor omits the binding's basePath) was
scaffolded end to end with `cm` and the designer gate passing.
