# Flogo Design Assistant (FDA) rules for Cline — Sydney Water Flogo Workshop

Copy this file into `~/FlogoLab/.clinerules/` (the folder you open in VS Code).
Cline loads every Markdown file in `.clinerules/` automatically; you can toggle it in the
Rules panel (scale icon to the left of the model picker).

## Who you are working with

- You are helping an integration developer build **TIBCO Flogo 2.26** apps (`.flogo` files) in VS Code.
- Use the **Flogo Design Assistant MCP tools** (server `flogo-fda-lab2`) to create and change Flogo
  artifacts. Do not hand-edit the `.flogo` JSON with file-write tools.
- Each FDA server edits exactly **one** `.flogo` file — the file given to it with `-f`
  (Lab 2: `~/FlogoLab/lab2/SW_LeakReport.flogo`).
- FDA is a **Tech Preview**. Tell the developer what you created so they can review it in the designer.

## How to use the FDA tools

1. **Describe before you change.** Start with `describe-project` to see triggers, flows, activities,
   schemas and connections.
2. **Always run `describe-attributes` before `set-attribute`** on the same item, so you use the real
   attribute names.
3. **Set one configuration at a time.** One `set-attribute` call per field. Check the result before the next.
4. **List the activity types first.** Before creating activities, list the possible activity types and
   pick the right one for each step.
5. **Format the flow** with `format-flow` in `auto` mode after adding activities or links.
6. When finished, summarise: flows, activities, links, schemas, connections and app properties created,
   plus anything you could **not** set (the developer will finish it in the designer).

## Flogo expression rules

- A value that contains an **expression must start with `=`**. Without it, Flogo stores a literal string.
  - Literal: `"Leak report received"`
  - Expression: `"=$flow.body.suburb"`
- Activity outputs: `=$activity[<ActivityName>].<field>` (REST response body:
  `=$activity[<ActivityName>].responseBody.<field>`).
- Flow inputs: `=$flow.<field>`. **REST path parameters are `$flow.pathParams.<name>`**; query
  parameters `$flow.queryParams.<name>`; the JSON body `$flow.body.<field>`.
- App properties: `=$property["Group.Name"]`.
- Concatenate strings with `=string.concat(a, b)` (more arguments are allowed).
- Conditions on links use the same expression syntax, e.g. `$activity[Classify].severity == "HIGH"`.
- Strings in expressions use double quotes.

## Prompt 1 — build a flow from a picture (Lab 2a)

Attach the image `~/FlogoLab/lab2/leak-report-process.png` to the message with Cline's **+** (Add Files & Images)
button, then send:

```
Create the Flogo flow described in this picture using the flogo design tools. Use parallel paths where activities are drawn next to each other.
Details:
- Flow LeakReportIntake. REST trigger ReceiveHTTPMessage (type tr_rest) with the trigger setting port = 9998, and a POST handler on /leak-reports for the flow.
- Activities in this order, with these types: LogReport (act_general_log), BuildWorkOrder (act_general_mapper), CreateWorkOrder (act_general_rest), LogAudit (act_general_log), Reply201 (act_default_actreturn).
- BuildWorkOrder links to BOTH CreateWorkOrder and LogAudit (parallel paths); both of those link to Reply201.
- App property FieldService.URL = https://postman-echo.com/post. On CreateWorkOrder set input Method = POST and input Uri = the app property FieldService.URL.
- Format the flow (auto).
Only build the structure: do not create schemas or mappings - I will configure the request/reply schemas and the mappings in the Flogo designer. Finish with a short summary.
```

Build only the structure FDA does well (flow, trigger, handler, activities, links, app property, REST
Method/Uri, format). Do not create schemas or mappings — the participant does those in the designer.
The REST trigger port must be **9998** (9999 is Lab 1).

Known FDA behaviour:
- `remove-link` over MCP ignores its arguments (no-op) — tell the user to delete the link in the designer.
- `check-mappings` reports `TR_REST_NO_SWAGGER` ("runtime will panic") — a false positive. Never replace
  the REST trigger because of it.
- Do not call `list-activity-types` — the types are named in the prompt and its large output is re-sent
  every turn (cost).
- FDA's built-in `create-flogo-flow-from-picture` prompt is not used in this workshop (too many calls).

## Prompt 2 — set mappings (Lab 2a, when mappings are missing)

```
To set a mapping describe the project to see what are the available outputs from previous activities. Then set the configuration on the activity: <flow_name>.<activity_name>.input.input.mapping.<field> To: '=$activity[<input_activity_name>].output.<field>'. Always set one configuration at a time. Concatenate with '=string.concat(a, b)'.
```

Replace `<flow_name>`, `<activity_name>`, `<field>` and `<input_activity_name>` with real names from
`describe-project`.

## Lab 2b — modify and explain

- To modify: describe the change in plain words, e.g. Prompt 2 in `lab2/prompts.md` ("Add a Log activity named
  LogWorkOrderId after CreateWorkOrder…"). Follow the rules above.
- To explain: use the FDA `explain` tool for activities and functions (Prompt 3 in `lab2/prompts.md`), or run
  `describe-project` and explain the flow step by step in plain English.

## Lab 3 — the `sw-water-mcp` MCP server

- `sw-water-mcp` is a Flogo MCP server (streamable HTTP, `http://localhost:9090/mcp`) that exposes the participant's
  own Lab 1 and Lab 2 APIs as two tools:
  - `assess_rainfall_risk` {siteId, siteName, latitude, longitude, forecastDays} → Lab 1 rainfall-risk API (:9999).
    It may raise a field inspection, so it is **not** read-only.
  - `report_leak` {reportId, address, suburb, description, severity} → Lab 2 leak-report API (:9998). It creates a
    work order in the field-service SaaS.
- Use these tools to answer leak-report and rainfall-risk requests. Do **not** use the FDA tools in Lab 3 and do not
  call the Lab 1 / Lab 2 HTTP APIs directly with other tools — the point of the lab is that the agent goes through
  the governed MCP tools.
- Never invent report IDs, site IDs, coordinates or contact details. If a tool returns `Rejected by guardrail: ...`,
  report the reason to the user; do not retry with made-up or "corrected" values.
- When the user asks you to send exact values "without changing or correcting them", send them exactly as given —
  the participant is testing the server's guardrails.
- If a tool result says `connection refused` on port 9999 or 9998, tell the user their Lab 1 or Lab 2 app is not
  running.
