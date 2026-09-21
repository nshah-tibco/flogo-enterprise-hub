# Flogo Skill Library

A library of **skills for AI coding agents** (such as **Claude Code**) to design, build, test, and deploy TIBCO Flogo integration applications. Drop these skills into the `.claude/skills/` directory of any project and the agent will use them to drive the Flogo, build, and platform CLIs end-to-end.

---

## What's a Skill?

A **skill** is a Markdown file with frontmatter that documents a specific capability for an AI coding agent. The agent reads the skill on demand when the user's request matches its description. Skills make the agent reliable and repeatable on domain-specific tasks (like building a Flogo flow) — without you having to explain the same patterns over and over.

Each skill in this library lives in `.claude/skills/<skill-name>/SKILL.md` and follows this shape:

```markdown
---
name: <skill-name>
description: <when the agent should use this skill>
user-invocable: true
---

# Step-by-step instructions, command references, and recipes...
```

![Skills folder structure and SKILL.md preview](./images/coding-agents-skills.png)

---

## What's in this Library

The library contains **10 skills** that cover the full Flogo development lifecycle — from designing a flow, to mapping and testing it, to building an executable, to deploying it on the TIBCO Platform, and up to scaffolding complete Agentic AI use cases.

| Skill | Type | Purpose |
|---|---|---|
| **fda** | CLI reference | Full reference for the **Flogo Design Assistant** CLI — every task to create or modify a `.flogo` file (flows, activities, triggers, schemas, properties, tests). |
| **fda-mapping** | CLI reference | Focused reference for **building, inspecting, and validating Flogo mappings** with `fda` — the `input.mapping` shape, the four source kinds (`$flowctx` / `$property` / `$activity` / `$loop`), function calls, and `@foreach` loops. |
| **flogobuild** | CLI reference | Reference for **building executables** and TIBCO Platform deployment artifacts from `.flogo` files. |
| **tibcop** | CLI reference | Reference for the **TIBCO Platform CLI** — manage builds, deploy, scale, and inspect Flogo applications on a dataplane. |
| **flogo-deploy** | Recipe | End-to-end recipe to **deploy a `.flogo` app to a TIBCO Platform dataplane** (build → values → deploy → scale). |
| **flogo-unit-testing** | Recipe | Recipe to **create and run unit tests for Flogo apps** — test files, test cases with flow inputs, assertions on flow outputs, and test execution with result verification. |
| **mapping-from-excel** | Recipe | Recipe to **build a Flogo flow from an Excel mapping spec** — input fields, output fields, and per-field mapping rules. |
| **rest-to-database-app** | Recipe | Recipe to **scaffold a REST API Flogo app that queries a database** (REST trigger → log → DB query → reply). |
| **agentic-ai-use-case** | Use-case builder | Scaffold a complete, runnable **Agentic AI demo for any vertical** — an MCP Server (read-only DB tools) + A2A Agents app (write-workflow agents) + WebSocket AI Orchestrator, backed by PostgreSQL, modeled on the reference use cases under `samples/Agentic_AI/`. |
| **agentic-ai-use-case-fda** | Use-case builder | The same 3-app Agentic AI demo, but constructed **entirely via the `fda` CLI** (command-by-command) rather than cloned/adapted JSON. |

---

## Architecture: Coding Agent + Flogo

The skills work alongside the rest of the Flogo developer toolkit. The coding agent uses **VS Code with the Flogo Design Assistant** for design-time editing, **flogobuild** for local builds, and the **TIBCO Platform CLI (`tibcop`)** to deploy applications to a dataplane on the TIBCO Platform.

![Architecture: VS Code + Skills + Design Assistant + builders + dataplane](./images/architecture.png)

---

## Example: Excel-to-Flogo Mapping

Using the `mapping-from-excel` skill, the agent can read an Excel mapping spec — input fields in column A, output fields in column B, and a mapping expression in column C — and turn it into a fully wired Flogo flow with two mappers, a logger, and a timer trigger.

![Excel mapping spec turned into a Flogo flow](./images/excel-to-flogo-mapping.png)

A typical prompt:

> *"Read `ExcelWithMapping.xlsx` and create a Flogo flow that performs the mapping defined in the spreadsheet. Then build it and run it locally for 5 seconds and show me the logs."*

---

## Example: Design, Build, Run, and Deploy

The `flogo-deploy` skill chains together the build (`flogobuild`), values generation, deployment (`tibcop flogo:deploy-app-release`), and scale-up (`tibcop flogo:scale-app`) steps. The agent can take an app from source to a running instance on the TIBCO Platform in a single conversation.

![Deployment success with build ID, app ID, and live logs in the platform](./images/deployed-app.png)

A typical prompt:

> *"Deploy the `Flogo_Apps/customer-api.flogo` app to dataplane `<DATAPLANE_NAME>` and start it."*

---

## Getting Started

### Option 1: Install via the Marketplace template

