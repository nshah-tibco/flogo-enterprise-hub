# bw6-flogo-modernize

Modernize a **TIBCO BusinessWorks 6 (BW6) REST application** as a **TIBCO Flogo 2.x** application with an AI
coding agent (Claude Code). The Flogo app exposes the same REST API and the same MCP tools as the BW6 app. The
two run side by side, so every answer can be checked against BW6 before you switch traffic.

The agent follows [SKILL.md](SKILL.md). This README is for the people who use it.

## What it does

1. **Analyzes** a BW6 module. It decodes the processes, the XSLT mappings, the shared resources, the module
   properties and the MCP configuration.
2. **Presents a modernization plan** and waits for your approval. The plan shows:
   - what the Flogo app will contain, one to one with BW6;
   - how each mapping translates;
   - what Flogo has no direct equivalent for, and the workaround;
   - what the agent needs from you.

   **Nothing is built until you approve.**
3. **Builds** the Flogo app with the Flogo Design CLI (`fda`). The `.flogo` file is never hand-edited.
4. **Verifies** the app:
   - mapping rules (`fda cm`);
   - a check that the VS Code designer won't drop activities when you open the app;
   - a **side-by-side parity test** against the running BW6 app;
   - if an AI agent uses the tools, its scenarios replayed against the Flogo tools.
5. **Hands over** a summary: what was built, how it was verified, what wasn't modernized, and the
   **manual steps** to run it end to end.

It is called *modernization*, not migration, because BW6 keeps running until the Flogo app has proven itself.

## Inputs

| Input | Required | Why |
|---|---|---|
| BW6 **module folder** (the one with `META-INF/module.bwm`) | yes | the source of truth |
| Flogo version | fixed: 2.x | this skill targets Flogo 2.x |
| Flogo **app name** | no (default: module name without dots) | file and app name |
| **Ports** | no (default: BW port +1000 for REST, +100 more for MCP) | runs next to BW6 without clashes |
| BW6 app **running**, its base URL and BW **MCP endpoint** | for verification | parity test calls both apps |
| **MCP exposure**: only BW's configured tools, or every operation | asked when it matters | BW exposes every operation of a module without MCP configuration; that can include admin/write operations |
| **Database** (same as BW6 or a copy), **user/password** | when the module uses JDBC | BW stores its password obfuscated; it can't be reused |
| Whether tests may **write** tagged fixture rows (deleted afterwards) or run **destructive** operations | when the module writes | parity of write operations |
| **LLM / vector store** choices and API key | when the module uses BW AI/RAG palettes | e.g. OpenAI vector store + model |
| **Called services**: base URLs and auth | when the module calls other services | outbound REST calls |
| **Build and run**, or generate only | asked | builds need `flogobuild` and Go |
| An **AI orchestrator** `.flogo` | optional | prove the agent works with the Flogo tools |

**Tools needed:**

- **To generate the app:** VS Code with the TIBCO Flogo extension (it includes `fda`) and Python 3.9 or later.
- **To build:** `flogobuild` and Go.
- **For the optional designer cross-check:** Node.js.

## Outputs

| Output | Where |
|---|---|
| Analysis: spec JSON, Flogo-ready OpenAPI, per-operation report with **decoded XSLT** | `<work>/analysis/<Module>.{bw6spec.json,openapi.json,report.md}` |
| **Modernization plan** (for approval) | `<work>/analysis/<Module>.plan.md` |
| Flogo app | `<FLOGO_APPS_DIR>/<AppName>.flogo` (`FLOGO_APPS_DIR` from `config.md`) |
| Business-logic script (re-runnable) | `<work>/<app>_logic.py` |
| Parity report | `<work>/parity_report.md` |
| **Hand-over summary** with manual run steps | `<AppName>.handover.md` (secrets are never printed) |
| Optional: rewired orchestrator copy | `<FLOGO_APPS_DIR>/<Orch>Modernized.flogo` |

## How it works

