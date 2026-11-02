# Lab 3 - build SW_Water_MCP with Cline + the FDA skills (gpt-4.1)

Three verified prompt sets, matching the workshop flow (starter first, then guardrails):

| | Builds | Prompts | Typical run (gpt-4.1) |
|---|---|---|---|
| A | the **finished** app with all four guardrails, from scratch: `~/FlogoLab/lab3/SW_Water_MCP.flogo` | 2 messages (part 1, part 2) | 127 model turns (71 + 56), about 7-8 min, about US$2.2-2.3 |
| B | the **starter** (no guardrails), from scratch: `~/FlogoLab/lab3/SW_Water_MCP_Starter.flogo` | 1 message | 37-43 model turns, about 3 min, about US$0.55-0.65 |
| C | **adds the guardrails** to an existing starter `~/FlogoLab/lab3/SW_Water_MCP_Starter.flogo` | 2 messages (part 1, part 2) | 80-82 model turns (40 + 41), about 6 min, about US$1.3-1.45 |

For C, the starter is either the one prompt B built, or the kit starter copied into place:
`cp ~/FlogoLab/lab3/starter/SW_Water_MCP_Starter.flogo ~/FlogoLab/lab3/` (both were verified).

The MCP server listens on `http://localhost:9090/mcp` and calls your Lab 1 (`:9999`) and Lab 2 (`:9998`) apps.

## One-time setup (once per VM, 2 minutes)

You need: VS Code with the **TIBCO Flogo extension 2.26.x** and **Cline**, and the workshop kit unzipped to
`~/FlogoLab` (it contains `cline/flogo-skills/`, `cline/flogo-skills.clinerules.md` and `cline/tools/`).
No `flogobuild` is needed: you run the app from the designer (**Run as Executable**).

1. Install the skills and the rules into the workspace:

   ```bash
   bash ~/FlogoLab/cline/setup-flogo-skills.sh
   ```

   It copies `fda`, `fda-mapping`, `flogobuild` and `flogo-unit-testing` to `~/FlogoLab/.claude/skills/`, the rules
   to `~/FlogoLab/.clinerules/flogo-skills.md`, and checks that `~/FlogoLab/cline/tools/fda` finds
   `flogodesign-cli` in the Flogo extension. By hand, the same thing is:

   ```bash
   mkdir -p ~/FlogoLab/.claude/skills ~/FlogoLab/.clinerules
   cp -r ~/FlogoLab/cline/flogo-skills/* ~/FlogoLab/.claude/skills/
   cp ~/FlogoLab/cline/flogo-skills.clinerules.md ~/FlogoLab/.clinerules/flogo-skills.md
   chmod +x ~/FlogoLab/cline/tools/*
   ~/FlogoLab/cline/tools/fda version
   ```

   (Global alternative for the skills: copy them to `~/.cline/skills/` instead. The rules file must still go to
   `~/FlogoLab/.clinerules/`.)
2. In VS Code open the folder `~/FlogoLab` (File > Open Folder). Cline reads skills and rules from the open folder.
3. In Cline pick the model: API Provider **OpenAI**, model **gpt-4.1**.
4. Open Cline's **Rules & Skills** panel (the scale icon under the chat box):
   - **Skills** tab: `fda`, `fda-mapping`, `flogobuild` and `flogo-unit-testing` are listed and switched on.
     (If there is no Skills tab, turn Skills on under Cline Settings > Features.)
   - **Rules** tab: `flogo-skills.md` is on. If `cline-rules-flogo-fda.md` (the FDA *MCP server* rules for the
     Lab 2 picture variant) is also listed, switch it **off** for these prompts: it tells Cline to use MCP tools
     instead of the fda command line.
5. Auto-approve (recommended): a build is 40-130 terminal commands. In Cline's Auto-approve bar turn on **Read
   project files**, **Edit project files** and **Execute all commands**, and raise **Max requests** to 150.
   Otherwise you click **Approve** on every `fda` command.

What Cline does with these files: at the start it only sees each skill's name and description; when your prompt
says "use the fda and fda-mapping skills" it loads their full text. The rules file tells it to run fda through
`~/FlogoLab/cline/tools/fda` (the extension path changes with every update), to change `.flogo` files only with
fda, the three designer-only rules, and the fda recipes the skills do not spell out (REST/MCP triggers, link
types via `~/FlogoLab/cline/tools/fda-link`, Invoke REST settings).

