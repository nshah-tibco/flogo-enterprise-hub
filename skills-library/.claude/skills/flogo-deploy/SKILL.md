---
name: flogo-deploy
description: Deploy a TIBCO Flogo application to the TIBCO Platform. Provide the flogo app file path and the target dataplane name.
user-invocable: true
---

# Deploy a Flogo Application to the TIBCO Platform

This skill builds a `.flogo` application into a TIBCO Platform deployment zip with the
`flogobuild` CLI, then imports and deploys it to a dataplane using the `tibcop` CLI.

## Before You Start — Read the Config

Always read `skills-library/.claude/skills/config.md` first for the values below. Print each
CLI's path and version before running it. Never run `flogobuild`/`tibcop` in the background —
the user wants real-time output.

| Config key | Used for |
|---|---|
| `FLOGOBUILD_PATH` | building the deployment zip and managing build contexts |
| `FLOGO_VERSION` | the target Flogo version (e.g. `2.26.5`) |
| `VSIX_FILE_PATH` | the Flogo VSCode extension VSIX used to create the build context |
| `TIBCOP_PATH` | importing and deploying to the platform |
| `CP_URL` / `DATAPLANE_NAME` | the target control plane and dataplane |

**Flogo version:** Use the `FLOGO_VERSION` value from config (e.g. `2.26.5`). If it is missing,
fall back to the version embedded in `VSIX_FILE_PATH`. If you still cannot determine it, **ask the user**.

**VSIX file:** Use the **latest** `VSIX_FILE_PATH` in the config. If it is missing from the config
or the file does not exist on disk, **ask the user** for the VSIX file path.

## Deployment Steps

### Step 1: Locate the Flogo app file

Find the `.flogo` file. If the user provides just an app name, look for it in the configured apps
folder (e.g. `./Flogo_Apps/<appName>.flogo`) first, then search the project.

### Step 2: Ensure a build context exists (create from the config VSIX)

List existing contexts:

```shell
flogobuild list-context
```

If there is no context matching the config's VSIX/Flogo version, create one from the config's
`VSIX_FILE_PATH` and set it as default:

```shell
flogobuild create-context -n <CONTEXT_NAME> -v "<VSIX_FILE_PATH>" --set-default
```

**Context name rules** (the CLI rejects invalid names): must start with a letter; may contain only
letters, digits, underscores, and hyphens (**no dots**); length 3–30 chars. Derive a valid name
from the VSIX version — e.g. VSIX `...-2.26.5-ENGR-001-...vsix` → context `flogo-vscode-2265-ENGR-001`.
(The `FLOGOBUILD_CONTEXT_NAME` in config may contain dots and be invalid — sanitize it.)

If the VSIX is not in config or the file is missing, **ask the user** for the VSIX path.

### Step 3: Build the TIBCO Platform deployment zip

Create the output directory first — the build fails with "Output directory does not exist" if it
is absent:

```shell
mkdir -p <OUTPUT_DIR>
flogobuild build-tp-deployment -f "<PATH_TO_FLOGO_FILE>" -c <CONTEXT_NAME> -o "<OUTPUT_DIR>" -z <APP_NAME>.zip
```

### Step 4: Import the build to the control plane

The zip is a **positional** argument (not `--file`):

```shell
tibcop flogo:import-build "<OUTPUT_DIR>/<APP_NAME>.zip" --profile <PROFILE> --dataplane-name <DATAPLANE_NAME> --json
```

This returns a `buildId`. Capture it for the next steps.

### Step 5: Generate values.yaml from the build

```shell
tibcop flogo:generate-values-from-build --build-id <BUILD_ID> --profile <PROFILE> --dataplane-name <DATAPLANE_NAME> --output-dir "<OUTPUT_DIR>"
```

The generated `values.yaml` has `appConfig.appId: ""` (fresh deploy) and `replicaCount: 0`, so the
app deploys **without starting**.

### Step 6: (Optional) Set the app name in values.yaml

If the user wants a custom app name, update **both** fields before deploying:

- `appConfig.originalAppName` — the display name in the platform
- `fullnameOverride` — the runtime (Kubernetes release) name

### Step 7: Deploy using deploy-app-release with EULA acceptance

**Important:** Use `deploy-app-release` (NOT `deploy-app`). `deploy-app` has no way to accept the
EULA — it always fails with `To deploy the app you must accept TIBCO End User Agreement (EUA)`,
and there is no `--eula` flag or payload field for it.

```shell
tibcop flogo:deploy-app-release "<OUTPUT_DIR>/values.yaml" --eula --profile <PROFILE> --dataplane-name <DATAPLANE_NAME> --json
```

This returns an `appId` and success status. Because `replicaCount` is 0, the app is deployed but
**not started**.

### Step 8: (Optional) Start the app — only if the user asks

Do **not** scale unless the user asks to start the app.

```shell
tibcop flogo:scale-app --app-id <APP_ID> --count 1 --profile <PROFILE> --dataplane-name <DATAPLANE_NAME> --json
```

### Step 9: Report results

Provide the user with the build ID, the app ID, the deployment status, and whether the app was
started (scaled to 1) or left stopped (0 replicas).

## Troubleshooting

- **`--json` hides the real error**: many `tibcop` commands print only `{"error":{"oclif":{"exit":2}}}`
  with `--json`. Re-run the **same command without `--json`** to see the actual message.
- **Authentication / `Refresh token expired`**: run `tibcop login --profile <PROFILE>` (opens a
  browser) to re-authenticate, then retry.
- **EUA error on `deploy-app`**: switch to `deploy-app-release` with `--eula` (see Step 7).
- **`Output directory does not exist`** during build: `mkdir -p` the output dir first (Step 3).
- **`invalid context name provided`**: the name has a dot or is out of the 3–30 char range — use
  only letters/digits/underscores/hyphens starting with a letter (Step 2).
- **Build failure**: check status with
  `tibcop flogo:get-build-status --profile <PROFILE> --dataplane-name <DATAPLANE_NAME> --build-id <BUILD_ID> --json`.
- **No flogo versions on the dataplane**: provision one with `tibcop flogo:provision-flogo-version`.
