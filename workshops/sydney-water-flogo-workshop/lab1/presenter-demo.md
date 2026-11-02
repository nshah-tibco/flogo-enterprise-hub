# Presenter demo — a REST service from an API spec (FDA `create-api-skeleton`)

Part 1 of the three-step story:

| Step | Input | FDA command | Result |
|---|---|---|---|
| **1 · REST service from an API spec** (this file) | `lab1/specs/rainfall-risk-api.openapi.json` | `create-api-skeleton` (`cas`) | REST trigger + handler + flow on port 9999, in ~2 s |
| 2 · REST service from a process diagram | `lab2/leak-report-process.png` | Cline + FDA (picture → flow) | Lab 2, see `lab2/prompts.md` |
| 3 · MCP server from an API spec | `lab3/specs/sw-flogo-apis.openapi.json` | `create-mcp-skeleton` (`cms`) | MCP tools over Lab 1 + Lab 2, see `lab3/presenter-demo.md` |

The point: **the contract (OpenAPI) becomes a running Flogo REST service in seconds; you spend your time on the
integration logic, not the plumbing.** Lab 1 then adds that logic (Open-Meteo call, risk rating, work order, 502).

## 0. Before you start
- The spec is `~/FlogoLab/lab1/specs/rainfall-risk-api.openapi.json` (OpenAPI 3.0.3, `POST /rainfall-risk/assessments`,
  request `{siteId, siteName, latitude, longitude, forecastDays}`, response `{siteId, siteName, riskLevel,
  totalRainfallMm, inspectionRequested, message}`).
- The generated service listens on **port 9999** (taken from the spec's server URL). **Stop the Lab 1 app first**, or
  change the port after generating (REST trigger → **Port**).

## 1. Generate (terminal, ~2 s)
```bash
mkdir -p ~/FlogoLab/demo && cd ~/FlogoLab/demo
FDA=$(ls -d ~/.vscode/extensions/tibco.flogo-2.26.*/bin/flogodesign-cli | tail -1)
F=SW_RainfallRisk_FromSpec.flogo
rm -f $F
$FDA -f $F cp SW_RainfallRisk_FromSpec "REST service generated from the Rainfall Risk API spec"
$FDA -f $F csp RainfallRiskAPI --specFile ../lab1/specs/rainfall-risk-api.openapi.json
$FDA -f $F cas RainfallRiskAPI logReply
$FDA -f $F cm          # validation: all rules pass
```
- Pass the spec with `--specFile` (inline JSON is rejected as "not a valid OpenAPI definition").
- `logReply` gives each operation a flow **Log → Configure HTTP Response → Return**; `none` gives empty flows.
- A `DeprecationWarning: url.parse()` line in the output is harmless.

## 2. Show it (designer)
Open `~/FlogoLab/demo/SW_RainfallRisk_FromSpec.flogo`:
- **REST trigger** `Sydney_Water_Rainfall_Risk_API`, port 9999, **POST /rainfall-risk/assessments**, request and
  response schemas imported from the spec (the API Spec is attached on the trigger).
- **Flow** `assessRainfallRisk_POST`: `Log_API` → `ConfigureHTTPResponse` → `Return`.

Run it (**Flogo** app view → **Run as Executable**) and call it:
```bash
curl -s -i -X POST http://localhost:9999/rainfall-risk/assessments \
  -H "Content-Type: application/json" --data @$HOME/FlogoLab/lab1/parramatta-3day.json
```
It answers with the contract's shape but no business logic yet: that is what Lab 1 builds.

## 3. Same thing from Cline (FDA skills)
With the FDA skills set up (`bash ~/FlogoLab/cline/setup-flogo-skills.sh`, see `lab1/prompts-fda-skills.md`):
```
Using the fda skill, create a new Flogo app ~/FlogoLab/demo/SW_RainfallRisk_FromSpec.flogo from the OpenAPI spec
~/FlogoLab/lab1/specs/rainfall-risk-api.openapi.json: create the project, add the spec with --specFile, then run
create-api-skeleton with the logReply skeleton. Validate with fda cm and summarise the trigger, port, path and flow
that were generated.
```
To go further, the full Lab 1 logic from a prompt is in `lab1/prompts-fda-skills.md` (tested with gpt-4.1).

## Verified (3 Nov 2026, FDA in Flogo extension 2.26.7)
Generated in ~2 s; `fda cm` all rules pass; designer lint (no settings expressions / password / `$error` issues)
clean; builds with flogobuild; the engine starts the trigger on 9999. The live call was not re-run on 3 Nov (port 9999
was in use by a running Lab 1 app).
