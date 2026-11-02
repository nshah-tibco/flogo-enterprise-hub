# Lab 2 - Process diagram to Flogo flow with Cline + Flogo Design Assistant (FDA)

App: **SW_LeakReport** - file `~/FlogoLab/lab2/SW_LeakReport.flogo` - REST `POST http://localhost:9998/leak-reports`

All prompts below were dry-run on 1 Nov 2026 against the FDA bundled with the Flogo VS Code
extension 2.26.7 (FDA 0.9.3) with gpt-4.1. Timings/costs are from that run. The lab VMs are Ubuntu: every path below
is a Linux path, and the FDA binary is `flogodesign-cli` (no `.exe`).

## 0. Cline MCP server entry (once - guide section 1.3)

Print the settings with your real paths filled in, then paste them into Cline > **MCP Servers** > **Configure** >
**Configure MCP Servers** (replace everything) and save:

```bash
bash ~/FlogoLab/cline/print-mcp-settings.sh
```

The FDA entry it prints looks like this (`<USER>` = `whoami`; `<EXT_DIR>` = the Flogo extension folder, see
`ls -d ~/.vscode/extensions/tibco.flogo-2.26.*`). JSON needs absolute paths - `~` is not expanded:

```json
{
  "mcpServers": {
    "flogo-fda-lab2": {
      "type": "stdio",
      "command": "/home/<USER>/.vscode/extensions/<EXT_DIR>/bin/flogodesign-cli",
      "args": ["-f", "/home/<USER>/FlogoLab/lab2/SW_LeakReport.flogo", "mcp", "stdio"],
      "disabled": false,
      "timeout": 120
    }
  }
}
```

- No `-c` config file is needed with the extension-bundled FDA (it has a built-in configuration).
- The file in `-f` does not need to exist - FDA creates it on the first change.
- If the server stays red with "permission denied": `chmod +x ~/.vscode/extensions/tibco.flogo-2.26.*/bin/flogodesign-cli`.
- FDA prints a disclaimer box on start-up; Cline may log a few "parse" warnings for it. Harmless.
- The server should show **44 tools**.

## 1. Prompt 1 - picture to flow (attach `~/FlogoLab/lab2/leak-report-process.png` with Cline's **+** Add Files & Images button)

Paste exactly:

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

Dry run: 18 tool calls, 0 errors, ~32 s, ~125k input tokens (~US$0.26 on gpt-4.1).
Result: trigger on 9998, handler POST /leak-reports, StartActivity + 5 activities, parallel
split/join, property FieldService.URL, CreateWorkOrder Method=POST and URL=`$property["FieldService.URL"]`.

