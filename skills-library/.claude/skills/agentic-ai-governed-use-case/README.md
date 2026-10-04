# Governed Agentic AI Use Case Builder for Flogo — User Guide

> Build an agentic AI demo where **the database decides and the agent reasons**. The skill first puts
> each operation through the Agentic AI decision framework, then builds the familiar three Flogo apps
> (WebSocket AI Orchestrator, MCP Server, A2A Agents). Identity, eligibility, prices and state changes
> are enforced in PostgreSQL. It proves all of that with a four-rung test ladder that ends in a real
> chat, including a prompt-injection attempt.

## When to use this vs. `agentic-ai-use-case`

| Use **agentic-ai-use-case** when… | Use **agentic-ai-governed-use-case** when… |
|---|---|
| you want a quick demo of MCP + A2A + orchestration | the audience will ask "what stops the model from doing X?" |
| the agent only looks things up | the agent acts on a user's **own** records, money or state |
| the data isn't sensitive | identity and per-user scoping matter |
| | you need a human-in-the-loop story that is real, not a prompt line |

## How to invoke it

- Slash command: `/agentic-ai-governed-use-case`, then describe the domain.
- Natural language: *"build a governed / production-grade / decision-framework agentic AI use case for
  &lt;vertical&gt;"*.

It will ask clarifying questions and show you the classification table and plan. **It builds nothing
until you approve.**

## What you get

`samples/Agentic_AI/<UseCase>_Use_Case/` (or your apps folder) containing:

| File | Purpose |
|---|---|
| `database.sql` / `reset_data.sql` | schema, **rule functions**, seeds (one row per reason code) / reset |
| `<Prefix>MCPServer.flogo` | scoped-read, guarded-write, two-step and review-case tools |
| `<Prefix>Agents.flogo` | the reasoning agent(s): read-only, minimised input |
| `<Prefix>AIOrchestrator.flogo` | WebSocket chat, AI Agent, per-connection memory |
| `README.md` | customer-facing: **"Why an agent here?"**, architecture, prerequisites, numbered steps to run, demo logins and script, troubleshooting |
| `prompts.md` | demo and adversarial prompts |
| `chat_e2e_transcript.md` | sanitized evidence from the last end-to-end run |
| `_rebuild/` | `tool_spec.py` (single source of truth), fda drivers, `test_rules.py`, `mcp_smoke.py`, `chat_e2e.py` |

## The test ladder

| Rung | What it proves |
|---|---|
| 1 `test_rules.py` | every SQL rule and reason code, using the exact tool SQL |
| 2 `validate_governed_apps.py` | wiring + governance: scoped reads, guarded writes, prompt hygiene, temperature, conn refs, WebSocket headers/conversationId, MCP hint booleans, secrets |
| 3 `mcp_smoke.py` | the rules hold at the MCP edge in the real Flogo runtime, no LLM |
| 4 `chat_e2e.py` | the whole system through a real chat, with assertions on DB state |

## Prerequisites

Same as `agentic-ai-use-case`: the Flogo Design CLI (`fda`), PostgreSQL + `psql`, an LLM API key, and
`skills-library/.claude/skills/config.md`. For rungs 3–4 you also need `flogobuild` (run
`flogobuild list-context` for the context name) and `pip install websocket-client`.

## Worked example

[Scholarly Publishing — Author Services](../../../../samples/Agentic_AI/Governed_Use_Cases/Scholarly_Publishing_Author_Services_Use_Case/README.md):
authors verify with ORCID + a code, check status, get journal suggestions from an agent, see APC
coverage computed in SQL, transfer a manuscript in two steps, and have fee waivers and appeals routed
to people.
