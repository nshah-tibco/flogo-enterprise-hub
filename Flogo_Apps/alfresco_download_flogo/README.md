# Alfresco Download Interface (TIBCO Flogo)

Flogo implementation of the **Oracle → Alfresco Download** interface, built from
`TDD_Flogo_Alfresco_Download.docx`. Oracle POSTs an `InvoiceId` + Alfresco `File_URL`;
the app extracts the SpacesStore NodeRef, downloads the document from Alfresco over
HTTP GET with Basic Auth, and returns the file as **Base64** in a synchronous response,
with structured error handling and logging.

> **SOAP → REST/JSON:** Flogo does not support SOAP/WSDL/XSD. Per the TDD (§3.1, §4.2/4.3)
> this app implements the **REST/JSON equivalent** the document explicitly provides.

## Interface

| | |
|---|---|
| Trigger | REST (`tr_rest`), `POST /alfresco/download`, port `server.port` (8068) |
| Request | `{ "Doc_Details": [ { "File_URL": "...", "InvoiceId": "..." } ] }` (first entry only) |
| Response | `{ "RunType": "", "FileData": [ { "Filename", "InvoiceId", "FileContent(base64)" } ], "StatusCode", "StatusDescription" }` |

### Success response
```json
{ "RunType": "", "FileData": [ { "Filename": "invoice.pdf", "InvoiceId": "INV123456",
  "FileContent": "<base64>" } ], "StatusCode": "SUCCESS",
  "StatusDescription": "Document downloaded successfully" }
```
### Error response
```json
{ "RunType": "", "StatusCode": "ERROR", "StatusDescription": "<detail>" }
```

## Flow design (`MainFlow`)

Single flow (the BW two-process design is consolidated; see *Deviations*). Branches:

```
LogTxnStart → DeriveNodeRef ─┬─[valid]──→ CallAlfresco ─┬─[status 200]─→ BuildSuccessResponse → LogTxnEnd → ReturnSuccess
                             │                           ├─[status !=200]→ BuildAlfrescoError  → LogAlfrescoError  → ReturnAlfrescoError
                             │                           └─[error/timeout]→ BuildTransportError → LogTransportError → ReturnTransportError
                             └─[invalid]→ BuildValidationError → LogValidationError → ReturnValidationError
```

- **DeriveNodeRef** – reads the first `Doc_Details` entry via `json.get(coerce.toObject(array.get($flow.body.Doc_Details, 0)), "…")` (NOT `json.path("$.…")` — the VSCode designer rewrites `$.` to `$flow.` and breaks it); `NodeRefId = string.substringAfter(File_URL, "SpacesStore/")`.
- **Validation** – proceeds only if `File_URL` contains `SpacesStore/` **and** the derived NodeRef is non-empty; otherwise returns `ERROR – Invalid or missing File_URL` **without calling Alfresco**.
- **CallAlfresco** – `http_client` (Data mode) HTTP GET. `settings.host` = `=$property["Alfresco_ServiceEndpoint"]` (a **single** property — settings cannot hold expressions in the designer) whose value carries a `{nodeRef}` placeholder substituted at runtime from `input.pathParams`. Basic Auth header built from `Alfresco_Username`/`Alfresco_Password`.
- **BuildSuccessResponse** – `FileContent = string.stringToBase64(responseBody)`; `Filename` parsed from the `Content-Disposition` response header; `InvoiceId` from the request.

## App properties (§8)

| Property | Default | Notes |
|---|---|---|
| `server.port` | `8068` | inbound listener port |
| `server.host` | `localhost` | |
| `LogLevel` | `DEBUG` | |
| `Alfresco_ServiceEndpoint` | `http://alfrescocontint:8080/alfresco/service/trafigura/1_3/contentRetrieve/workspace/SpacesStore/{nodeRef}` | full endpoint; `{nodeRef}` substituted at runtime. Combines the TDD's Hostname/Port/RequestURI (a Flogo **setting** field takes only a literal or one property, not a `concat` expression). |
| `SocketTimeout` | `1000` | used as retry interval |
| `ConnectionTimeout` | `30000` | HTTP client timeout |
| `Retry_Count` | `3` | retry config (see limitation below) |
| `Alfresco_Username` | `SVC.ofcs.qa` | renamed from `Username` — see note |
| `Alfresco_Password` | `changeit` | store as secret / env var in real deployments |