## A - the finished app from scratch (two messages, same Cline task)

Send part 1, wait for Cline's summary, then send part 2 in the same chat.

```text
Use the fda and fda-mapping skills to build a new Flogo MCP server app from scratch: ~/FlogoLab/lab3/SW_Water_MCP.flogo (app name SW_Water_MCP). It gives AI agents two governed tools over our Lab 1 and Lab 2 APIs. I will give you the work in two parts; this is part 1 (app, trigger and the first tool).

App properties:
- Lab1.AssessURL (string) = http://localhost:9999/rainfall-risk/assessments
- Lab2.LeakReportURL (string) = http://localhost:9998/leak-reports
- MCP.ApiKey = password property with plain value sw-workshop-key: create it as type string with the SECRET: value printed by ~/FlogoLab/cline/tools/flogo-encrypt sw-workshop-key

MCP Server trigger MCPServer (tr_mcpserver): serverName SW_Water_MCP, serverVersion 1.0.0, serverType HTTP, serverPort 9090, serverEndpointPath /mcp, authType API Key, authToken = app property MCP.ApiKey.

Tool 1: assess_rainfall_risk -> flow AssessRainfallRisk. Tool title "Assess rainfall risk". Hints: readOnly false, destructive false, idempotent false, openWorld true. Description: "Assess the wet-weather overflow/inflow risk at one Sydney Water site in Greater Sydney from forecast rainfall. Calls the Rainfall Risk API, which reads the weather forecast and, when the risk is MEDIUM or HIGH, raises an inspection request in Field Service. forecastDays must be 1-7; latitude/longitude must be inside Greater Sydney (latitude -34.2 to -33.3, longitude 150.5 to 151.4). Returns siteId, siteName, riskLevel (LOW, MEDIUM or HIGH), totalRainfallMm, inspectionRequested and message."
Arguments schema (all 5 required, no enum): siteId string "Sydney Water site ID, e.g. PS-102"; siteName string "Site name, e.g. Parramatta Sewage Pumping Station SP0102"; latitude number "Site latitude in decimal degrees; Greater Sydney only (-34.2 to -33.3)"; longitude number "Site longitude in decimal degrees; Greater Sydney only (150.5 to 151.4)"; forecastDays integer "Number of forecast days to assess, 1 to 7".
Flow AssessRainfallRisk:
1. LogCall (Log): string.concat("assess_rainfall_risk called with ", coerce.toString($flow.arguments))
2. ValidateInput (Mapper, field rejectReason string) = (coerce.toInt($flow.arguments.forecastDays) < 1 || coerce.toInt($flow.arguments.forecastDays) > 7) ? string.concat("forecastDays must be between 1 and 7 (got ", coerce.toString($flow.arguments.forecastDays), ")") : ((coerce.toFloat64($flow.arguments.latitude) < -34.2 || coerce.toFloat64($flow.arguments.latitude) > -33.3 || coerce.toFloat64($flow.arguments.longitude) < 150.5 || coerce.toFloat64($flow.arguments.longitude) > 151.4) ? string.concat("site must be in Greater Sydney (latitude -34.2 to -33.3, longitude 150.5 to 151.4), got ", coerce.toString($flow.arguments.latitude), ", ", coerce.toString($flow.arguments.longitude)) : "")
3. Success with condition $activity[ValidateInput].output.rejectReason != "" -> ReturnRejected (Return): response.error = string.concat("Rejected by guardrail: ", $activity[ValidateInput].output.rejectReason)
4. Otherwise -> CallRainfallRiskAPI (Invoke REST): POST, URL = app property Lab1.AssessURL, Throw Error = true. JSON body {siteId, siteName, latitude (number), longitude (number), forecastDays (integer)}, each = $flow.arguments.<same field>. Response schema sample {"siteId":"PS-102","siteName":"x","riskLevel":"MEDIUM","totalRainfallMm":16.5,"inspectionRequested":true,"message":"x"}.
5. CallRainfallRiskAPI -> ShapeResult (Mapper with those same 6 fields, each = $activity[CallRainfallRiskAPI].responseBody.<field>) -> Return (Return): response.data = coerce.toString($activity[ShapeResult].output)
6. Error link CallRainfallRiskAPI -> ReturnBackendError (Return): response.error = string.concat("Rainfall Risk API (Lab 1) failed: ", $error[CallRainfallRiskAPI].message)
Links of AssessRainfallRisk - exactly these 7: StartActivity -> LogCall; LogCall -> ValidateInput; ValidateInput -> ReturnRejected (expression $activity[ValidateInput].output.rejectReason != ""); ValidateInput -> CallRainfallRiskAPI (exprOtherwise); CallRainfallRiskAPI -> ShapeResult; ShapeResult -> Return; CallRainfallRiskAPI -> ReturnBackendError (error).


Work one activity at a time: create it (with --doNotLink), then set ALL of its settings, schemas and mappings before you create the next one. Make the links last, with fda-link. Designer rules: the URL is one whole app property, the error branch uses $error[<task>].message, and expressions in mappings start with =. Copy every expression character for character: do not add, drop or move parentheses or quotes.
When part 1 is done, show me the links of AssessRainfallRisk (fda-link with just the file and flow), run fda cm and the validator, and tell me what you built.
```

