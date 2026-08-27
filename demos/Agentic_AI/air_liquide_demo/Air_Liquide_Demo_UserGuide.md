# Air Liquide — Smart Operations AI Demo

An end-to-end demo showing how **TIBCO BusinessWorks 6 (BW 6.12)** can power an
AI assistant. A single-page web app (`demo.html`) talks to three BW6
applications through two AI patterns:

1. **Agentic tool-calling over MCP** — an LLM decides when to call live BW6 REST
   operations that are auto-exposed as **MCP tools** (Model Context Protocol).
2. **Retrieval-Augmented Generation (RAG)** — upload technical documents, then
   ask grounded natural-language questions (with optional image input), answered
   by BW6's built-in RAG activities.

The story it tells a customer: *"BW6 turns your existing REST/integration assets
into AI-callable tools and a document knowledge base — with almost no glue
code."*

---

## 1. What the use case does

The scenario is a gas-cylinder logistics operation ("Smart Cylinder
Operations"). The UI has two tabs:

### Tab 1 — Smart Cylinder Operations (MCP / agentic)
You chat with an AI assistant about gas-cylinder inventory. The LLM
(OpenAI `gpt-5.5`) is given three tools and calls them autonomously:

| Tool (LLM function) | BW6 REST operation | What it does |
|---|---|---|
| `searchGasStock` | `GET /cylinders/search` | Find cylinders by gas type + yard location |
| `getCylinderStatus` | `GET /cylinders/{id}` | Live pressure, purity, cert-expiry for one cylinder |
| `dispatchCylinder` | `POST /cylinders/{id}/dispatch` | Mark a cylinder *In-Transit* to a destination |

Example: ask *"What is the pressure and certification status of AL-ARG-9082?"*
→ the model calls `getCylinderStatus` → the BW6 app returns the record → the
model writes a natural-language answer citing the real figures.

The cylinder inventory is **mock data hardcoded inside the BW6 process** (no
database required). Four cylinders ship with the demo:

| Cylinder ID | Gas | Purity | Pressure | Volume | Location | Status | Cert. Expiry |
|---|---|---|---|---|---|---|---|
| `AL-ARG-9082` | Argon | 5.0 (99.999%) | 200 bar | 50 L | Houston Yard B | Available | 2026-12-31 |
| `AL-NIT-4011` | Nitrogen | Cryo-Grade (99.99%) | 180 bar | 50 L | Houston Yard A | Available | 2026-11-15 |
| `AL-OXY-1022` | Oxygen | Medical Grade (99.5%) | 150 bar | 40 L | Dallas Distribution Center | Reserved | 2026-09-30 |
| `AL-HYD-7730` | Hydrogen | Ultra-Pure (99.9999%) | 220 bar | 50 L | Houston Yard B | In-Transit | 2027-03-31 |

### Tab 2 — AI Document Assistant (RAG)
- **Upload** manuals, safety data sheets, certificates, etc. BW6 saves each
  file, chunks it, and ingests the chunks into a local vector store.
- **Ask** questions in natural language (optionally attaching an image). BW6
  retrieves the most relevant chunks and asks the LLM to answer using them.

---

## 2. Architecture

```
                         ┌────────────────────────────────────────────┐
                         │              demo.html (browser)            │
                         │   Tab 1: MCP agentic chat  Tab 2: RAG chat  │
                         └───┬───────────────┬───────────────┬─────────┘
                             │               │               │
             OpenAI API      │               │ POST /upload  │ POST /ragimgquery
        (gpt-5.5 + tools)    │               │  (files)      │  (question + images)
                             ▼               ▼               ▼
                   ┌──────────────┐   ┌──────────────┐  ┌──────────────┐
                   │  api.openai  │   │ BW6: RAG      │  │ BW6: RAG     │
                   │    .com      │   │ Ingestion     │  │ Query        │
                   └──────┬───────┘   │  :5000        │  │  :7312       │
        tool call         │           └──────┬────────┘  └──────┬───────┘
   POST /mcp/call         │                  │  chunk+ingest    │ retrieve+LLM
                          ▼                  ▼                  ▼
                 ┌──────────────┐      ┌───────────────────────────────┐
                 │  mcp-proxy   │      │   Local vector store (file)    │
                 │ (Node :3001) │      │  C:\tmp\air_liquide_demo\...   │
                 └──────┬───────┘      └───────────────────────────────┘
                        │ stdio (npx mcp-remote)
                        ▼
        ┌────────────────────────────────────────┐
        │  BW6 MCP Server   http://<host>:18000/rest/mcp │
        │  (Smart Cylinder REST app, ops exposed as MCP tools) │
        └────────────────────────────────────────┘
```

### Components in this folder

| Path | Type | Role | Default endpoint |
|---|---|---|---|
| `air_liquide_smart_cylinder/` (+ `.application`) | BW6 app | Cylinder REST API; ops auto-exposed as MCP tools | `http://localhost:8080/api/v1` and MCP at `:18000/rest/mcp` |
| `RAG_Air_Liquide_Ingestion/` (+ `.application`) | BW6 app | Upload → save → chunk → ingest to vector store | `POST http://localhost:5000/upload` |
| `RAG_Air_Liquide_Query/` (+ `.application`) | BW6 app | Question (+images) → retrieve → LLM answer | `POST http://localhost:7312/ragimgquery` |
| `mcp-proxy/` | Node.js | Browser-callable HTTP/CORS bridge to the BW6 MCP server | `http://localhost:3001` |
| `demo.html` | Web UI | The chatbot / demo front-end | open in a browser |

**How the MCP tools work:** the Smart Cylinder OpenAPI contract
(`Service Descriptors/gemini-code-*.json`) carries `x-mcp-tool-name` /
`x-mcp-description` annotations on each operation. When the BW6 engine runs with
its MCP server enabled, those REST operations are published as callable MCP
tools — no extra code. `mcp-proxy` exists only because browsers can't speak the
MCP stdio transport directly; it spawns `npx mcp-remote <mcp-url>` and re-exposes
it as plain HTTP with CORS.

---

## 3. Prerequisites

- **TIBCO BusinessWorks 6.12** (the processes were built on `6.12.0 HF4`) with
  the **RAG** and **MCP server** capabilities, to run/deploy the three BW apps.
- **Node.js 18+** and **npm** (for `mcp-proxy` and `npx mcp-remote`).
- An **OpenAI API key** with access to the models referenced by the demo
  (`gpt-5.5` and `text-embedding-3-large`). The key is used in two places:
  - The **browser** (Tab 1) — you paste it into the UI; it stays in
    `sessionStorage` and is sent directly to `api.openai.com`.
  - The **BW6 RAG apps** — the key is stored (encrypted) in each app's
    `*.ragResource`. You must set your own key there before deploying.
- A modern browser.

> **Model note:** `gpt-5.5` and `text-embedding-3-large` are what the demo is
> configured to request. If your OpenAI account doesn't have those exact models,
> switch to available ones (see *Configuration* below) or the calls will fail.

---

## 4. Setup & run

There are three moving parts to start: the **BW6 apps**, the **MCP proxy**, and
the **web UI**. Do them in this order.

### Step A — Run/deploy the three BW6 apps

Open the three application projects in **TIBCO Business Studio** (or build and
deploy the `.application` modules to a BW6 AppNode):

1. `air_liquide_smart_cylinder.application` → listens on **:8080**, and its
   engine exposes the **MCP server** on **:18000/rest/mcp**.
2. `RAG_Air_Liquide_Ingestion.application` → listens on **:5000**.
3. `RAG_Air_Liquide_Query.application` → listens on **:7312**.

Before running the RAG apps, set your OpenAI key and the vector-store path:
- Edit `RAG_Air_Liquide_Ingestion/Resources/rest_download/IngestRAGConfiguration.ragResource`
- Edit `RAG_Air_Liquide_Query/Resources/rag_image_query/RAGConfiguration.ragResource`
- In each, set `openAIKey`, confirm `openAIModelType` / `embeddingOpenAIModelName`,
  and confirm `localStorageFileLocation` (default `C:\tmp\air_liquide_demo\localvector.txt`).
  Create that folder first if it doesn't exist. Both apps must point at the
  **same** vector-store file so that queries can find what ingestion wrote.

Ports are defined as module properties in each app's `META-INF/default.substvar`
(`UploadPort=5000`, `imgUploadPort=7312`, etc.) — change them there if needed and
update `demo.html` to match.

### Step B — Start the MCP proxy

```bash
cd mcp-proxy
npm install          # first time only (deps are already vendored, but this is safe)
npm start            # -> MCP proxy on http://localhost:3001
```

The proxy reads `mcp-proxy/mcp-config.json`, which tells it which MCP server to
connect to:

```json
{
  "command": "npx",
  "args": ["mcp-remote", "http://10.182.34.53:18000/rest/mcp", "--allow-http"],
  "env": {}
}
```

**Point this at your BW6 MCP server.** Replace `10.182.34.53:18000` with the host
and port where your Smart Cylinder app's MCP server is running (use `localhost`
if you deployed it locally). `--allow-http` permits the plain-HTTP MCP endpoint.

