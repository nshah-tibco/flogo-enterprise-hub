# Lab 2 - build SW_LeakReport from a prompt (Cline + the FDA skills, gpt-4.1)

The "build it from a prompt instead of a picture" variant of Lab 2. Cline uses the **fda** and **fda-mapping**
skills (the Flogo Design Assistant command line, not the FDA MCP server) to build the complete app
`~/FlogoLab/lab2/SW_LeakReport.flogo`: REST POST `/leak-reports` on port 9998, LogReport, BuildWorkOrder
(severity -> P1/P2/P3, `WO-` + reportId), CreateWorkOrder and LogAudit in parallel, joined at Reply201
`201 {reportId, workOrderRef, priority, status:"RECEIVED"}`. Unlike the picture variant, the schemas and mappings
are built too.

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

## The prompt (paste as one message)

```text
Use the fda and fda-mapping skills to build a new Flogo app from scratch: ~/FlogoLab/lab2/SW_LeakReport.flogo (app name SW_LeakReport). It takes leak reports from residents and raises a work order in our Field Service SaaS.

App property: FieldService.URL (string) = https://postman-echo.com/post

Trigger: REST trigger ReceiveHTTPMessage (tr_rest) on port 9998, handler POST /leak-reports for flow LeakReportIntake.
- Request body sample: {"reportId":"LR-1001","address":"12 Church St","suburb":"Parramatta","description":"Water bubbling up through the footpath","severity":"HIGH"} (all strings)
- Reply data sample: {"reportId":"LR-1001","workOrderRef":"WO-LR-1001","priority":"P1","status":"RECEIVED"} (all strings)
- Flow inputs headers and body; flow outputs code (integer) and data (object).

Flow LeakReportIntake:
1. LogReport (Log): message = string.concat("Leak report ", $flow.body.reportId, " at ", $flow.body.address, ", ", $flow.body.suburb, " - severity ", $flow.body.severity)
2. BuildWorkOrder (Mapper) with string fields workOrderRef, priority, location:
   - workOrderRef = string.concat("WO-", $flow.body.reportId)
   - priority = $flow.body.severity == "HIGH" ? "P1" : ($flow.body.severity == "MEDIUM" ? "P2" : "P3")
   - location = string.concat($flow.body.address, ", ", $flow.body.suburb)
3. Two parallel paths out of BuildWorkOrder:
   a. CreateWorkOrder (Invoke REST): POST, URL = app property FieldService.URL, Response Type text/plain. JSON body {source, workOrderRef, reportId, location, description, priority}: source = literal flogo-leak-intake, workOrderRef / location / priority from $activity[BuildWorkOrder].output, reportId and description from $flow.body.
   b. LogAudit (Log): message = string.concat("AUDIT leak-report ", $flow.body.reportId, " -> ", $activity[BuildWorkOrder].output.workOrderRef, " priority ", $activity[BuildWorkOrder].output.priority)
4. Reply201 (Return): code 201; data reportId = $flow.body.reportId, workOrderRef and priority from $activity[BuildWorkOrder].output, status = literal RECEIVED.

Links - exactly these 6 plain success links (add every activity with --doNotLink, then make each link with fda-link):
- StartActivity -> LogReport
- LogReport -> BuildWorkOrder
- BuildWorkOrder -> CreateWorkOrder
- BuildWorkOrder -> LogAudit
- CreateWorkOrder -> Reply201
- LogAudit -> Reply201

Designer rules: the URL is one whole app property (never string.concat), and expressions in mappings start with =.
When done, show me the links (fda-link with just the file and flow), run fda cm and the validator, and summarise anything I still need to finish in the Flogo designer.
```

## What to expect

- Cline loads `fda` and `fda-mapping`, then runs about **50 terminal commands** (`fda ...` and `fda-link ...`),
  `fda cm`, the validator and a summary.
- Time about **3 minutes** with auto-approve. Cost about **US$0.75** at gpt-4.1 list price (48-59 model turns).
- `fda cm` reports only `TR_REST_NO_SWAGGER` (known false positive for a REST trigger without a spec).

## Finish and check in the designer

1. Open `~/FlogoLab/lab2/SW_LeakReport.flogo`. Drag the activities apart if they overlap (fda does not lay out the
   flow): StartActivity -> LogReport -> BuildWorkOrder, then CreateWorkOrder and LogAudit side by side, both into
   Reply201.
2. Check: trigger port **9998**, POST `/leak-reports`, Request/Reply schemas; CreateWorkOrder URL bound to
   `FieldService.URL`, Method POST, **Response Type text/plain**, body mapped; Reply201 code 201 and the 4 data
   fields; no red errors.
3. Save, then **Run as Executable**.

## Test

```bash
bash ~/FlogoLab/lab2/test-leak.sh               # 3 calls: HIGH -> P1, MEDIUM -> P2, LOW -> P3, all 201
```

To see the work order arrive at the "Field Service SaaS", set app property `FieldService.URL` to your
`https://webhook.site/<id>` URL and run the test again.

## Optional follow-up prompt (not run in the verification)

```text
Add a Log activity named LogWorkOrderId to the LeakReportIntake flow in ~/FlogoLab/lab2/SW_LeakReport.flogo, between CreateWorkOrder and Reply201 (delete the link CreateWorkOrder -> Reply201 with fda rl, then link CreateWorkOrder -> LogWorkOrderId -> Reply201 with fda-link). Its message is string.concat("Work order created: ", $activity[BuildWorkOrder].output.workOrderRef). Then run fda cm and the validator.
```

## How this prompt was verified (2 Nov 2026)

gpt-4.1 in the Cline emulator (`_build/cline_skills_harness.py`) built the app from an empty workspace; `fda cm`,
`designer_lint.py`, `validate_flogo_apps.py`, a `flogobuild` build, `test-leak.sh` (201 + P1/P2/P3) and a
text/plain Field Service stand-in receiving the work order all passed in each of runs 1-4 (runs 3 and 4 are
this exact prompt; run 4 with the final rules file, 24/24 checks). Transcripts: `verification/cline-skills/lab2-run*.md`. Not verified: the designer UI, Cline on
Ubuntu.