```text
Part 2: in the same app ~/FlogoLab/lab3/SW_Water_MCP.flogo (trigger MCPServer, already built in part 1), add the second tool with the fda and fda-mapping skills.

Tool 2: report_leak -> flow ReportLeak. Tool title "Report a water leak". Same hints. Description: "Log a water leak reported by a resident or a field crew. Calls the Leak Report API, which creates a work order in Field Service. reportId must look like LR-1234; severity must be HIGH, MEDIUM or LOW; description is what the reporter said, 10-500 characters. Returns reportId, workOrderRef, priority (P1, P2 or P3) and status."
Arguments schema (all 5 required, all strings, no enum): reportId "Leak report ID: LR- followed by 4 digits, e.g. LR-2001"; address "Street address of the leak, e.g. 12 Church St"; suburb "Suburb, e.g. Parramatta"; description "What the reporter observed, in their words (10-500 characters)"; severity "HIGH, MEDIUM or LOW".
Flow ReportLeak (no LogCall here - logging raw arguments would leak PII):
1. ValidateInput (Mapper, rejectReason string) = string.matchRegEx("^LR-[0-9]{4}$", $flow.arguments.reportId) == false ? string.concat("reportId must look like LR-1234 (got ", $flow.arguments.reportId, ")") : (($flow.arguments.severity != "HIGH" && $flow.arguments.severity != "MEDIUM" && $flow.arguments.severity != "LOW") ? string.concat("severity must be HIGH, MEDIUM or LOW (got ", $flow.arguments.severity, ")") : ((string.len($flow.arguments.description) < 10 || string.len($flow.arguments.description) > 500) ? "description must be 10-500 characters" : ""))
2. Same ReturnRejected branch and condition as in AssessRainfallRisk; otherwise -> MaskPII (Mapper, field description string) = string.replaceRegEx("([+]61[ ]?|0)4[0-9]{2}[ -]?[0-9]{3}[ -]?[0-9]{3}|([(]0[2378][)]|0[2378]|[+]61[ ]?[2378])[ -]?[0-9]{4}[ -]?[0-9]{4}", string.replaceRegEx("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}", $flow.arguments.description, "[redacted]"), "[redacted]")
3. LogForward (Log): string.concat("report_leak ", $flow.arguments.reportId, " forwarded to Lab 2 with description: ", $activity[MaskPII].output.description)
4. CallLeakReportAPI (Invoke REST): POST, URL = app property Lab2.LeakReportURL, Throw Error = true. JSON body {reportId, address, suburb, description, severity}: description = $activity[MaskPII].output.description, the others = $flow.arguments.<same field>. Response schema sample {"reportId":"LR-2001","workOrderRef":"WO-LR-2001","priority":"P1","status":"RECEIVED"}.
5. CallLeakReportAPI -> ShapeResult (Mapper with those 4 fields from $activity[CallLeakReportAPI].responseBody) -> Return: response.data = coerce.toString($activity[ShapeResult].output)
6. Error link CallLeakReportAPI -> ReturnBackendError: response.error = string.concat("Leak Report API (Lab 2) failed: ", $error[CallLeakReportAPI].message)
Links of ReportLeak - exactly these 8: StartActivity -> ValidateInput; ValidateInput -> ReturnRejected (expression $activity[ValidateInput].output.rejectReason != ""); ValidateInput -> MaskPII (exprOtherwise); MaskPII -> LogForward; LogForward -> CallLeakReportAPI; CallLeakReportAPI -> ShapeResult; ShapeResult -> Return; CallLeakReportAPI -> ReturnBackendError (error).


Work one activity at a time: create it (with --doNotLink), then set ALL of its settings, schemas and mappings before you create the next one. Make the links last, with fda-link. Designer rules: the URL is one whole app property, the error branch uses $error[<task>].message, and expressions in mappings start with =. Copy every expression character for character: do not add, drop or move parentheses or quotes.
When done, show me the links of both flows (fda-link with just the file and flow), run fda cm and the validator, and summarise anything I still need to finish in the Flogo designer.
```

