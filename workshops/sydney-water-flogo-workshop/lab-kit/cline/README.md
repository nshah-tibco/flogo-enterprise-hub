# Cline setup files (Sydney Water Flogo Workshop, Ubuntu lab VMs)

| File | Where it goes |
|---|---|
| `cline-rules-flogo-fda.md` | `~/FlogoLab/.clinerules/cline-rules-flogo-fda.md` (workspace rules, auto-loaded when `~/FlogoLab` is the open folder) |
| `cline_mcp_settings.sample.json` | Template for Cline's MCP settings (two servers: `flogo-fda-lab2`, `sw-water-mcp`) |
| `print-mcp-settings.sh` | Prints that JSON with **this VM's** real paths filled in — what participants use |

## Participants: one command

```bash
bash ~/FlogoLab/cline/print-mcp-settings.sh
```

Copy the JSON it prints. In Cline click the **MCP Servers** icon (stacked servers, top of the Cline panel) →
**Configure** tab → **Configure MCP Servers** (bottom). Replace the whole file with the JSON and save.
`flogo-fda-lab2` turns green; `sw-water-mcp` stays red until the Lab 3 app runs on port 9090.

## Filling the template by hand

Replace `<USER>` (your Linux user name, `whoami`) and `<EXT_DIR>` (the Flogo extension folder, which carries the
version and build, e.g. `tibco.flogo-2.26.8-NNNN`). JSON needs absolute paths — `~` is **not** expanded.
Print the real path of the Flogo Design Assistant binary:

```bash
ls -d ~/.vscode/extensions/tibco.flogo-2.26.*/bin/flogodesign-cli
```

If it is not executable (Cline shows `flogo-fda-lab2` red with "permission denied"):

```bash
chmod +x ~/.vscode/extensions/tibco.flogo-2.26.*/bin/flogodesign-cli
```

## Where Cline keeps the file (checked against cline/cline v4.1.26 source, 2 Nov 2026)

- **Current Cline (4.x):** `~/.cline/data/settings/cline_mcp_settings.json` — shared by the VS Code extension, the CLI
  and JetBrains (`apps/vscode/src/sdk/SdkController.ts`; override with `CLINE_DIR`).
- **Older Cline builds:** `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
  (the extension's global storage). Current builds migrate that file once into `~/.cline/data/settings/`
  (`apps/vscode/src/hosts/vscode/mcp-settings-legacy-migration.ts`).
- Always prefer the UI path (**MCP Servers → Configure → Configure MCP Servers**): it opens whichever file the installed
  version actually uses.

## Notes (docs.cline.bot and cline/cline source)

- Cline 4.1.26 (`saoudrizwan.claude-dev`, released 26 Oct 2026) requires **VS Code ^1.101.0**
  (`apps/vscode/package.json` → `engines.vscode`).
- `"type": "streamableHttp"` is **required** for `sw-water-mcp`; a server with a `url` and no `type` defaults to the
  legacy SSE transport and will not connect to Flogo's `/mcp` endpoint.
- `"type": "stdio"` is optional (a `command` implies stdio) but valid.
- `timeout` is in **seconds** (default 60, range 1–3600).
- MCP auto-approve is the single **Use MCP servers** switch in Auto Approve settings. Leave it off in the workshop so
  participants see each tool call.
- `sw-water-mcp` sends `Authorization: Bearer sw-workshop-key` from the start. That is harmless before guardrail 1 (no
  auth on the starter) and exactly what the server expects after it. A wrong key gets HTTP 500 "invalid API key".
- Not tested in Cline itself on the lab VM: plain-HTTP `http://localhost` with `streamableHttp` (the server side was
  verified with a Python MCP client).

## Second route: Cline + the FDA *skills* (fda command line, no MCP server)

Prompts that build each lab app from scratch: `lab1/prompts-fda-skills.md`, `lab2/prompts-fda-skills.md`,
`lab3/prompts-fda-skills.md` (verified with gpt-4.1 in a Cline emulator, 2 Nov 2026).

| File | What it is |
|---|---|
| `flogo-skills/` | The skills `fda`, `fda-mapping`, `flogobuild`, `flogo-unit-testing` (+ `config.example.md`, placeholders only), from flogo-enterprise-hub `skills-library` (PR #124 state). One change: the `fda` skill's frontmatter `name` is `fda` (was `flogo-design-assistant`), because Cline requires the name to equal the folder name. |
| `flogo-skills.clinerules.md` | The rules Cline needs instead of skills-library's `AGENT.md` (Cline does not read `AGENT.md`): run fda via `tools/fda`, change `.flogo` only with fda, the designer-only rules, verified fda recipes for REST/MCP triggers, links, Invoke REST and Return. |
| `setup-flogo-skills.sh` | Copies the skills to `~/FlogoLab/.claude/skills/` and the rules to `~/FlogoLab/.clinerules/flogo-skills.md`, checks fda. |
| `tools/fda` | Finds `flogodesign-cli` in the newest `~/.vscode*/extensions/tibco.flogo-*` and runs it. |
| `tools/fda-link` | Creates a link and sets its type (success / expression + condition / exprOtherwise / error) with fda, without counting `links[N]` positions. |
| `tools/flogo-encrypt` | Prints the `SECRET:` value for a password app property (`flogo-vscode-cli secret encrypt`). |
| `tools/validate_flogo_apps.py` | The skills-library static validator (designer-only rules); needs `python3`. |

Do not enable `cline-rules-flogo-fda.md` (the MCP route) at the same time: it tells Cline to use the FDA MCP tools.
