# TIBCO Flogo® Hands-on Workshop — Sydney Water

A 2.5-hour hands-on workshop: build integration APIs in Flogo by hand and with AI, then expose them to an AI
agent as MCP tools with guardrails.

| Lab | What you build | Port | Skills |
|---|---|---|---|
| **1 · Rainfall Risk API** | REST API that calls a weather SaaS (Open-Meteo), rates the rainfall risk and raises an inspection work order in a field-service SaaS (webhook.site) | 9999 | API integration & mediation: REST trigger, Invoke REST, mapper, branching, error handling, app properties |
| **2 · Leak Report Intake** | A flow built from a process diagram by an AI assistant (Cline + Flogo Design Assistant), finished and tested by you | 9998 | AI-assisted development, diagram → flow |
| **3 · Your APIs as MCP tools** | An MCP server exposing the Lab 1 and Lab 2 APIs as tools for an AI agent, with four guardrails: API-key auth, input validation, PII masking, least privilege | 9090 | MCP, guardrails |

**Participant guide (step by step):** [`guide/SydneyWater_Flogo_Workshop_Guide.pdf`](guide/SydneyWater_Flogo_Workshop_Guide.pdf)
(also as `.docx`). Section 1 lists every prerequisite and how to check it.

## Quick start (Ubuntu lab VM)

```bash
# 1. Get the workshop and put the lab kit where the guide expects it (~/FlogoLab)
git clone -b sydney-water-workshop https://github.com/nshah-tibco/flogo-enterprise-hub.git ~/flogo-enterprise-hub
cp -r ~/flogo-enterprise-hub/workshops/sydney-water-flogo-workshop/lab-kit ~/FlogoLab
chmod +x ~/FlogoLab/*.sh ~/FlogoLab/*/*.sh ~/FlogoLab/cline/tools/*

# 2. Check the machine: VS Code, Flogo extension 2.26.x, Go 1.25.7+, curl, python3, network, free ports
bash ~/FlogoLab/prereq-check.sh

# 3. Open ~/FlogoLab in VS Code, install the Cline extension, choose OpenAI + gpt-4.1
#    (the OpenAI key is handed out on the day - never commit it)
```

Then follow the guide. Every lab has a **fast-track** solution in `lab-kit/solutions/` if you fall behind.

## What's in the lab kit (`lab-kit/` → `~/FlogoLab`)

| Path | Contents |
|---|---|
| `prereq-check.sh` | PASS/WARN/FAIL check of every prerequisite (`--no-net` skips network checks) |
| `lab1/` | `sample-requests.sh` (curl tests) and sample request bodies |
| `lab2/` | `leak-report-process.png` (the process diagram), `prompts.md` (Cline + FDA prompts), `test-leak.sh` |
| `lab3/` | `starter/SW_Water_MCP_Starter.flogo`, `prompts.md` (agent prompts), `test-mcp.sh` (MCP tests without an LLM), `presenter-demo.md`, `specs/` (OpenAPI spec of the Lab 1 + 2 APIs) |
| `solutions/` | Finished apps: `Lab1_SW_RainfallRisk.flogo`, `Lab2_SW_LeakReport.flogo`, `Lab3_SW_Water_MCP.flogo` |
| `cline/` | Cline MCP settings sample + rules for the Flogo Design Assistant, and the Flogo FDA skills setup (`setup-flogo-skills.sh`, `flogo-skills/`, `tools/`) |
| `lab*/prompts-fda-skills.md` | Optional: natural-language prompts that make Cline build each lab app end to end with the Flogo FDA skills (tested with gpt-4.1) |

## Notes

- Apps run in non-production mode (stop after 24 h) without a Flogo licence — fine for the workshop.
- Lab 3 needs the Lab 1 and Lab 2 apps running (use the solutions if needed).
- The Flogo Design Assistant is a Tech Preview: always review what it generates.
- More Flogo samples, MCP and agentic AI examples, and the full skills library are in this repository
  (`samples/`, `skills-library/`).