## B - the starter from scratch (one message)

```text
Use the fda and fda-mapping skills to build a new Flogo MCP server app from scratch: ~/FlogoLab/lab3/SW_Water_MCP_Starter.flogo (app name SW_Water_MCP_Starter). It exposes our Lab 1 and Lab 2 APIs as two MCP tools, with no guardrails yet.

App properties: Lab1.AssessURL (string) = http://localhost:9999/rainfall-risk/assessments and Lab2.LeakReportURL (string) = http://localhost:9998/leak-reports.

MCP Server trigger MCPServer (tr_mcpserver): serverName SW_Water_MCP, serverVersion 1.0.0, serverType HTTP, serverPort 9090, serverEndpointPath /mcp, authType None.

Tool assess_rainfall_risk -> flow AssessRainfallRisk, description "Assess rainfall risk for a site.". Arguments (all required): siteId string, siteName string, latitude number, longitude number, forecastDays integer.
Tool report_leak -> flow ReportLeak, description "Create a leak report.". Arguments (all required, all strings): reportId, address, suburb, description, severity.
Hints on both tools: readOnly false, destructive false, idempotent false, openWorld true.

Each flow is three activities in a row (add them with --doNotLink, then link StartActivity -> LogCall -> Call...API -> Return with fda-link):
1. LogCall (Log): string.concat("<tool name> called with ", coerce.toString($flow.arguments))
2. CallRainfallRiskAPI / CallLeakReportAPI (Invoke REST): POST, URL = app property Lab1.AssessURL / Lab2.LeakReportURL. JSON body = the same 5 fields as the tool arguments, each mapped from $flow.arguments.<same field>.
3. Return (Return): response.data = coerce.toString($activity[CallRainfallRiskAPI].responseBody) (or CallLeakReportAPI in ReportLeak)

Designer rule: each URL is one whole app property. Expressions in mappings start with =.
When done, run fda cm and the validator, and summarise anything I still need to finish in the Flogo designer.
```

## C - add the guardrails to an existing starter (two messages, same Cline task)

```text
Use the fda and fda-mapping skills to add guardrails to my existing Flogo MCP server ~/FlogoLab/lab3/SW_Water_MCP_Starter.flogo (flows AssessRainfallRisk and ReportLeak, each LogCall -> Call...API -> Return, trigger MCPServer).
In fda commands the trigger is MCPServer (its id; the designer may show the name flogo-mcp-mcpsever - do not use that name) and the handlers are MCPServer.AssessRainfallRisk and MCPServer.ReportLeak. I will give you the work in two parts; this is part 1 (the API key and the AssessRainfallRisk flow). First describe the project, then change it in place with fda. fda has no "remove activity" command, so keep the existing activities and re-link around them: delete links with fda rl, add new activities with --doNotLink, and make every new link (and its type) with fda-link.

G1 - API key: create the password property MCP.ApiKey as type string with the SECRET: value printed by ~/FlogoLab/cline/tools/flogo-encrypt sw-workshop-key, then set the trigger authType to API Key and authToken to the app property MCP.ApiKey.

G2 - input validation, AssessRainfallRisk: remove the link LogCall -> CallRainfallRiskAPI (fda rl). Add ValidateInput (Mapper, field rejectReason string) after LogCall:
rejectReason = (coerce.toInt($flow.arguments.forecastDays) < 1 || coerce.toInt($flow.arguments.forecastDays) > 7) ? string.concat("forecastDays must be between 1 and 7 (got ", coerce.toString($flow.arguments.forecastDays), ")") : ((coerce.toFloat64($flow.arguments.latitude) < -34.2 || coerce.toFloat64($flow.arguments.latitude) > -33.3 || coerce.toFloat64($flow.arguments.longitude) < 150.5 || coerce.toFloat64($flow.arguments.longitude) > 151.4) ? string.concat("site must be in Greater Sydney (latitude -34.2 to -33.3, longitude 150.5 to 151.4), got ", coerce.toString($flow.arguments.latitude), ", ", coerce.toString($flow.arguments.longitude)) : "")
Links out of ValidateInput: success with condition $activity[ValidateInput].output.rejectReason != "" -> new ReturnRejected (Return, response.error = string.concat("Rejected by guardrail: ", $activity[ValidateInput].output.rejectReason)); otherwise -> CallRainfallRiskAPI.

G4 - safe errors and output, AssessRainfallRisk: set Throw Error = true on CallRainfallRiskAPI and give it a response schema {siteId, siteName, riskLevel, totalRainfallMm (number), inspectionRequested (boolean), message}. Remove the link CallRainfallRiskAPI -> Return, add ShapeResult (Mapper with those 6 fields, each = $activity[CallRainfallRiskAPI].responseBody.<field>) between them, and map Return response.data = coerce.toString($activity[ShapeResult].output). Add an error link CallRainfallRiskAPI -> new ReturnBackendError (Return): response.error = string.concat("Rainfall Risk API (Lab 1) failed: ", $error[CallRainfallRiskAPI].message).

Also set the tool title "Assess rainfall risk" on MCPServer.AssessRainfallRisk.
Expected links of AssessRainfallRisk when you are done: LogCall -> ValidateInput; ValidateInput -> ReturnRejected (expression); ValidateInput -> CallRainfallRiskAPI (exprOtherwise); CallRainfallRiskAPI -> ShapeResult; ShapeResult -> Return; CallRainfallRiskAPI -> ReturnBackendError (error). No other links.
Work one activity at a time: create it (with --doNotLink), then set ALL of its settings, schemas and mappings before the next one; then fix the links with fda rl and fda-link. Designer rules: URLs stay one whole app property, error branches use $error[<task>].message, the API key is a SECRET: value. Expressions in mappings start with =. Copy every expression character for character: do not add, drop or move parentheses or quotes.
When part 1 is done, show me the links of AssessRainfallRisk (fda-link with just the file and flow), run fda cm and the validator, and tell me what you changed.
```

