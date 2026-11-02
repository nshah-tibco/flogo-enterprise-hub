# Lab 1 - build SW_RainfallRisk with Cline + the FDA skills (gpt-4.1)

This is the "describe it, let the agent build it" variant of Lab 1. Cline uses the **fda** and **fda-mapping**
skills to drive the Flogo Design Assistant command line (`fda`) and builds the whole app
`~/FlogoLab/lab1/SW_RainfallRisk.flogo`: REST trigger on port 9999, Open-Meteo call, risk mapper, conditional
Field Service ticket, 502 error branch and the four app properties. You then open it in the designer and run it.

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
Use the fda and fda-mapping skills to build a new Flogo app from scratch: ~/FlogoLab/lab1/SW_RainfallRisk.flogo (app name SW_RainfallRisk). It is a Rainfall Risk API for Sydney Water pumping stations.

App properties:
- Weather.URL (string) = https://api.open-meteo.com/v1/forecast
- FieldService.URL (string) = https://postman-echo.com/post
- Risk.HighMm (number) = 25
- Risk.MediumMm (number) = 5

Trigger: REST trigger ReceiveHTTPMessage (tr_rest) on port 9999, handler POST /rainfall-risk/assessments for flow AssessRainfallRisk.
- Request body sample: {"siteId":"PS-102","siteName":"Parramatta Sewage Pumping Station SP0102","latitude":-33.815,"longitude":151.001,"forecastDays":3} (latitude/longitude number, forecastDays integer)
- Reply data sample: {"siteId":"PS-102","siteName":"Parramatta ...","totalRainfallMm":19.2,"riskLevel":"MEDIUM","inspectionRequested":true,"message":"..."} (totalRainfallMm number, inspectionRequested boolean)
- Flow inputs headers and body; flow outputs code (integer) and data (object).

Flow AssessRainfallRisk, activities (keep the StartActivity that fda cf adds):
1. LogRequest (Log): message = string.concat("Rainfall risk request for site ", $flow.body.siteId, " - ", $flow.body.siteName)
2. GetForecast (Invoke REST): GET, URL = app property Weather.URL, Throw Error = true. Query params: latitude (number) = $flow.body.latitude, longitude (number) = $flow.body.longitude, daily (string) = literal precipitation_sum,precipitation_probability_max, timezone (string) = literal Australia/Sydney, forecast_days (integer) = $flow.body.forecastDays. Response schema sample: {"daily":{"time":["2026-11-03"],"precipitation_sum":[1.5],"precipitation_probability_max":[40]}}
3. BuildAssessment (Mapper) with fields totalRainfallMm (number), riskLevel (string), assessedAt (string):
   - totalRainfallMm = array.sum($activity[GetForecast].responseBody.daily.precipitation_sum)
   - riskLevel = array.sum($activity[GetForecast].responseBody.daily.precipitation_sum) >= $property["Risk.HighMm"] ? "HIGH" : (array.sum($activity[GetForecast].responseBody.daily.precipitation_sum) >= $property["Risk.MediumMm"] ? "MEDIUM" : "LOW")
   - assessedAt = datetime.now()
4. CreateInspection (Invoke REST): POST, URL = app property FieldService.URL, Response Type text/plain. JSON body {source, siteId, siteName, priority, reason, totalRainfallMm (number), requestedAt}: source = literal flogo-rainfall-risk, siteId/siteName from $flow.body, priority = $activity[BuildAssessment].output.riskLevel, reason = string.concat("Forecast rainfall ", coerce.toString($activity[BuildAssessment].output.totalRainfallMm), " mm over ", coerce.toString($flow.body.forecastDays), " days - ", $activity[BuildAssessment].output.riskLevel, " overflow/inflow risk"), totalRainfallMm = $activity[BuildAssessment].output.totalRainfallMm, requestedAt = $activity[BuildAssessment].output.assessedAt.
5. ReturnTicketed (Return): code 200; data siteId, siteName from $flow.body, totalRainfallMm and riskLevel from $activity[BuildAssessment].output, inspectionRequested = true, message = string.concat("Inspection requested in Field Service (HTTP ", coerce.toString($activity[CreateInspection].statusCode), ")")
6. ReturnNoAction (Return): code 200; same data as ReturnTicketed but inspectionRequested = false and message = literal Rainfall risk LOW - no inspection needed
7. ReturnError (Return): code 502; data siteId, siteName from $flow.body, riskLevel = literal UNKNOWN, inspectionRequested = false, message = string.concat("Weather service unavailable: ", $error[GetForecast].message)

