---
name: agentic-ai-governed-use-case
description: Build a GOVERNED Agentic AI use case on TIBCO Flogo Enterprise, where business rules, identity, prices and state changes are enforced in PostgreSQL, not in prompts. It passes the Agentic AI decision framework (human-owned vs. agent vs. deterministic) before anything is built. Same three-app shape as agentic-ai-use-case (WebSocket AI Orchestrator + MCP Server + A2A Agents), but with scoped reads (FROM rule_fn(token)), guarded writes (INSERT … SELECT rule_fn → 0 rows when blocked), two-step propose/confirm for state changes, routed human review cases, session-token identity, per-connection conversation memory, keyword-only A2A agents, and a four-rung test ladder (SQL rules → static governance validator → MCP smoke → chat e2e with prompt injection). Use when the user asks for a "real-world", "production-grade", "governed", "decision-framework" or "safe" agentic AI demo, or when an agent must act on a user's own records, money or state. For a quick unguided demo, use agentic-ai-use-case instead.
user-invocable: true
metadata:
  author: Flogo Skills Author <author@example.com>
  version: "1.0.0"
  last-updated-date: "2026-10-04"
---

# Governed Agentic AI Use Case Builder

Builds an agentic AI demo that would survive a customer's architecture review: **agentic in the
middle, deterministic at the edges**. The LLM handles the conversation and the one genuinely semantic
step. The database decides identity, eligibility, prices and state changes. People decide anything
they must answer for.

It is a sibling of [`agentic-ai-use-case`](../agentic-ai-use-case/SKILL.md), which stays unchanged.
It reuses that skill's build machinery (fda recipes, the PostgreSQL activity contract, the base
validator, the manual-config gap) and changes **what** gets built:

| | agentic-ai-use-case | **agentic-ai-governed-use-case** |
|---|---|---|
| Starting point | a domain | a domain **+ the decision-framework gate** (every operation classified first) |
| Reads | one tool per table | **scoped** by a session token through a rule function |
| Writes | A2A agents write with LLM-chosen values | **guarded** MCP tools: `INSERT … SELECT rule_fn()`, plus readback of outcome and reason |
| State changes | one call | **two-step** propose → user yes → confirm (15-minute expiry, rules rechecked) |
| Exceptions | the model decides | **human-owned** `open_review_case`, routed by a table |
| A2A agents | action agents | reasoning agents with **minimised, read-only** input |
| Identity | none / trust the chat | `verify_*` → session token; per-connection `conversationId` |
| Done means | design-time validation | **4-rung test ladder**, including prompt injection |

**Worked example:** `samples/Agentic_AI/Scholarly_Publishing_Author_Services_Use_Case/`. Read its
`database.sql`, `_rebuild/tool_spec.py` and `README.md` before building a new one.

## Hard rules

Everything in the original skill's *Hard rules* applies: never regenerate a designer-touched `.flogo`,
never write to an open one, and use FDA mode with every structural change through `fda`. On top of
that:

1. **Gate first.** No design until every operation has an owner from
   [decision-framework-gate.md](references/decision-framework-gate.md). If you can't write the "Why an
   agent here?" paragraph, tell the user the use case doesn't need an agent.
2. **No rule in a prompt.** Filtering, arithmetic, eligibility, routing and "only show their own" are
   SQL. Prompts may *explain* outcomes. They never *produce* them.
3. **Every write is guarded.** Use `INSERT … SELECT * FROM <rule_fn>(…)`, never `VALUES`. Use an event
   row plus a trigger rather than an UPDATE. Always read back the outcome.
4. **The model never decides human-owned requests.** Open a case, give the case id and team, and say
   a person will decide.
5. **Honest AI.** The assistant says it is an AI when asked. Never write a prompt that hides it.
6. **Tests assert on DB state.** Text checks stay loose, because the wording varies (temperature 0 =
   provider default).
7. **Secrets.** Builds read secrets at run time (env or config.md). Never print config.md unredacted.
   Scrub the `.flogo` files before handing them over (Phase 6). Executables and their copies live
   outside the repo.
8. **Report honestly.** Report pass counts, retries and the known limitations every time. Never
   report a green run you didn't see.

## Reference files

| File | Read when |
|---|---|
| [references/decision-framework-gate.md](references/decision-framework-gate.md) | Phase 1: classify operations, write "Why an agent here?" |
| [references/governed-patterns.md](references/governed-patterns.md) | Phases 2–4: SQL shapes and the fda recipes that differ |
| [references/runtime-gotchas.md](references/runtime-gotchas.md) | Phases 4–5: wsserver headers, temperature, guardrails, LLM timeout, flogobuild context |
| [references/testing-ladder.md](references/testing-ladder.md) | Phase 5: the four rungs and how to run the apps |
| [references/spec-and-readme-template.md](references/spec-and-readme-template.md) | Phases 2 and 6: spec additions, README template |
| [references/validate_governed_apps.py](references/validate_governed_apps.py) | Phase 5: runs the base validator, then G1–G9 |
| [templates/_rebuild/fda_common.py](templates/_rebuild/fda_common.py) | Phase 4: `App` helper (`bake_pg`, `conn_ref`, `cap_empty`, connections) |
| Shared with the original skill: [fda-build-recipes](../agentic-ai-use-case/references/fda-build-recipes.md), [postgres-activity-patterns](../agentic-ai-use-case/references/postgres-activity-patterns.md), [fda-limitations](../agentic-ai-use-case/references/fda-limitations.md), [manual-config-gap](../agentic-ai-use-case/references/manual-config-gap.md), [connector-prereqs](../agentic-ai-use-case/references/connector-prereqs.md) | as in that skill |

