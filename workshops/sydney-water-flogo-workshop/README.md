# TIBCO Flogo® Hands-on Workshop — Sydney Water

Build integration APIs in Flogo by hand and with AI, then expose them to an AI agent as MCP tools with guardrails.

## How the session runs

| # | Part | Who | Where |
|---|---|---|---|
| 1 | **Demo** of all three labs: API spec → REST service, process diagram → REST service (AI), API spec → MCP server + guardrails | Presenter | `lab1/`, `lab2/`, `lab3/` `presenter-demo.md` |
| 2 | **Lab 0 — Hello Flogo**: timer trigger + log, by hand (~10 min) | You | [`lab0/README.md`](lab0/README.md) |
| 3 | **Lab 1 — Rainfall Risk API from its spec**, by hand (~15 min) | You | [`lab1/README.md`](lab1/README.md) part A |
| 4 | **Run all three solutions** and test them with curl | You | [`lab1`](lab1/README.md) part B, [`lab2`](lab2/README.md), [`lab3`](lab3/README.md) |
| 5 | **Ask the AI agent** (Cline) to use your MCP tools, then try to break the guardrails | You | [`lab3/README.md`](lab3/README.md) |

## Setup (once, ~5 min)

```bash
git clone -b sydney-water-workshop https://github.com/nshah-tibco/flogo-enterprise-hub.git ~/flogo-enterprise-hub
```

1. VS Code → **File → Open Folder…** → `~/flogo-enterprise-hub/workshops/sydney-water-flogo-workshop`
   (trust the authors if asked).
2. **Terminal → New Terminal** (`Ctrl+Shift+`` ` ``), then:
   ```bash
   bash setup.sh
   ```
   It points `~/FlogoLab` at this folder, adds the workshop MCP servers to Cline, and checks the prerequisites
   (VS Code, Flogo extension 2.26.x, Go 1.25.7+, curl, python3, network, free ports 9999 / 9998 / 9090).
   All **PASS** (a WARN is fine) → carry on. Any **FAIL** → raise a hand.
3. **Cline** (needed for step 5): Extensions (`Ctrl+Shift+X`) → search **Cline** → Install → *Bring my own API key*
   → API Provider **OpenAI** → paste the workshop key (handed out on the day) → model **gpt-4.1** → mode **Act**.

## The labs at a glance

| Lab | App | Port | API spec | Test from a terminal |
|---|---|---|---|---|
| 0 | `HelloFlogo` — Timer → Log | – | – | watch the terminal: a greeting every 10 s |
| 1 | `SW_RainfallRisk_FromSpec` (you build) / `SW_RainfallRisk` (solution) | 9999 | [`lab1/specs/rainfall-risk-api.openapi.json`](lab1/specs/rainfall-risk-api.openapi.json) | `bash lab1/sample-requests.sh` |
| 2 | `SW_LeakReport` (solution) | 9998 | [`lab2/specs/leak-report-api.openapi.json`](lab2/specs/leak-report-api.openapi.json) | `bash lab2/test-leak.sh` |
| 3 | `SW_Water_MCP` (solution) / starter | 9090 | tools: [`lab3/specs/sw-water-mcp-tools.json`](lab3/specs/sw-water-mcp-tools.json) · backend APIs: [`lab3/specs/sw-flogo-apis.openapi.json`](lab3/specs/sw-flogo-apis.openapi.json) | `bash lab3/test-mcp.sh` |

Solutions for every lab are in [`solutions/`](solutions/): open one, then **Flogo** app view → **Run as Executable**.
Only one app per port at a time — stop your Lab 1 app before running the Lab 1 solution.

## curl cheat sheet (no Postman needed)

```bash
# Lab 1 - Rainfall Risk (port 9999)
curl -s -X POST http://localhost:9999/rainfall-risk/assessments -H "Content-Type: application/json" \
  -d '{"siteId":"PS-102","siteName":"Parramatta Sewage Pumping Station SP0102","latitude":-33.815,"longitude":151.001,"forecastDays":3}'

# Lab 2 - Leak report (port 9998) -> 201 {"priority":"P1","reportId":"LR-1001","status":"RECEIVED","workOrderRef":"WO-LR-1001"}
curl -s -i -X POST http://localhost:9998/leak-reports -H "Content-Type: application/json" \
  -d '{"reportId":"LR-1001","address":"12 Church St","suburb":"Parramatta","description":"Water bubbling up through the footpath","severity":"HIGH"}'

# Lab 3 - MCP server (port 9090): see lab3/README.md "Query it with curl" (initialize -> tools/list -> tools/call)
```

Add `-i` to see the HTTP status line, `| python3 -m json.tool` to pretty-print JSON.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `curl: (7) Failed to connect … port 9999/9998/9090` | That app is not running: open it, **Run as Executable**, wait for "Started" in its terminal |
| App won't start: `bind: address already in use` | Another app holds the port: stop it (`fuser -k 9999/tcp`) |
| Lab 3 tool returns `… (Lab 1) failed` / `(Lab 2) failed` | Lab 1 or Lab 2 is not running |
| Lab 3 curl/agent gets HTTP 401 | Solution app needs `Authorization: Bearer sw-workshop-key` (the Cline settings from `setup.sh` already send it) |
| `sw-water-mcp` red in Cline | Lab 3 app not running yet, or restart the server in Cline's MCP panel / reload VS Code |
| `flogo-fda-lab2` red in Cline | Run `bash setup.sh` again, then reload VS Code |
| Cline searches files / guesses tool names (e.g. `log_leak_report`) instead of calling `report_leak` | `sw-water-mcp` is not in **Cline's** MCP settings: run `bash setup.sh`, reload VS Code, check it is green with two tools, start a new task. Servers added with VS Code's own **MCP: Add Server** are for Copilot Chat, not Cline |
| VS Code: "MCP Server Definition … wants to authenticate to localhost:9090", then `/authorize` → 404 | The server was added to VS Code's MCP config without the Bearer header, so VS Code tried OAuth. Click **Cancel** and use Cline (or add `"headers": {"Authorization": "Bearer sw-workshop-key"}` to the VS Code entry) |
| Lab 1 always LOW | Live weather; set `Risk.MediumMm` = `0` in APP PROPERTIES to force a ticket |

## More

- `~/FlogoLab` in the guide and prompts is a shortcut to this folder (created by `setup.sh`).
- Full step-by-step guide, incl. building Labs 2 and 3 yourself: [`guide/SydneyWater_Flogo_Workshop_Guide.pdf`](guide/SydneyWater_Flogo_Workshop_Guide.pdf) (reference).
- Build each app from a prompt with Cline + the FDA skills: `lab1/`, `lab2/`, `lab3/` `prompts-fda-skills.md` (optional).
- Apps run in non-production mode (stop after 24 h) without a Flogo licence — fine for the workshop.
- The Flogo Design Assistant is a Tech Preview: always review what it generates.
- More samples, MCP and agentic AI examples and the full skills library are in this repository (`samples/`, `skills-library/`).
