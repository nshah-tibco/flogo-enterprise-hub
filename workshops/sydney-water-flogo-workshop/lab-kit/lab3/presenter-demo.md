# Lab 3 presenter demo: FDA `create-mcp-skeleton` (about 3 minutes)

The point of the demo: **FDA turns an OpenAPI spec into a working MCP server in about 3 seconds. Making it safe
is the work you do in Lab 3.** Run it after Lab 1 and Lab 2 are up and before participants open the Lab 3 starter.

Verified on 2 Nov 2026 on Windows (bundled FDA 0.9.3, extension 2.26.7) and on Ubuntu (WSL2 Ubuntu 26.04; FDA
binary from the 2.26.8 Linux VSIX). The commands, the tool list and the calls below produced the same results on both.

## 0. Before you start
- Lab 1 (`SW_RainfallRisk`, port 9999) and Lab 2 (`SW_LeakReport`, port 9998) are running.
- The spec is in `~/FlogoLab/lab3/specs/sw-flogo-apis.openapi.json`. It is OpenAPI 3.0 with both operations:
  `POST /rainfall-risk/assessments` and `POST /leak-reports`.
- The skeleton listens on port **3040**, so it can run next to a participant's Lab 3 app on 9090.

## 1. Generate (terminal)
```bash
cd ~/FlogoLab/lab3/specs
FDA=$(ls -d ~/.vscode/extensions/tibco.flogo-2.26.*/bin/flogodesign-cli | tail -1)   # Linux build of the extension
F=SW_Water_MCP_Skeleton.flogo
rm -f $F
$FDA -f $F cp SW_Water_MCP_Skeleton "FDA create-mcp-skeleton demo over the Lab 1 and Lab 2 APIs"
$FDA -f $F csp SW_Flogo_APIs --specFile sw-flogo-apis.openapi.json
$FDA -f $F cms SW_Flogo_APIs --methodFilter POST
```
- Pass the spec with `--specFile`. Passing it inline fails with "not a valid OpenAPI definition".
- The output includes `DeprecationWarning: url.parse()` and `Ignoring method: SERVERS for resource ...`. Both are
  harmless.

## 2. The one fix it needs: a second base URL
FDA reads only the **first** `servers` URL (`http://localhost:9999`) and puts it in one app property, `API_Endpoint`.
It ignores the per-path `servers` entries, so out of the box `leak-reports-POST` would call Lab 1 on port 9999 instead of Lab 2.
Point that tool at Lab 2:
```bash
$FDA -f $F cap Lab2_Endpoint string http://localhost:9998
$FDA -f $F sa activity leak-reports_POST.Call_API.input.Uri Lab2_Endpoint -C app-property
```
To do the same in the designer: **App Properties**, add `Lab2_Endpoint` = `http://localhost:9998`. Then in flow
`leak-reports_POST`, open activity **Call_API** and set **URL** = `$property["Lab2_Endpoint"]`.

Generating two specs, one per API, is worse. The second `cms` adds a second MCP trigger (empty name, port 8080)
and still binds the tool to `API_Endpoint`.

## 3. Run it
Open `SW_Water_MCP_Skeleton.flogo` in VS Code and **Run**. It logs
`MCP HTTP Server [MCP Server for Sydney Water workshop Flogo APIs:1.0.0] reachable on [http://localhost:3040/mcp]`.
In Cline, add a second server entry `"sw-skeleton": {"type": "streamableHttp", "url": "http://localhost:3040/mcp"}`.
No key is needed.

You can also skip Cline and call it with curl:
```bash
U=http://localhost:3040/mcp; H=(-H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')
SID=$(curl -s -D - -o /dev/null "${H[@]}" -X POST $U --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"demo","version":"1"}}}' | tr -d '\r' | awk -F': ' 'tolower($1)=="mcp-session-id"{print $2}')
curl -s "${H[@]}" -H "Mcp-Session-Id: $SID" -X POST $U --data '{"jsonrpc":"2.0","method":"notifications/initialized"}'
curl -s "${H[@]}" -H "Mcp-Session-Id: $SID" -X POST $U --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
curl -s "${H[@]}" -H "Mcp-Session-Id: $SID" -X POST $U --data '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"leak-reports-POST","arguments":{"body":{"reportId":"LR-2002","address":"4 Smith St","suburb":"Burwood","severity":"URGENT","description":"Burst main - call me on 0412 345 678"}}}}'
```

## 4. What to point out (all observed in the dry run)
| | FDA skeleton (3 s) | Hand-built Lab 3 solution |
|---|---|---|
| Tools | `rainfall-risk-assessments-POST`, `leak-reports-POST` (named from path + method) | `assess_rainfall_risk`, `report_leak` |
| Descriptions | the spec `summary` only ("Log a water leak report") | full guidance: allowed values, ranges, what is returned |
| Arguments | nested under `body`. `required` and the spec's `enum` (severity) are dropped | flat, typed, described, required |
| Auth | none (`authType` None, port from `MCP_Port` = 3040) | API key (`Authorization: Bearer sw-workshop-key`) |
| Bad input | `severity URGENT` is accepted and Lab 2 creates a **P3** work order | `Rejected by guardrail: ...`, and Lab 2 is never called |
| PII | the phone number goes to Lab 2 unchanged, and `Log_Input` writes it to the log | masked to `[redacted]` before the POST |
| Output | the whole HTTP envelope: `statusCode`, response `headers`, `responseTimeInMilliSec`, `responseBody` | only the documented fields |
| Errors | a Lab 1 502 comes back as a normal result with `statusCode:502` inside (isError false) | `isError` with a clear message |
| Base URL | one per app (fix in step 2) | one property per API (`Lab1.AssessURL`, `Lab2.LeakReportURL`) |

Close with: "The skeleton is a good first draft, and it is what you get by default. Lab 3 makes it safe: auth, input
validation, PII masking and least privilege."

## Reset
Stop the app and delete `SW_Water_MCP_Skeleton.flogo` (step 1 also runs `rm -f`).