```
BW6 module ─► analyze_bw6.py ─► modernization_plan.py ─► YOU APPROVE ─► scaffold_flogo_app.py
          ─► <app>_logic.py (flogo_logic_lib) ─► cm + designer-load gate ─► parity_check.py
          ─► [rewire_orchestrator.py] ─► handover_summary.py ─► YOU RUN IT
```

| Step | BW6 | Flogo |
|---|---|---|
| Trigger | REST service binding (HTTP connector) | REST trigger, one handler per operation, port from app property `REST_PORT` |
| MCP | BW MCP server (`-Dbw.enable.mcp.server=true`) | MCP Server trigger on `MCP_PORT`, one `mcp_<tool>` flow per tool that calls the REST flow, so REST and MCP answers are identical |
| Process | one `onMessage` branch per operation | one flow per operation (`<operationId>_<METHOD>`) |
| Reply | `reply` with XSLT | Configure HTTP Response + Return, one pair per outcome and status code |
| Conditional transitions | `bpws:link` with a condition | links with a condition expression |
| Sub-process / loop | call process, Iterate group | subflow, subflow with an iterator |
| JDBC | JDBC Query / Update / SQL Direct | Flogo database connector activities (SQL Server verified) |
| JSON parse / render | JsonParser / JsonRender | typed mappers / `utility.renderJSON` |
| RAG (BW AI plugin) | chunk / ingest / query | OpenAI vector store via `extensions/openAI` + Agentic AI LLM Client (verified) |
| Module properties | substvar values | app properties (passwords as `SECRET:` or supplied at run time) |
| Errors | HTML pages / Java stack traces | JSON `{error, message}` with 400/403/404/409/422/500 |

## How mappings are handled

BW6 maps data with XSLT, which is richer than Flogo's mapper. The skill doesn't try to run XSLT. It
**rewrites each mapping as Flogo expressions, field by field**:

1. **Decode.** The analyzer turns each activity's HTML-encoded XSLT into a compact, readable form and lists
   it per operation in `<Module>.report.md`. Example: `<if test="$post.item/customerId"> customerId={$post.item/customerId}; </if>`.
   It also lists the hardcoded literals, the XSLT constructs and XPath functions each operation uses, and the
   activities whose result nothing reads.
2. **Plan.** The plan's mapping table shows every construct and function in your module, its Flogo
   translation, and whether that translation is *verified* by an earlier parity run or only *planned*.