Verify it's up:
```bash
curl http://localhost:3001/health          # {"ok":true,...,"connected":...}
curl http://localhost:3001/mcp/tools       # lists the tools the BW6 MCP server exposes
```

> Tip: run `/mcp/tools` and confirm the tool **names** returned match the ones
> the UI expects (`searchGasStock`, `getCylinderStatus`, `dispatchCylinder`). If
> your BW6 MCP server publishes the snake_case names from the contract
> (`search_gas_stock`, …), align them — either rename in the UI's `MCP_TOOLS`
> array or configure the tool names on the BW6 side.

### Step C — Open the web UI

Open `demo.html` directly in a browser (double-click, or `file://…/demo.html`).
No build step is required. The header shows a live connection indicator:
- It pings `:5000` (upload), `:7312` (RAG query) and `:3001/health` (MCP proxy).
- Green **"All services online"** = 3/3 reachable.

The endpoints the UI calls are set at the top of the `<script>` in `demo.html`:

```js
const API = {
  cyl: 'http://localhost:8080/api/v1',              // Smart Cylinder REST (via MCP)
  up:  'http://localhost:5000',                     // RAG ingestion
  rag: 'http://localhost:7312',                     // RAG query
  mcp: 'http://10.182.34.53:18000/rest/mcp'         // BW6 MCP server (informational)
};
```

