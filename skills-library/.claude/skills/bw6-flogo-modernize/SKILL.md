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
  version: "0.6.0"
  last-updated-date: "2026-11-16"
---

# Modernize a BW6 REST app as a Flogo app

**Wording:** this is *modernization* (BW6 and Flogo run side by side; the Flogo app is a modern equivalent),
never "migration" — in code, docs, READMEs and replies. Human overview: [README.md](README.md).

**Input:** the path of one BW6 module folder (the one holding `META-INF/module.bwm`). **Output:**
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

## Workflow

### 0. Collect the inputs
Ask only for what you can't find. Required: the **BW6 module path**. Then, as the plan shows they are needed:
Flogo app name (default: module name without dots), whether the **BW6 app is running** and its base URL / MCP
endpoint (for parity), **database** to use + credentials (BW's password is obfuscated and can't be reused) and
whether tests may write fixture rows or run destructive operations, **LLM / vector store** choices for AI
palettes, **called services** (base URLs, auth), MCP exposure (explicit vs all), whether to **build and run**
or only generate, and an **AI orchestrator** `.flogo` if the tools must be proven end to end. Full list:
README.md → *Inputs*.

### 1. Analyze the BW6 module
```bash
python -I -X utf8 scripts/analyze_bw6.py <bw6-module-dir> --out <work>/analysis \
    [--port-offset 1000] [--mcp-port-offset 100] [--bw-port <port>] [--error-codes 401:Unauthorized,...]
```
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
python -I -X utf8 scripts/scaffold_flogo_app.py --analysis <work>/analysis --module <Module_slug> \
    --app-name <AppName> --apps-dir <FLOGO_APPS_DIR> --work <work> [--mcp explicit|all] [--force]
```
Generic part: project, spec, `cas` skeleton, port properties, the query/path-parameter fixes, the MCP trigger
and `mcp_<tool>` flows; `plan.json` records the spec path. Then write `<work>/<app>_logic.py` with
[`scripts/flogo_logic_lib.py`](scripts/flogo_logic_lib.py), translating each operation's decoded XSLT
(**mappings**: README.md → *How mappings are handled*). Worked examples:
[`promotions`](examples/promotions_logic.py) (lookup), [`orders`](examples/orders_logic.py) (joins, variables,
dates), [`inventory`](examples/inventory_logic.py) (several outcomes, body lookups, dead code skipped),
[`operations`](examples/operations_logic.py) (SQL Server reads/writes, role check, branch join),
[`policy`](examples/policy_logic.py) (RAG with a user extension, subflows, an iterator).
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
python -I -X utf8 scripts/parity_check.py <work>/cases.json --report <work>/parity_report.md
```
Done = **0 MISMATCH**. MATCH = identical; EQUIVALENT = only null-vs-absent; IMPROVED = BW failed (5xx /
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
   `modernization_plan.py`), not only into that module's logic script. No sample-specific names, paths, ports or
   data in `scripts/` or in instruction text.
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
| Other JDBC databases, outbound REST calls (`invoke`), fault handlers, module properties, headers, non-200 success codes, non-JSON bodies | **planned** — the plan flags them with the intended workaround; verify with parity before relying on it |
| Non-REST starters (JMS, timers, file pollers), SOAP bindings, event handlers, compensation, Swagger 2.0 descriptors, several HTTP connectors per module | **not supported** — flagged in the plan as *unsupported* / *decide* |

The verified rows come from modernizing the five REST modules of the `Retail_AI_BW_Flogo` sample
(`examples/`).