Links - exactly these 7 (add every activity with --doNotLink, then make each link with fda-link):
- StartActivity -> LogRequest (success)
- LogRequest -> GetForecast (success)
- GetForecast -> BuildAssessment (success)
- BuildAssessment -> CreateInspection: success with condition $activity[BuildAssessment].output.riskLevel != "LOW"
- BuildAssessment -> ReturnNoAction: success with no matching condition (exprOtherwise)
- CreateInspection -> ReturnTicketed (success)
- GetForecast -> ReturnError: error link

Designer rules: URLs are one whole app property (never string.concat), the error branch uses $error[GetForecast].message, and expressions in mappings start with =.
When done, show me the links (fda-link with just the file and flow), run fda cm and the validator, and summarise anything I still need to finish in the Flogo designer.
```

## What to expect

- Cline loads the `fda` and `fda-mapping` skills, runs `fda version`, then about **80 terminal commands**, almost
  all `~/FlogoLab/cline/tools/fda ...` (create project, properties, trigger, schemas, activities, mappings) and
  `~/FlogoLab/cline/tools/fda-link ...` (links and their types). It ends with `fda cm`, the validator and a summary.
- Time **4-5 minutes** with auto-approve. Cost about **US$1.2-1.4** at gpt-4.1 list price (78-86 model turns;
  most input tokens are cached).
- `fda cm` reports one error, `TR_REST_NO_SWAGGER`. That is a known false positive for a REST trigger without an
  API spec; the app runs. Cline is told to ignore it.

## Finish and check in the designer

1. Open `~/FlogoLab/lab1/SW_RainfallRisk.flogo` in the Flogo designer. fda does not lay out the flow, so the
   activities may sit on top of each other: drag them apart (StartActivity, LogRequest, GetForecast,
   BuildAssessment, then CreateInspection -> ReturnTicketed on the condition branch, ReturnNoAction on the
   otherwise branch, ReturnError on the error branch).
2. Click through and check there is no red error:
   - Trigger: port 9999, POST `/rainfall-risk/assessments`, Request and Reply schemas shown.
   - GetForecast: URL bound to `Weather.URL`, 5 query parameters mapped, **Throw Error** on.
   - CreateInspection: URL bound to `FieldService.URL`, **Response Type text/plain**, body mapped.
   - Link from BuildAssessment to CreateInspection is *Success with condition*
     `$activity[BuildAssessment].output.riskLevel != "LOW"`; to ReturnNoAction *Success with no matching
     condition*; GetForecast to ReturnError is an *Error* link and ReturnError uses `$error[GetForecast].message`.
3. Save, then **Run as Executable** (port 9999).

## Test

```bash
bash ~/FlogoLab/lab1/sample-requests.sh        # forecastDays 1, 3 and 7 for PS-102
```

Force a ticket on a dry day: set app property `Risk.MediumMm` to `0` and run again. Error branch: set
`Weather.URL` to `https://api.open-meteo.invalid/v1/forecast`; the reply is **502** with
`"riskLevel":"UNKNOWN"` and `"message":"Weather service unavailable: ..."`.

## How this prompt was verified (2 Nov 2026)

gpt-4.1 in a Cline emulator (`_build/cline_skills_harness.py`: Cline-style system prompt, these rules, skills
loaded on demand, one tool per turn) built the app from an empty workspace; then `fda cm`, `designer_lint.py`,
`validate_flogo_apps.py`, a `flogobuild` build and live calls (LOW / ticket via a text/plain Field Service stand-in /
forced LOW / 502) all passed in runs 2, 3 and 4 (run 4 = this prompt with the final rules file, 38/38 checks). Transcripts: `verification/cline-skills/lab1-run*.md`.
Not verified: opening the generated file in the VS Code designer UI and running Cline itself on Ubuntu.