Adjust these if your hosts/ports differ.

---

## 5. Using the chatbot

### Tab 1 — Smart Cylinder Operations (MCP)
1. Paste your **OpenAI API key** into the *OpenAI Key* field (top-right of the
   chat card). It's saved to `sessionStorage` for the session only.
2. Type a question or click a **"Try:"** chip, then **Ask AI**.
3. Watch the flow: the assistant shows a **"Calling MCP → `toolName`"** step
   (arguments), then **"MCP returned"** with the live BW6 result, then a written
   answer. Multi-step tool chains are handled automatically.

Good prompts (match the shipped mock data):
- *"What is the current pressure and certification status of cylinder AL-ARG-9082?"*
- *"Dispatch cylinder AL-NIT-4011 to Customer Site Paris Nord"*
- *"Do we have high-purity Nitrogen available in Houston Yard A?"*

### Tab 2 — AI Document Assistant (RAG)
1. **Left panel — Document Ingestion:** drag files (PDF/Word/Excel/TXT/MD) into
   the drop zone (or click to browse) → **Ingest into Knowledge Base**. Each
   file is saved, chunked, and embedded into the vector store.
2. **Right panel — Ask the AI Assistant:** type a question and **Send**. You can
   attach one or more images (📷 button) for visual context. The answer is
   grounded in whatever you've ingested.

---

## 6. Suggested 2-minute demo script

1. Open Tab 1, paste OpenAI key. Click **"▶ Try: Search Nitrogen"** banner
   button (or ask *"Do we have high-purity Nitrogen in Houston Yard A?"*).
   → Show the live MCP tool call + BW6 result.
2. Ask *"Reserve/dispatch AL-ARG-9082 to Fab Plant 4"* → show the `dispatchCylinder`
   POST executing and the confirmation.