```text
Part 2: in the same app ~/FlogoLab/lab3/SW_Water_MCP_Starter.flogo (trigger MCPServer, handler MCPServer.ReportLeak), add the guardrails to the ReportLeak flow with the fda and fda-mapping skills.

G2 - input validation, ReportLeak: remove the link LogCall -> CallLeakReportAPI. Add ValidateInput after LogCall:
rejectReason = string.matchRegEx("^LR-[0-9]{4}$", $flow.arguments.reportId) == false ? string.concat("reportId must look like LR-1234 (got ", $flow.arguments.reportId, ")") : (($flow.arguments.severity != "HIGH" && $flow.arguments.severity != "MEDIUM" && $flow.arguments.severity != "LOW") ? string.concat("severity must be HIGH, MEDIUM or LOW (got ", $flow.arguments.severity, ")") : ((string.len($flow.arguments.description) < 10 || string.len($flow.arguments.description) > 500) ? "description must be 10-500 characters" : ""))
Same ReturnRejected branch and condition; otherwise -> MaskPII.

G3 - PII masking, ReportLeak: change the LogCall message so it no longer logs the arguments: string.concat("report_leak called for ", $flow.arguments.reportId). Add MaskPII (Mapper, field description string):
description = string.replaceRegEx("([+]61[ ]?|0)4[0-9]{2}[ -]?[0-9]{3}[ -]?[0-9]{3}|([(]0[2378][)]|0[2378]|[+]61[ ]?[2378])[ -]?[0-9]{4}[ -]?[0-9]{4}", string.replaceRegEx("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}", $flow.arguments.description, "[redacted]"), "[redacted]")
then LogForward (Log): string.concat("report_leak ", $flow.arguments.reportId, " forwarded to Lab 2 with description: ", $activity[MaskPII].output.description), then link LogForward -> CallLeakReportAPI, and map CallLeakReportAPI body description = $activity[MaskPII].output.description.

G4 - safe errors and output, ReportLeak: set Throw Error = true on CallLeakReportAPI and give it a response schema {reportId, workOrderRef, priority, status}. Remove the link CallLeakReportAPI -> Return, add ShapeResult (Mapper with those 4 fields, each = $activity[CallLeakReportAPI].responseBody.<field>) between them, and map Return response.data = coerce.toString($activity[ShapeResult].output). Add an error link CallLeakReportAPI -> new ReturnBackendError (Return): response.error = string.concat("Leak Report API (Lab 2) failed: ", $error[CallLeakReportAPI].message).

Also set the tool title "Report a water leak" on MCPServer.ReportLeak.
Expected links of ReportLeak when you are done: LogCall -> ValidateInput; ValidateInput -> ReturnRejected (expression); ValidateInput -> MaskPII (exprOtherwise); MaskPII -> LogForward; LogForward -> CallLeakReportAPI; CallLeakReportAPI -> ShapeResult; ShapeResult -> Return; CallLeakReportAPI -> ReturnBackendError (error). No other links.
Work one activity at a time: create it (with --doNotLink), then set ALL of its settings, schemas and mappings before the next one; then fix the links with fda rl and fda-link. Designer rules: URLs stay one whole app property, error branches use $error[<task>].message, the API key is a SECRET: value. Expressions in mappings start with =. Copy every expression character for character: do not add, drop or move parentheses or quotes.
When done, show me the links of both flows (fda-link with just the file and flow), run fda cm and the validator, and summarise anything I still need to finish in the Flogo designer.
```

