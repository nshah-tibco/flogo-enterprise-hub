# Scholarly Publishing — Author Services Assistant (Governed Agentic AI)

A chat assistant for a scholarly publisher's authors. An author verifies who they are, checks where
their manuscripts stand, gets suggestions for better-suited journals when a manuscript is declined with
a transfer offer, sees what they would pay under their institution's open-access agreement, and moves
the manuscript in two confirmed steps. Fee waivers, appeals, authorship changes and integrity questions
go to the right team. The assistant never decides those.

**Agentic in the middle, deterministic at the edges:** the AI handles the conversation and the journal
matching. PostgreSQL decides identity, eligibility, prices and every change. People decide the exceptions.

> All publishers, journals, institutions and people in this sample are fictional.

## Why an agent here?

| Part | Who owns it | Why |
|---|---|---|
| Matching a manuscript's abstract to journals whose aims & scope fit, and explaining why | **AI agent** | Free text against free text, with trade-offs (topic, method, word limit). A keyword filter misses "compound coastal flood risk" ↔ "storm surge and flood risk models". |
| Understanding the request and chaining the steps | **AI agent** | Conversation, ambiguity, multi-step planning. |
| Identity, which manuscripts an author can see, transfer eligibility, fees, moving the manuscript | **Database rules** | A model must not be able to talk its way into someone else's record or a different price. |
| Fee waivers, decision appeals, authorship changes, integrity questions | **People** | Discretion and accountability. The assistant opens a case for the right team. |

Without the AI, status, fees and transfers would still work through a form. What you would lose is
reading an abstract and knowing which journals it belongs in, and why.

## Architecture

```
Chat UI ──WebSocket :9840 /authorservices──► AuthorServicesAIOrchestrator  (AI Agent)
                                               │
                  MCP :9842 ◄──────────────────┤──────────────► A2A :9843
                  AuthorServicesMCPServer       │               AuthorServicesAgents
                  8 tools                       │               journal_match_agent
                          └─────────────► PostgreSQL `author_services` ◄──┘
                                          business rules · review teams
```

| App | Port / path | What it does |
|---|---|---|
| `AuthorServicesAIOrchestrator.flogo` | WebSocket `9840` `/authorservices` | The assistant the author chats with. Each browser connection is its own conversation. |
| `AuthorServicesMCPServer.flogo` | MCP `9842` `/author-services-mcp` | Tools: verify the author, list and show manuscripts, check fees, propose and confirm a transfer, open and list review cases. |
| `AuthorServicesAgents.flogo` | A2A `9843` | `journal_match_agent`: suggests journals from the manuscript's title, abstract and keywords. It never sees who the author is. |

## Prerequisites

- **TIBCO Flogo VS Code extension** 2.26.6 or later.
- **PostgreSQL** 14 or later.
- An **OpenAI API key** (or another provider the AI Agent supports).
- **Node.js** 16 or later, for the shared [Chatbot](../Chatbot/) web client.

## Steps to run

### 1. Create the database

```bash
createdb -U postgres author_services
psql -U postgres -d author_services -f database.sql
```

### 2. ⚠️ Configure the apps — these are NOT configured in the shipped files

Open each `.flogo` in VS Code and set these **App Properties**:

**`AuthorServicesMCPServer.flogo`**

| Property | Set to |
|---|---|
| `PostgreSQL.PostgresConn.Host` / `Port` / `User` | your PostgreSQL server (default `localhost` / `5432` / `postgres`) |
| `PostgreSQL.PostgresConn.Password` | your PostgreSQL password |
| `PostgreSQL.PostgresConn.Database_Name` | `author_services` |

**`AuthorServicesAgents.flogo`**

| Property | Set to |
|---|---|
| `AgenticAI.OpenAIConn.API_Key` | your LLM API key |
| `AgenticAI.OpenAIConn.LLM_Provider` / `LLM_Base_URL` | `OpenAI` / leave empty for OpenAI, or your provider's endpoint |
| `LLM_Model` | a model your key can use (ships as `gpt-5-nano`) |
| `PostgreSQL.PostgresConn.*` | the same values as the MCP Server |