3. Switch to Tab 2. Upload a safety PDF → **Ingest**.
4. Ask *"What PPE is required when handling Oxygen cylinders?"* → show the
   grounded RAG answer.

Narrative: *the same BW6 REST services are (1) called autonomously by an AI agent
via MCP and (2) complemented by a document knowledge base — all built in BW6.*

---

## 7. Configuration reference

| Setting | Where | Default |
|---|---|---|
| Smart Cylinder REST port | app substvar / httpConnResource | `8080` |
| BW6 MCP server URL | `mcp-proxy/mcp-config.json` → `args[1]` | `http://10.182.34.53:18000/rest/mcp` |
| MCP proxy port | `PORT` env for `mcp-proxy` (`server.js`) | `3001` |
| RAG ingestion port | `RAG_Air_Liquide_Ingestion/META-INF/default.substvar` → `UploadPort` | `5000` |
| RAG query port | `RAG_Air_Liquide_Query/META-INF/default.substvar` → `imgUploadPort` | `7312` |
| LLM model | `*.ragResource` (`openAIModelType`) and `demo.html` (`model`) | `gpt-5.5` |
| Embedding model | `*.ragResource` (`embeddingOpenAIModelName`) | `text-embedding-3-large` |
| Vector store | `*.ragResource` (`embeddingStorageProvider=local`, `localStorageFileLocation`) | `C:\tmp\air_liquide_demo\localvector.txt` |
| Browser API endpoints | `demo.html` → `const API` | see Step C |

The RAG shared resource also supports **Weaviate**, **Ollama** embeddings, and a
**data grid** store — those fields are present but not used by this demo (it runs
`embeddingStorageProvider="local"` with OpenAI embeddings).

---

## 8. Troubleshooting & known quirks

- **Connection dot shows "offline" / "n/3".** One of the services isn't up. The
  UI checks `:5000`, `:7312`, and `:3001/health` — not `:8080` directly (the
  cylinder API is reached *through* the MCP server, not by the browser).
- **"OpenAI API key required".** Enter the key in Tab 1's key field; RAG (Tab 2)
  uses the key stored in the BW6 `.ragResource`, not the browser field.
- **Model errors (404 / model not found).** Your account may not have `gpt-5.5`
  or `text-embedding-3-large`. Change the model in `demo.html` (`callOpenAI`) and
  in both `.ragResource` files to a model you can access.
- **Search returns nothing.** The Smart Cylinder search
  (`GET /cylinders/search`) filters on **both** `gasType` **and** `location` and
  matches them **exactly** — you must supply both, spelled as in the mock data
  (e.g. gas `Nitrogen`, location `Houston Yard A`). A gas-type-only search yields
  no results by design.
- **Cylinder not found.** Only the four IDs in the table above exist. (Note: some
  UI example chips mention `AL-NIT-3041`, which is **not** in the data — use
  `AL-NIT-4011`.)
- **Dispatch doesn't "stick".** `dispatchCylinder` returns an *In-Transit*
  confirmation but the process is **stateless** — the mock inventory isn't
  mutated, so re-querying the cylinder still shows its original status. This is
  expected for a demo.
- **MCP tool name mismatch.** If tool calls fail with "unknown tool", reconcile
  the names from `GET /mcp/tools` with the `MCP_TOOLS` array in `demo.html`.
- **CORS.** The proxy sends `Access-Control-Allow-Origin: *`. The BW6 REST apps
  must also allow the browser origin (the UI issues `OPTIONS` preflights on
  upload/query).

---

## 9. Security notes

- The `*.ragResource` files contain **encrypted (BW6-obfuscated) OpenAI keys**.
  Replace them with your own and **do not commit real keys**. Treat this folder
  as containing credentials.
- The browser sends your OpenAI key straight to `api.openai.com`; it is kept only
  in `sessionStorage`. Use a key you're comfortable exposing client-side for a
  demo (ideally a scoped/temporary key).
- `mcp-config.json` points at a specific internal host (`10.182.34.53`). Update
  it for your environment and avoid publishing internal addresses.
</content>
</invoke>