## Workflow

### Phase 0: environment
Read `skills-library/.claude/skills/config.md` for the fda path, psql, PostgreSQL, LLM provider and
model. **Redact** passwords and keys before echoing anything. Run `flogobuild list-context` and record
the real context name; config.md's value can be stale (runtime-gotchas.md §7). Pick the output folder:
`samples/Agentic_AI/<UseCase>_Use_Case/` for a catalogue demo.

### Phase 1: frame and gate
Name the persona and the vertical. Use fictional organisations, and never a customer's name on
screen. List the operations and classify each one (Q1 human? Q2 semantic?). Check that the catalogue
doesn't already cover the vertical (`samples/Agentic_AI/README.md`).

### Phase 2: spec
Fill in the spec with the governed additions: identity and scope, the classification, rules with
reason codes and a seed row per code, two-step actions, request types → teams, adversarial acceptance.

### Phase 3: plan, then gate on approval ⛔
Present the classification table, tools, agent, rules, ports and the demo script. Build nothing until
the user approves.

### Phase 4: build (FDA mode)
1. `database.sql` (schema + rule functions + seeds) and `reset_data.sql`. Load them.
2. `_rebuild/tool_spec.py`: every tool's description, args, and guarded write + read SQL. This is the
   single source of truth.
3. `_rebuild/test_rules.py`: **run it and make it pass before generating any app** (rung 1).
4. `_rebuild/build_mcp.py`, `build_agents.py`, `build_orchestrator.py` drive `fda` through
   `fda_common.App`, following the sample's drivers. Each driver refuses to overwrite an existing app.
5. `prompts.md`.

### Phase 5: verify (the testing ladder, all four rungs)
Rung 1 `test_rules.py` → rung 2 `validate_governed_apps.py --local` + `fda cm -f` for each app →
build the exes in a scratch folder outside the repo → rung 3 `mcp_smoke.py` → reset the DB → rung 4
`chat_e2e.py` with `A2A_LOG` set. The user asking for an end-to-end test counts as the explicit
request to build binaries. Otherwise, stop at rung 2 and say so.

### Phase 6: hand over
1. Stop the exes. Reset the DB.
2. **Scrub the secrets** in the sample's `.flogo` files with surgical text replacement. Never
   round-trip through `json.dump`, because that reorders keys and rewrites unicode. API key →
   `sk-REPLACE-WITH-YOUR-OPENAI-KEY`, DB password → `SET_YOUR_DB_PASSWORD`.
3. Delete the scratch exes and `.flogo` copies.
4. Run `validate_governed_apps.py` **without** `--local` (G9 is now an error), plus a grep secret scan
   over the sample and the skill folders.
5. Write the README from the template. It is for customers and partners who want to **run** the demo:
   "Why an agent here?", architecture, prerequisites, numbered steps to run (database, the ⚠️ app
   properties per app, start order, chat client, demo logins and script, reset), troubleshooting.
   Keep test results, negative tests, limitations and file lists **out** of the README; they go in the
   report (step 7). Add a sanitized `chat_e2e_transcript.md`.
6. Add a catalogue row in `samples/Agentic_AI/README.md` and `samples/README.md`.
7. Report: what passed (with counts), retries, the limitations, and anything skipped. **End the report
   with "Test it in the chatbot"** from
   [chatbot-test.md](../agentic-ai-use-case/references/chatbot-test.md), filled in with this use case's
   `ws://localhost:<port><path>`. Include the ↻ click next to the URL box, which people miss. Don't commit
   unless asked.

## Top gotchas (full list in runtime-gotchas.md)

- **wsserver headers `schema://` → no headers at runtime.** Set them inline, and map `conversationId`
  from `Sec-Websocket-Key`, or every client shares one conversation and one verified token.
- **Temperature 0 = omitted**, not deterministic. Non-zero values break gpt-5.x and Claude 4.7+.
- **`redactSensitiveData=true` on the orchestrator masks the ORCID/code**, so no one can verify.
- **MCP hints need `--jsonValue`**, because `--type boolean` stores strings.
- **No LLM timeout in the AI Agent.** One hung call blocks that socket. The test retries once and
  reports it.
- **`fda` without `-f`** creates `flogo-project.flogo` in the current folder.
- **Placeholders can't repeat within one statement.** The write uses `?w_*` and the read uses `?r_*`.