**`AuthorServicesAIOrchestrator.flogo`**

| Property | Set to |
|---|---|
| `AgenticAI.OpenAIConn.API_Key` / `LLM_Provider` / `LLM_Base_URL` / `LLM_Model` | the same values as the Agents app |

Then open the **Connections** of each app and click **Connect** (or **Test**) on the PostgreSQL and LLM
connections. If a trigger shows a red ✗ after import, open it and click **Sync**.

> Changing a port? Update the port property (`MCP_SERVER_PORT`, `journal_match_agent_PORT`,
> `WebSocket_PORT`) **and** the matching connection URL in the orchestrator:
> `http://localhost:9842/author-services-mcp` (MCP) and `http://localhost:9843` (A2A).

### 3. Start the apps in this order

**MCP Server (9842) → Agents (9843) → Orchestrator (9840).** Wait for each one to log a clean start.

### 4. Open the chat client and connect

The chat client is the shared web app in [`samples/Agentic_AI/Chatbot`](../Chatbot/) (one folder up from
this one). It needs Node.js 16+.

```bash
cd ../Chatbot
npm install    # first time only
npm start
```

1. Open **http://localhost:3000**.
2. In the URL box at the top right, replace the default with **`ws://localhost:9840/authorservices`**.
3. **Click the ↻ (refresh) icon next to the URL box.** Typing the URL alone does nothing: ↻ applies it, and
   an alert confirms *"WebSocket URL updated. Click Connect to use the new URL."*
4. Click **Connect**. The status turns green: **● Connected**.

**Won't connect?** Click **Disconnect** (↻ is refused while connected), check the URL, click **↻** again,
then **Connect**. Make sure the orchestrator is running on port 9840. The chatbot remembers the last URL
you applied, so a URL left over from another demo is a common cause.

### 5. Run the demo

Sign in as one of the demo authors. In a real portal the author would already be signed in; here they
type their ORCID iD and the code from a "verification email".

| Author | ORCID iD | Code | What they show |
|---|---|---|---|
| Dr. Maya Okafor | `0000-0002-1825-0097` | `482913` | 3 manuscripts; MS-2026-0412 has a transfer offer; her agreement covers HCRL in full |
| Prof. Lars Eriksen | `0000-0001-5109-3700` | `771204` | an accepted paper whose agreement budget is used up, so a fee waiver goes to a person |
| Dr. Ana Ribeiro | `0000-0003-1415-9269` | `305118` | a manuscript under an integrity hold: details hidden, transfer blocked |

The main walkthrough, as Maya:

1. *"Hi, I'd like help with my submissions. ORCID 0000-0002-1825-0097, code 482913."*
2. *"What manuscripts do I have and where are they?"*
3. *"MS-2026-0412 got a transfer offer. Which journals would fit it better?"* — the journal-match agent runs.
4. *"What would I pay to publish in HCRL?"* — covered in full, so she pays 0.
5. *"OK, please transfer MS-2026-0412 to HCRL."* — the assistant shows the quote and asks for a yes.
6. *"Yes, I confirm."* — the transfer is made.
7. *"For MS-2026-0301 I think reviewer 2 misunderstood our method. I want to appeal."* — an appeal
   case goes to the Editorial Office.

More prompts, including ones that show the rules holding, are in [prompts.md](prompts.md).

**Reset between demos:**

```bash
psql -U postgres -d author_services -f reset_data.sql
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| The assistant never manages to verify the author | Use the exact ORCID iD and code from the table. Keep **Redact Sensitive Data** off on the orchestrator's AI Agent; it masks the ORCID and the code. |
| "I can't reach the tools" or no journal suggestions | Start the MCP Server and the Agents app **before** the orchestrator, and check the orchestrator's connection URLs match their ports. |
| LLM errors (401, model not found) | Check the API key and that your key can use the model in `LLM_Model`. For providers other than OpenAI, set `LLM_Base_URL`. |
| A new browser tab asks the author to verify again | Expected: each connection is a separate conversation. |
| Transfer offer or dates look wrong | Reload `reset_data.sql`. Demo dates are relative to today. |