## What to expect

- Cline loads `fda` and `fda-mapping` and runs only terminal commands: `fda ...`, `fda-link ...` (links and link
  types) and `~/FlogoLab/cline/tools/flogo-encrypt sw-workshop-key` (the `SECRET:` value of the password property
  `MCP.ApiKey`). Each part ends with `fda cm`, the validator and a summary.
- Why two messages for A and C: in one message gpt-4.1 built every activity but skipped most mappings and settings
  (verified, run 2 of each). Split in two, every part completes.
- Prompt C does not delete the starter's `LogCall` in ReportLeak (fda has no "remove activity"): it changes its
  message so it logs only the reportId. On the kit starter, fda also adds an unlinked `StartActivity` (no-op) to
  each flow; it does nothing and you may delete it in the designer.

## Finish and check in the designer

1. Open the `.flogo`, drag the activities apart where they overlap (fda does not lay out flows).
2. Check, with no red errors:
   - Trigger: Server Name `SW_Water_MCP`, port `9090`, path `/mcp`; A and C: Authentication Type **API Key**,
     Secret bound to `MCP.ApiKey`, and `MCP.ApiKey` shows as a **Password** property (B: Authentication None).
   - Each tool's arguments schema, the ValidateInput conditions (*Success with condition* to ReturnRejected,
     *Success with no matching condition* onwards), **Throw Error** on the Invoke REST activities and the *Error*
     links to ReturnBackendError using `$error[CallRainfallRiskAPI].message` / `$error[CallLeakReportAPI].message`.
   - Invoke REST URLs bound to `Lab1.AssessURL` / `Lab2.LeakReportURL`.
3. Save and **Run as Executable**, with Lab 1 and Lab 2 running.

## Test

```bash
bash ~/FlogoLab/lab3/test-mcp.sh             # finished app (A, or B + C): API key + guardrails
bash ~/FlogoLab/lab3/test-mcp.sh --no-key    # starter (B): no auth, everything passes through
```

The finished app's terminal shows `report_leak LR-2001 forwarded to Lab 2 with description: ... [redacted] ...`.

## How these prompts were verified (2 Nov 2026)

gpt-4.1 in the Cline emulator (`_build/cline_skills_harness.py`) ran each prompt set in a fresh workspace;
`_build/cline_verify.py` then ran `fda cm`, `designer_lint.py`, `validate_flogo_apps.py`, the contract checks, a
`flogobuild` build, `test-mcp.sh` against the result (with the kit Lab 1 / Lab 2 apps on 9999 / 9998), a capture
proxy in front of Lab 2 (phone, landline and email arrive as `[redacted]`) and a Lab 1-down call (MCP error
`Rainfall Risk API (Lab 1) failed: ...`). Results: A passed runs 3, 5 and 6 (45-46/46 checks; run 6 = these exact prompts and rules); run 4 failed to start because gpt-4.1 wrapped the ReportLeak ValidateInput expression in an extra pair of parentheses, which led to the 'copy every expression character for character' sentence. B passed runs 1-3 (run 3 = this prompt, 18/18). C passed on the kit starter (runs 3 and 6, 45-46/46) and on the starter built by prompt B (run 4, 45/45); run 5 returned the backend error text unevaluated (Return mapped without .mapping.), which the rules file now covers (run 6, 46/46). Transcripts:
`verification/cline-skills/lab3*-run*.md`. Not verified: the designer UI, Cline itself on Ubuntu.
