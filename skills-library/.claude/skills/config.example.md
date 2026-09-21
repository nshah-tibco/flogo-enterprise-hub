# Environment Configuration

All skills reference this file for environment-specific values.

**This is a TEMPLATE. Copy it to `config.md` and fill in your own values:**

```
cp config.example.md config.md
```

`config.md` is git-ignored so your real credentials are never committed.
Never put real secrets in this template.

> **OS note:** the paths below are shown as **Windows** examples (`C:\…`, `.exe`).
> On **macOS/Linux** use POSIX paths and drop the `.exe` suffix — e.g. `psql`,
> `flogodesign-cli`, `flogobuild`, `tibcop` (often already on your `PATH`). The
> CLI tool paths (`FLOGODESIGN_CLI_PATH`, `FLOGOBUILD_PATH`, `TIBCOP_PATH`) are
> whatever `which <tool>` / `where <tool>` reports on your machine.

---

## PostgreSQL

| Key | Value |
|---|---|
| PSQL_PATH | `C:\Program Files\PostgreSQL\18\bin\psql.exe` (Windows) · `/usr/bin/psql` or `/opt/homebrew/bin/psql` (Linux/macOS) |
| PSQL_PATH_GITBASH | `/c/Program Files/PostgreSQL/18/bin/psql.exe` *(Git-Bash-on-Windows form; ignore on real Linux/macOS)* |
| PG_HOST | `localhost` |
| PG_PORT | `5432` |
| PG_USER | `postgres` |
| PG_PASSWORD | `<your-postgres-password>` |

---

## LLM Provider Connection  or LLM Client Activity Configuration
LLM Provider: OpenAI

API Key: <your-openai-api-key>

LLM Model: gpt-5.6
---

## Email Server, Username and app password

Server: smtp.gmail.com
Username: <your-email-address>
Port: 465
Password: <your-app-password>

---

## Agentic AI Use Cases (skills: `agentic-ai-use-case` / `agentic-ai-use-case-fda`)

| Key | Value |
|---|---|
| AGENTIC_USE_CASES_DIR | *(optional — leave unset)* |

Optional override — a path **relative to the repo root** (or an absolute path) to the
folder holding the reference Agentic AI use-case apps that the two agentic skills
clone/study. **Leave this unset** to use the built-in default `demos/Agentic_AI/`,
which is correct when the skills ship inside `flogo-enterprise-hub`. Set it only if
your reference apps live elsewhere — e.g. `skills-library/` is installed standalone in
another project. If the folder can't be found, the skills will ask you to point to it.

## Flogo VSCode Extension

| Key | Value |
|---|---|
| VSIX_FILE_PATH | `"C:\Users\<you>\Downloads\flogo-vscode-win32-x64-2.26.5-ENGR-001-3035.vsix"` |
| FLOGOBUILD_CONTEXT_NAME | `flogo-vscode-2.26.5-ENGR-001` |
| FLOGO_VERSION  | `2.26.5` |

---

## Flogo Design CLI (flogodesign-cli)

| Key | Value |
|---|---|
| FLOGODESIGN_CLI_PATH | `"C:\Users\<you>\.vscode\extensions\tibco.flogo-2.26.5-ENGR-001-3035\bin\flogodesign-cli.exe"` |
| FLOGODESIGN_CLI_VERSION | `v0.9.3` |

> The extension folder name is **version-specific** — do not hardcode it. The `fda`
> alias in [../../README.md](../../README.md) discovers the newest
> `flogodesign-cli` under your installed extension automatically; this row is for
> reference only. (Same idea for `FLOGOBUILD_PATH`.)


---

## Flogobuild CLI

| Key | Value |
|---|---|
| FLOGOBUILD_PATH | `C:\tibco\TIB_flogo-app-build-cli_1.0.6\windows_amd64\flogobuild.exe` |
| FLOGOBUILD_VERSION | `v1.0.6` |

---

## TIBCO Platform CLI (tibcop)

| Key | Value |
|---|---|
| TIBCOP_PATH | `C:\tibco\tibco-platform-cli_1.8.0-win-amd64\tibcop.exe` |
| TIBCOP_VERSION | `v1.8.0` |
| CP_URL | `https://tibcopm.us-west.my.tibco.com` |
| DATAPLANE_NAME | `<your-dataplane-name>` |
| TIBCOP_TOKEN | `<your-platform-token>` |

---

## Flogo License

| Key | Value |
|---|---|
| LICENSE_FILE_PATH | `C:\Work\MyflogoLicence_ANY.bin` |

---

## Output Directory

| Key | Value |
|---|---|
| FLOGO_APPS_DIR | `../../../Flogo_Apps` |

> Path is **relative to this `config.md`** (which lives at
> `skills-library/.claude/skills/`), so `../../../Flogo_Apps` resolves to
> `Flogo_Apps/` at the repo root. Use an absolute path if you prefer.
