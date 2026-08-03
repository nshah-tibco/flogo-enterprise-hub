# Environment Configuration

All skills reference this file for environment-specific values.

**This is a TEMPLATE. Copy it to `config.md` and fill in your own values:**

```
cp config.example.md config.md
```

`config.md` is git-ignored so your real credentials are never committed.
Never put real secrets in this template.

---

## PostgreSQL

| Key | Value |
|---|---|
| PSQL_PATH | `C:\Program Files\PostgreSQL\18\bin\psql.exe` |
| PSQL_PATH_UNIX | `/c/Program Files/PostgreSQL/18/bin/psql.exe` |
| PG_HOST | `localhost` |
| PG_PORT | `5432` |
| PG_USER | `postgres` |
| PG_PASSWORD | `<your-postgres-password>` |

---

## LLM Provider Connection  or LLM Client Activity Configuration
LLM Provider: OpenAI

API Key: <your-openai-api-key>

LLM Model: gpt-5.5
---

## Email Server, Username and app password

Server: smtp.gmail.com
Username: <your-email-address>
Port: 465
Password: <your-app-password>

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