> **Property naming:** the TDD uses `/AlfrescoConnections/…` names. Flogo property names
> cannot contain `/`, so dot/flat names are used. `Username`/`Password` were renamed to
> `Alfresco_Username`/`Alfresco_Password` because the bare name `Username` collides with the
> OS `USERNAME` environment variable under the env property resolver.

## Build

Context matches the installed Flogo VS Code extension (2.26.5-ENGR-001).

```bash
# from builds/ (relative -f avoids an absolute-path bug in flogobuild -o)
flogobuild build-exe -f ../alfresco_download_flogo.flogo -c flogo-2265-eb01                       # local
flogobuild build-exe -f ../alfresco_download_flogo.flogo -c flogo-2265-eb01 -p linux/amd64 -n alfresco_download_flogo_linux
```

Prebuilt: `builds/alfresco_download_flogo_win.exe`, `builds/alfresco_download_flogo_linux`.

## Run

App-property values can be overridden by environment variables via the env resolver:

```bash
export FLOGO_APP_PROPS_ENV=auto
export Alfresco_ServiceEndpoint='http://alfrescocontint:8080/alfresco/service/trafigura/1_3/contentRetrieve/workspace/SpacesStore/{nodeRef}'
export Alfresco_Username=SVC.ofcs.qa Alfresco_Password='<secret>'
./alfresco_download_flogo_linux         # listens on :8068
```

## Verified scenarios (mock Alfresco)

| Scenario | Result |
|---|---|
| Valid URL, document exists | `SUCCESS`, correct Base64, `Filename` from Content-Disposition |
| **True binary** (all bytes 0x00–0xFF) | Base64 round-trips **exactly** (lossless) |
| Alfresco 404 | `ERROR` (no retry) |
| Alfresco 401 (bad creds) | `ERROR` (no retry) |
| Connection refused / host down | `ERROR – Alfresco unavailable` |
| Malformed URL (no `SpacesStore/`) | `ERROR – Invalid or missing File_URL`, no Alfresco call |
| Empty `File_URL` | `ERROR – Invalid or missing File_URL`, no Alfresco call |

## Known limitations / notes

1. **Automatic retry is not active.** The download must use the `http_client` activity
   (the `rest` activity force-parses responses as JSON and cannot return binary). In this
   Flogo version `http_client` does **not** honour `settings.retryOnError`, so transient
   failures are **not** auto-retried. The `Retry_Count`/`SocketTimeout` retry config is left
   in place (forward-compatible) but does not currently fire. Connection failures still return
   a clean structured `ERROR`. A production enhancement would add an explicit retry loop.
2. **Base64 fidelity** (TDD Open Item #8) is **solved** — verified lossless for arbitrary binary.
3. **Error `FileData`** is omitted (rather than `[]`) in error responses — cosmetic only.
4. **HTTP inbound.** Enforce HTTPS at the load balancer/infra for production (TDD §11).

### VSCode Flogo designer compatibility

The app is authored to survive a round-trip through the VSCode Flogo designer. Two designer
behaviours were hit and worked around (opening an older version can re-introduce them):
- **Settings fields take only a literal or a single `$property`** — not a `concat` expression.
  The designer silently blanks an expression in `settings.host` ("Service Endpoint is required").
  Fixed by using one `Alfresco_ServiceEndpoint` property with a `{nodeRef}` placeholder.
- **The designer rewrites `$.` → `$flow.` inside `json.path("$.…")` strings**, corrupting them
  (`key error: flow not found`). Body fields are read with `json.get(coerce.toObject(array.get(...)))`
  instead — no `$.` string, no `[N]` indexing, no `.field` on a function result (none of which compile/survive).
- Mapper output schemas are declared (e.g. `DeriveNodeRef`) so the designer can resolve
  `$activity[…].output.*` references (otherwise Input tabs show validation errors).

## Deviations from the BW reference

- SOAP/XML → REST/JSON (Flogo has no SOAP; TDD-sanctioned).
- Two BW processes → one Flogo flow.
- `IdentityProvider` Basic Auth → Authorization header built from app properties.
- `.substvar` → Flogo app properties (overridable via env).