> Alternative (show-and-tell only): FDA's own built-in prompt **create-flogo-flow-from-picture**
> ("...Before creating the activities, list all the possible activity types... create the required
> schema's and connections... set all possible attributes"). In the dry run it ran out of steam: 60+ tool
> calls, 14 errors, ~930k input tokens (~US$1.90), port left at 9999, the URL put in the wrong field
> and wrong mapping paths (`$.reportId`). The guided prompt above is the one to use in class.

## 2. Finish in the Flogo designer (what FDA does not do)

Open `SW_LeakReport.flogo` (close and reopen it if it was already open while Cline edited it).

1. **Trigger handler** (click the REST trigger > LeakReportIntake handler):
   - *Output Settings > Request Schema* - paste:
     `{"reportId":"LR-1001","address":"12 Church St","suburb":"Parramatta","description":"Water bubbling up through the footpath","severity":"HIGH"}`
   - *Reply Settings > Reply data schema* - paste:
     `{"reportId":"LR-1001","workOrderRef":"WO-LR-1001","priority":"P1","status":"RECEIVED"}`
   - Map trigger output `body` to the flow input, flow output `code`/`data` to the reply.
2. **Delete the link CreateWorkOrder -> Reply201** if Prompt 2 left it (FDA's MCP `remove-link` is a no-op -
   known issue). If you forget, nothing breaks: Reply201 simply waits for all incoming branches.
3. **LogReport** message:
   `string.concat("Leak report ", $flow.body.reportId, " at ", $flow.body.address, ", ", $flow.body.suburb, " - severity ", $flow.body.severity)`
4. **BuildWorkOrder** (Mapper) - schema `{"workOrderRef":"","priority":"","location":""}` then:
   - workOrderRef = `string.concat("WO-", $flow.body.reportId)`
   - priority = `$flow.body.severity == "HIGH" ? "P1" : ($flow.body.severity == "MEDIUM" ? "P2" : "P3")`
   - location = `string.concat($flow.body.address, ", ", $flow.body.suburb)`
5. **CreateWorkOrder** - Request Schema `{"source":"","workOrderRef":"","reportId":"","location":"","description":"","priority":""}`,
   map source = `"flogo-leak-intake"`, workOrderRef/location/priority from `$activity[BuildWorkOrder].output`,
   reportId/description from `$flow.body`. Set **Response Type = text/plain** (needed if you point
   FieldService.URL at webhook.site, which answers text/plain).
6. **LogAudit** message:
   `string.concat("AUDIT leak-report ", $flow.body.reportId, " -> ", $activity[BuildWorkOrder].output.workOrderRef, " priority ", $activity[BuildWorkOrder].output.priority)`
7. **Reply201** (Return): code = `201`, data = reportId `$flow.body.reportId`, workOrderRef / priority from
   `$activity[BuildWorkOrder].output`, status = `"RECEIVED"`.

Also set app property **FieldService.URL** to your own webhook.site URL (from Lab 1) so you can see the work orders
arrive - Lab 3 relies on it.

Reference: `~/FlogoLab/solutions/Lab2_SW_LeakReport.flogo`.

## 3. Prompt 2 - modify the flow with AI

```
Add a Log activity named LogWorkOrderId after CreateWorkOrder that logs the work order id. Link CreateWorkOrder -> LogWorkOrderId -> Reply201 and remove the direct link CreateWorkOrder -> Reply201. Set the LogWorkOrderId message to =string.concat("Work order created: ", $activity[BuildWorkOrder].output.workOrderRef). Then format the flow again.
```

Dry run: 10 tool calls (~15 s, ~US$0.18). Activity, both new links and the message were set; the
`remove-link` call fails ("Link not found from New_activity to New_activity_2" - FDA ignores the
arguments), so delete that link in the designer (step 2.2 above).

## 4. Prompt 3 - ask FDA to explain

```
Use the explain tool to explain the Invoke REST activity (act_general_rest) and the string.concat function. Summarise each in 3 bullets for a BusinessWorks developer.
```

Dry run: 2 tool calls (`explain` x2), ~7 s, ~US$0.06.

## 5. Test

```bash
bash ~/FlogoLab/lab2/test-leak.sh
```

or by hand:

```bash
curl -s -X POST http://localhost:9998/leak-reports \
  -H "Content-Type: application/json" \
  -d '{"reportId":"LR-1001","address":"12 Church St","suburb":"Parramatta",
       "description":"Water bubbling up through the footpath","severity":"HIGH"}'; echo
```

Expected `201 {"reportId":"LR-1001","workOrderRef":"WO-LR-1001","priority":"P1","status":"RECEIVED"}`
(MEDIUM gives P2, anything else P3). App log shows LogReport, LogAudit and "Work order created: WO-LR-1001".
Keep this app: Lab 3 calls it as the `report_leak` MCP tool.

## Gotchas

- If Cline runs FDA `check-mappings`, it reports `TR_REST_NO_SWAGGER` ("runtime will panic"). That is a
  false positive for this trigger - the app runs fine. Tell Cline not to replace the REST trigger.
- FDA cannot create conditional / otherwise / error links, flow input-output from a REST trigger, or Return
  mappings reliably - that is designer work (Lab 1 skills).
- Each Cline turn re-sends the whole conversation, so big tool outputs (e.g. `list-activity-types`) make
  every later step expensive - name the activity types in the prompt instead.
