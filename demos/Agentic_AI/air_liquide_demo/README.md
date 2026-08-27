# Air Liquide — Smart Operations AI Demo

> **📖 Full user guide:** [`Air_Liquide_Demo_UserGuide.md`](Air_Liquide_Demo_UserGuide.md)
> — read that for the complete architecture, prerequisites, and step-by-step run
> instructions. This README is a short orientation.

> **⚠️ Different stack from the other use cases here.** Unlike the sibling
> `*_Use_Case` folders (which use the TIBCO **Flogo** 3-app MCP + A2A +
> Orchestrator pattern), this demo is built on **TIBCO BusinessWorks 6 (BW 6.12)**
> and a single-page web UI. There is no Flogo orchestrator, no PostgreSQL, and no
> A2A tier.

## What this demo does

An end-to-end demo showing how **TIBCO BusinessWorks 6** can power an AI
assistant for a gas-cylinder logistics operation ("Smart Cylinder Operations").
A single browser app (`demo.html`) talks to three BW6 apps through two AI
patterns:

1. **Agentic tool-calling over MCP** — an LLM decides when to call live BW6 REST
   operations that BW6 auto-exposes as **MCP tools** (Model Context Protocol).
2. **Retrieval-Augmented Generation (RAG)** — upload technical documents, then
   ask grounded natural-language questions (optionally with an image), answered
   by BW6's built-in RAG activities.

The customer story: *"BW6 turns your existing REST/integration assets into
AI-callable tools and a document knowledge base — with almost no glue code."*

## Components

| Component | Type | Role | Endpoint (default) |
|---|---|---|---|
| `air_liquide_smart_cylinder/` (+ `.application`) | BW6 app | Cylinder REST API; operations auto-exposed as MCP tools | REST `:8080/api/v1`, MCP `:18000/rest/mcp` |
| `RAG_Air_Liquide_Ingestion/` (+ `.application`) | BW6 app | Upload → save → chunk → ingest to vector store | `POST :5000/upload` |
| `RAG_Air_Liquide_Query/` (+ `.application`) | BW6 app | Question (+images) → retrieve → LLM answer | `POST :7312/ragimgquery` |
| `mcp-proxy/` | Node.js | Browser-callable HTTP/CORS bridge to the BW6 MCP server | `:3001` |
| `demo.html` | Web UI | The chatbot / demo front-end | open in a browser |

## Quick start (summary — see the user guide for detail)

1. **Run the three BW6 apps** in Studio or deploy the `.application` modules to a
   BW6 AppNode (ports `:8080` / `:5000` / `:7312`).
2. **Start the MCP proxy:** `cd mcp-proxy && npm install && npm start` (→ `:3001`).
   Point `mcp-proxy/mcp-config.json` at your BW6 MCP server URL
   (`http://<host>:18000/rest/mcp`).
3. **Open `demo.html`** in a browser. Adjust the endpoint hosts/ports at the top
   of its `<script>` block if yours differ.

## Prerequisites

- **TIBCO BusinessWorks 6.12** (processes built on `6.12.0 HF4`) with the AI/RAG
  and MCP palettes.
- **Node.js 18+** and **npm** (for `mcp-proxy` / `npx mcp-remote`).
- An **OpenAI API key** — set it in each BW6 RAG app's app property/keystore and
  in `demo.html` (never commit the real key; use the encrypted app property).

> ⚠️ **Manual configuration:** supply your own OpenAI API key, and update every
> host/port to your environment (`mcp-proxy/mcp-config.json`, `demo.html`
> endpoint map, and each app's `META-INF/default.substvar`). The user guide's
> "Configuration reference" table lists every value and where it lives.