1. Open the **Flogo Skill Library** entry in the TIBCO Developer Hub Marketplace.
2. Click **Get** to install the documentation.
3. Click the **Run Flogo Skill Library Template** button to generate a new project pre-seeded with the skills.
4. Open the generated GitHub repo in **VS Code with Claude Code** installed.
5. Copy `.claude/skills/config.example.md` to `.claude/skills/config.md` and fill in the values for your environment (build context, platform token, dataplane, database, LLM key). Agent conventions live in `AGENT.md`.
6. Start asking the agent to design, build, run, or deploy Flogo apps.

### Option 2: Add skills to an existing project

If you already have a project, copy the `.claude/skills/` folder from the seed repo into your project root, and add the conventions to your project's `AGENT.md`.

---

## Required Tools

The skills drive the following tools. **`fda` and `flogobuild` ship inside the TIBCO Flogo VS Code extension** — they are not on your `PATH` by default, so set up the `fda` alias (see [Setting up the `fda` alias](#setting-up-the-fda-alias)) to run them from any terminal. **`tibcop`** is installed separately and should be on your `PATH`.

| Tool | Purpose | Documentation |
|---|---|---|
| **fda** (Flogo Design Assistant) | Design-time edits to `.flogo` files (ships inside the Flogo VS Code extension) | [Flogo](https://docs.tibco.com/products/tibco-flogo-enterprise) |
| **flogobuild** | Build executables and Platform deployment artifacts (ships inside the Flogo VS Code extension) | [Flogo](https://docs.tibco.com/products/tibco-flogo-enterprise) |
| **tibcop** (TIBCO Platform CLI) | Deploy and manage applications on the TIBCO Platform | [TIBCO Platform](https://www.tibco.com/platform) |
| **TIBCO Flogo VS Code extension** | Provides `fda` + `flogobuild`, plus the visual designer for `.flogo` files | [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=tibco.flogo) |
| **Claude Code** (or another coding agent) | Reads and applies the skills | [Claude Code](https://www.anthropic.com/claude-code) |

---

## Setting up the `fda` alias

The Flogo Design Assistant CLI (`flogodesign-cli`) ships inside the [**TIBCO Flogo VS Code extension**](https://marketplace.visualstudio.com/items?itemName=tibco.flogo) at a long, versioned path like `<vscode-extensions-dir>/tibco.flogo-<VERSION>/bin/flogodesign-cli`. Because that path **changes with every extension update**, don't hardcode it — set up an `fda` alias that **discovers the latest installed version dynamically**, so you (and the coding agent) can simply run `fda <task>` from any terminal.

> **Never hardcode the extension folder name** (e.g. `tibco.flogo-2.26.6-2851`). The glob `tibco.flogo-*/bin/flogodesign-cli*` sorted by newest always resolves to the latest installed version. If the binary can't be found, install the TIBCO Flogo VS Code extension.

Add the function below to your shell startup file so `fda` is available in every terminal session:

| OS | Shell | Startup file |
|---|---|---|
| Windows | Git Bash | `~/.bashrc` |
| Windows | PowerShell | `$PROFILE` |
| macOS | zsh (default) | `~/.zshrc` |
| Linux | bash | `~/.bashrc` |

### macOS / Linux / Windows (Git Bash) — Bash or Zsh function

Add to `~/.bashrc` (bash / Git Bash) or `~/.zshrc` (macOS zsh):

```bash
fda() {
  local cmd="" home_dir="${HOME:-$USERPROFILE}" ext_name="flogodesign-cli"
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    ext_name="flogodesign-cli.exe"
  fi
  for dir in "$home_dir/.vscode/extensions" \
             "$home_dir/.vscode-insiders/extensions" \
             "$home_dir/.vscode-server/extensions"; do
    cmd=$(ls -td "$dir/tibco.flogo-"*/bin/"$ext_name" 2>/dev/null | head -1)
    [ -n "$cmd" ] && break
  done
  if [ -z "$cmd" ]; then
    echo "Error: flogodesign-cli not found. Install the TIBCO Flogo VS Code extension." >&2
    return 1
  fi
  "$cmd" "$@"
}
```

Reload the shell so the function takes effect:

```bash
source ~/.zshrc   # or: source ~/.bashrc
```

### Windows — PowerShell function

PowerShell aliases cannot accept arguments, so define `fda` as a **function**. Add to your PowerShell profile (`$PROFILE`):

```powershell
function fda {
  $cli = Get-ChildItem "$env:USERPROFILE\.vscode\extensions\tibco.flogo-*\bin\flogodesign-cli.exe" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $cli) {
    $cli = Get-ChildItem "$env:USERPROFILE\.vscode-insiders\extensions\tibco.flogo-*\bin\flogodesign-cli.exe" -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
  }
  if (-not $cli) { Write-Error "flogodesign-cli not found. Install the TIBCO Flogo VS Code extension."; return }
  & $cli.FullName @args
}
```

If `$PROFILE` doesn't exist yet, create it first, then reload it:

```powershell
New-Item -Type File -Path $PROFILE -Force   # only if it doesn't exist yet
. $PROFILE
```

### Verify

```bash
fda version
```

---

## Configurable Defaults

All environment-specific values live in a **single source of truth**: `config.md`, next to the skills. Copy the template and fill in your values (the file is git-ignored, so real credentials are never committed). The skills folder lives at `.claude/skills/` in a Marketplace-seeded project, or at `skills-library/.claude/skills/` in this hub repo — run the copy from your repo root accordingly:

```bash
# Marketplace-seeded project (skills at the repo root):
cp .claude/skills/config.example.md .claude/skills/config.md

# this hub repo:
cp skills-library/.claude/skills/config.example.md skills-library/.claude/skills/config.md
```

Key values the skills rely on:

| Key (in `config.md`) | What to set it to | How to find the value |
|---|---|---|
| `FLOGOBUILD_CONTEXT_NAME` | Build context name for `flogobuild` (e.g. `flogo-vscode-2.26.5-ENGR-001`) | `flogobuild list-context` |
| `DATAPLANE_NAME` | Default dataplane to deploy to | `tibcop tplatform:list-data-planes` |
| `CP_URL` / `TIBCOP_TOKEN` | TIBCO Platform control-plane URL and API token | TIBCO Platform console |
| PostgreSQL / LLM / email | Connection settings for the database, LLM provider, and SMTP | your environment |
| `AGENTIC_USE_CASES_DIR` | *(optional)* folder of reference Agentic AI use-case apps the two `agentic-ai-use-case*` skills clone/study | leave unset to default to `samples/Agentic_AI/`; set only if the skills are installed standalone away from that folder |

---

## Layout

```
.
├── .claude/
│   └── skills/                       # Skill definitions consumed by the AI coding agent
│       ├── fda/                      # Flogo Design Assistant CLI reference
│       ├── fda-mapping/              # Flogo mapping reference for the fda CLI
│       ├── flogobuild/               # Flogo build CLI reference
│       ├── tibcop/                   # TIBCO Platform CLI reference
│       ├── flogo-deploy/             # End-to-end deployment recipe
│       ├── flogo-unit-testing/       # Create and run Flogo unit tests
│       ├── mapping-from-excel/       # Build a Flogo flow from an Excel mapping spec
│       ├── rest-to-database-app/     # Scaffold a REST -> DB Flogo app
│       ├── agentic-ai-use-case/      # Scaffold an Agentic AI use case (MCP + A2A + orchestrator)
│       ├── agentic-ai-use-case-fda/  # Same, built entirely via the fda CLI
│       ├── config.example.md         # Template for environment-specific values (copy to config.md)
│       └── config.md                 # Your environment values (git-ignored; not committed)
├── AGENT.md                          # Project-level instructions for the agent
└── Flogo_Apps/                       # Place your .flogo applications here
```

## Example prompts

- *"Create a Flogo app under `Flogo_Apps/` that exposes a REST endpoint `GET /customers/{id}` and queries a MySQL database. Call the app `customer-api`."* (`rest-to-database-app`)
- *"Read `mapping.xlsx` and create a Flogo flow that performs the mapping defined in the spreadsheet."* (`mapping-from-excel`)
- *"Inspect and validate the mappings in `Flogo_Apps/customer-api.flogo` and fix any unresolved mapper fields."* (`fda-mapping`)
- *"Build the `Flogo_Apps/customer-api.flogo` app and run it locally for 5 seconds, then show me the logs."* (`flogobuild`)
- *"Create and run unit tests for `Flogo_Apps/customer-api.flogo` with assertions on the response."* (`flogo-unit-testing`)
- *"List my TIBCO Platform dataplanes and show the status of the apps running on `MyDataPlane`."* (`tibcop`)
- *"Deploy the `Flogo_Apps/customer-api.flogo` app to dataplane `MyDataPlane`."* (`flogo-deploy`)
- *"Build a telecom invoice-support Agentic AI demo (MCP Server + A2A Agents + WebSocket orchestrator) backed by PostgreSQL — ask me whether to use the FDA CLI or the clone method first."* (`agentic-ai-use-case` / `agentic-ai-use-case-fda`)

> **Note:** For more sample prompts, see [skills-library/SamplePrompts/README.md](SamplePrompts/README.md).

---

## Tips for Working with the Agent

- **Be explicit about file paths.** The agent works best when you tell it where to put the `.flogo` file (e.g. `Flogo_Apps/customer-api.flogo`).
- **Iterate in small steps.** Ask for a flow first, then add activities, then add the trigger, then build & test.
- **Always run a local test before deploying.** The `mapping-from-excel` and `rest-to-database-app` recipes both include a build + 5-second-run step.
- **Check the agent's commands.** The `fda` and `tibcop` commands are well-documented in the skills — if the agent does something unexpected, ask it to explain which skill it used and which command it ran.

---

<!-- SEO Keywords: TIBCO Flogo, AI Coding Agent, Claude Code, AI Skills, Flogo Design Assistant, FDA CLI, Flogobuild, TIBCO Platform CLI, Low-Code, No-Code, iPaaS, Integration Automation, Excel to Flogo, REST API Scaffolding, Flogo Deployment, AI-Powered Development, Visual Flow Designer, Enterprise Integration, GoLang, VS Code Extension -->

**Topics:** `AI Coding Agent` · `Claude Code` · `Flogo Skills` · `Low-Code` · `iPaaS` · `Enterprise Integration`
