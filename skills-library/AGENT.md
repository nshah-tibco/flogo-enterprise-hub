# AGENT.md

You are a software integration developer that uses TIBCO Flogo to build integration applications (`.flogo` files).

Use the `fda` (Flogo Design Assistant) command line tool to create and modify these applications.
The available skills under `.claude/skills/` document how to use the relevant CLIs and provide step-by-step recipes for common patterns.

**NEVER UPDATE THE `.flogo` FILES DIRECTLY** — always use `fda`.

## Resolving the `fda` CLI

The `fda` binary (`flogodesign-cli`) ships inside the TIBCO Flogo VS Code extension. Its path changes with every extension update, so **always discover it dynamically** before running any `fda` command:

```bash
# 1. Check if fda is already on PATH (user may have set up an alias/function)
which fda 2>/dev/null

# 2. If not found, discover the latest version dynamically
HOME_DIR="${HOME:-$USERPROFILE}"
EXT_NAME="flogodesign-cli"

# Windows (Git Bash / msys / cygwin): binary has .exe extension
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
  EXT_NAME="flogodesign-cli.exe"
fi

# Search across VS Code variants (standard, Insiders, Remote/WSL)
for dir in "$HOME_DIR/.vscode/extensions" \
           "$HOME_DIR/.vscode-insiders/extensions" \
           "$HOME_DIR/.vscode-server/extensions"; do
  FDA_PATH=$(ls -td "$dir/tibco.flogo-"*/bin/"$EXT_NAME" 2>/dev/null | head -1)
  [ -n "$FDA_PATH" ] && break
done

# 3. Use the discovered path (quote it — the path may contain special characters)
"$FDA_PATH" version
```

**Never hardcode the extension folder name** (e.g. `tibco.flogo-2.26.6-2851`). The glob `tibco.flogo-*/bin/flogodesign-cli*` with `-td` (sort by newest) always resolves to the latest installed version.

If neither `which fda` nor the dynamic scan finds the binary, ask the user to install the TIBCO Flogo VS Code extension.

### Setting up a persistent `fda` alias

Add the function below to your shell startup file so `fda` is available in every terminal session:

| OS | Shell | File |
|---|---|---|
| Windows | Git Bash | `~/.bashrc` |
| macOS | zsh (default) | `~/.zshrc` |
| Linux | bash | `~/.bashrc` |

**Bash / Zsh function** (add to `~/.bashrc` or `~/.zshrc`):

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

**PowerShell function** (add to `$PROFILE`):

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

## Project conventions

- Always work with Flogo applications inside the `./Flogo_Apps/` folder.
- Always pass `-f <AppName>.flogo` on every `fda` command to target the correct file.
- To build applications, use the `flogobuild` CLI with the build context configured in `config.md` (`FLOGOBUILD_CONTEXT_NAME`).
- To deploy applications, use the `tibcop` (TIBCO Platform CLI) with the `flogo` topic and the platform credentials configured in `config.md` (`CP_URL`, `TIBCOP_TOKEN`, `DATAPLANE_NAME`).

## Configurable values for this project

All environment-specific values — build context, platform credentials, dataplane, database, LLM keys, and CLI paths — live in a **single source of truth**: [`.claude/skills/config.md`](.claude/skills/config.md). Read that file first; never duplicate these values across skills or in this document.

If `config.md` does not exist yet, copy the template and fill in your values:

```bash
cp .claude/skills/config.example.md .claude/skills/config.md
```

`config.md` is git-ignored, so your real credentials are never committed. Key values include `FLOGOBUILD_CONTEXT_NAME` (build context), `DATAPLANE_NAME`, `CP_URL` / `TIBCOP_TOKEN` (platform), plus the PostgreSQL, LLM, and email settings.

To list available `flogobuild` contexts: `flogobuild list-context`
To list configured `tibcop` profiles: `tibcop list-profiles`

## Testing locally

To run and test an application locally:

1. Add a timer trigger to a flow that executes the flow on startup.
2. Use log activities to log output to the console.
3. Build with `flogobuild build-exe -f <AppName>.flogo -c <FLOGOBUILD_CONTEXT_NAME> -o ./bin` (use the `FLOGOBUILD_CONTEXT_NAME` value from `config.md`).
4. Run the executable with a 5 second timeout: `timeout 5 ./bin/<AppName> 2>&1 || true` and read the output logs.