3. **Translate.** The logic script rebuilds each mapping with `fda mm`, one field at a time, using the
   library's building blocks:

   | XSLT | Flogo |
   |---|---|
   | `value-of` path / literal | `=$flow.queryParams.x`, `=$flow.pathParams.x`, `=$flow.body.x`, `=$activity[A].output.y`, or a literal |
   | `if` around an optional field | plain mapping; run with `FLOGO_MAPPING_OMIT_NULLS=true` |
   | `choose/when/otherwise` | ternary `cond ? a : b`, or one response branch per outcome (conditional links) |
   | `for-each` with a predicate, joins | `@foreach(source, item, filter)` via `Logic.select`; nested selects for joins |
   | `variable` | `Logic.compute`: a mapper of typed derived values |
   | JSON literals the process returns | `Logic.static_data`: typed mapper seeded with the same records (each operation's own copy) |
   | `concat`, `contains`, `count`, `string`, `current-dateTime`, date arithmetic, `tib:uuid` ... | `string.concat`, `string.contains`, `array.count`, `coerce.toString`, `datetime.*`, `utils.uuid()` ... (names checked against the Flogo function catalog) |
   | `not(x)` | `(x) == false` (the designer rejects unary `!`) |

4. **Check.** `fda cm` validates mapping references. The **parity test** then proves the mappings
   produce the same JSON as BW6 for the same requests, including edge cases.

Constructs that have no rule yet (for example `for-each-group` or `apply-templates`) are marked *decide* in
the plan, so you see them before anything is built.

## Limitations

- **REST modules only.**
  - Not supported, and flagged in the plan: SOAP bindings, JMS/EMS/Kafka/timer/file-poller starters, event
    handlers and compensation.
  - Swagger 2.0 descriptors must be converted to OpenAPI 3 first.
  - A module with several HTTP connectors gets one Flogo REST trigger.
- **Databases.** The SQL helpers are verified for **SQL Server**. Other databases (PostgreSQL, MySQL, Oracle,
  DB2) use the same pattern but are *planned*: verify them with parity.
- **Planned, not yet verified:** outbound REST calls (`invoke`), fault handlers (`catch` / `catchAll`), header
  parameters, success codes other than 200, non-JSON bodies, module properties beyond ports and connections.
  The plan lists them with the intended workaround.
- **Java code.** Java invoke steps are skipped when the analyzer proves nothing reads their result. Otherwise
  they have to be rewritten with mapping functions or as a Flogo Go extension, which is your decision.
- **Business logic is per app.** The generic scripts build everything except the per-operation logic. The
  agent writes that as a short Python script using the library, guided by the decoded XSLT and the 5 worked
  examples.
- **Parity needs BW running.** Without it, the app is built and gated but not proven equal.
- **Flogo 2.x designer quirks** that the runtime and `fda cm` don't catch are enforced by the library and
  listed in [gotchas](references/gotchas.md). Most important: the designer deletes activities on open when
  links are stored out of order (F37, filed as FLOGO-20730). Every build ends with a designer-load gate that
  catches this. The designer also removes empty-object literals (`{}`) from mappings when it saves (F38); the
  gate warns about each affected reply field.
- AI answers (RAG, LLM) can't be byte-identical. They are checked for the same response shape and the same
  facts (SEMANTIC).

## Sample prompts

- "Modernize the BW6 app at `C:\bw6\workspace\Orders.API` as a Flogo app."
- "Analyze `<path>/Customer.API` and show me how you would build it in Flogo. Don't build anything yet."
- "Here is a BW6 REST module: `<path>`. Rebuild it in Flogo with the same MCP tools, using database `<db>` and
  user `<user>`, then run a side-by-side parity test against the running BW6 app on port 8080."
- "Use `--mcp all` for `<module>`: the agents call every operation of it."
- "Modernize all REST modules under `<workspace>` one by one, starting with the simplest, and rewire
  `<orchestrator.flogo>` to the new Flogo MCP servers."
- "Generate the hand-over for `<app>.flogo`: what was built and how I run it."

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | the agent's procedure: inputs, both approval gates, commands, conventions, status |
| `scripts/analyze_bw6.py` | BW6 module → spec, Flogo-ready OpenAPI, report, gap warnings |
| `scripts/modernization_plan.py` | spec → plan for approval |
| `scripts/scaffold_flogo_app.py` | generic part of the app (project, REST trigger, MCP trigger and tool flows, ports) |
| `scripts/flogo_logic_lib.py` | library for the per-app logic (mappings, branches, SQL, subflows, RAG, LLM, link order + gates) |
| `scripts/parity_check.py` | side-by-side REST + MCP comparison with BW6 |
| `scripts/designer_load_check.py`, `scripts/designer_tree.js` | designer-load gate (`--fix` re-orders links; `--designer-js` runs the designer's own code) |
| `scripts/restore_branch_returns.py` | repairs branch Returns lost when an app was opened in the designer |
| `scripts/rewire_orchestrator.py` | copy of an AI orchestrator pointed at the Flogo MCP servers |
| `scripts/handover_summary.py` | final summary + manual run steps |
| `scripts/extend_fda_catalog.py`, `scripts/fdalib.py` | user-extension activities for fda; fda wrapper |
| `examples/*_logic.py` | 5 worked examples (lookup, joins/dates, several outcomes, SQL writes, RAG) |
| `references/bw6-to-flogo-patterns.md` | BW6 → Flogo patterns with verified/planned status |
| `references/gotchas.md` | every trap found so far: symptom, cause, fix |
