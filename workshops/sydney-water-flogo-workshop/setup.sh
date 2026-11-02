#!/usr/bin/env bash
# One-time setup after cloning. Run it from a VS Code terminal in this folder:
#
#   bash setup.sh             # Ubuntu lab VM (also works in Git Bash on Windows for a dry run)
#   bash setup.sh --no-net    # skip the internet checks of the prerequisite check
#
# It does three things and changes nothing else:
#   1. Makes ~/FlogoLab point to this folder, so every ~/FlogoLab path in the guide and prompts works.
#   2. Adds the two workshop MCP servers to Cline (flogo-fda-lab2 = Flogo Design Assistant for Lab 2,
#      sw-water-mcp = your Lab 3 server); other Cline MCP servers are kept, the old file is saved as .bak.
#   3. Runs the prerequisite check (Ubuntu only).
set -uo pipefail
WS="$(cd "$(dirname "$0")" && pwd)"
LINK="$HOME/FlogoLab"
WINDOWS=false
case "${OSTYPE:-}" in msys*|cygwin*) WINDOWS=true ;; esac

echo "Workshop folder: $WS"

# 1. ~/FlogoLab -> this folder
if [ "$(cd "$LINK" 2>/dev/null && pwd -P)" = "$(cd "$WS" && pwd -P)" ]; then
  echo "[1/3] ~/FlogoLab already points here"
elif [ -L "$LINK" ]; then
  ln -sfn "$WS" "$LINK" && echo "[1/3] ~/FlogoLab -> $WS (updated)"
elif [ -e "$LINK" ]; then
  echo "[1/3] WARN: $LINK already exists and is not a link to this folder. Rename it and run setup again,"
  echo "      otherwise the ~/FlogoLab paths in the guide point to the old folder."
elif $WINDOWS; then
  MSYS_NO_PATHCONV=1 cmd /c mklink /J "$(cygpath -w "$LINK")" "$(cygpath -w "$WS")" >/dev/null \
    && echo "[1/3] ~/FlogoLab -> $WS (junction)"
else
  ln -s "$WS" "$LINK" && echo "[1/3] ~/FlogoLab -> $WS"
fi

chmod +x "$WS"/*.sh "$WS"/lab*/*.sh "$WS"/cline/*.sh "$WS"/cline/tools/* 2>/dev/null

# 2. Cline MCP servers
PY="${PYTHON:-python3}"
WS_NATIVE="$WS"; $WINDOWS && WS_NATIVE="$(cygpath -w "$WS")"
"$PY" - "$WS_NATIVE" <<'EOF'
import glob, json, os, shutil, sys
ws = sys.argv[1]
home = os.path.expanduser("~")
exe = "flogodesign-cli.exe" if os.name == "nt" else "flogodesign-cli"
fda = os.environ.get("FDA_BIN")
if not fda:
    hits = []
    for base in (".vscode", ".vscode-server", ".vscode-insiders"):
        hits += glob.glob(os.path.join(home, base, "extensions", "tibco.flogo-2*", "bin", exe))
    hits.sort(key=os.path.getmtime)
    fda = hits[-1] if hits else None
if not fda:
    print("[2/3] FAIL: Flogo Design Assistant not found - install the TIBCO Flogo VS Code extension, then run setup again")
    sys.exit(0)
if os.name != "nt":
    os.chmod(fda, os.stat(fda).st_mode | 0o111)
servers = {
    "flogo-fda-lab2": {"type": "stdio", "command": fda,
                       "args": ["-f", os.path.join(ws, "lab2", "SW_LeakReport.flogo"), "mcp", "stdio"],
                       "env": {}, "disabled": False, "autoApprove": [], "timeout": 120},
    "sw-water-mcp": {"type": "streamableHttp", "url": "http://localhost:9090/mcp",
                     "headers": {"Authorization": "Bearer sw-workshop-key"},
                     "disabled": False, "autoApprove": [], "timeout": 60},
}
appdata = os.environ.get("APPDATA") or os.path.join(home, ".config")
paths = [os.path.join(home, ".cline", "data", "settings", "cline_mcp_settings.json")]
legacy = os.path.join(appdata, "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings",
                      "cline_mcp_settings.json")
if os.path.exists(legacy):
    paths.append(legacy)
for p in paths:
    data = {}
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
        except ValueError:
            data = {}
        shutil.copy2(p, p + ".bak")
    data.setdefault("mcpServers", {}).update(servers)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(f"[2/3] Cline MCP servers flogo-fda-lab2 + sw-water-mcp written to {p}")
print(f"      Flogo Design Assistant: {fda}")
EOF

# 3. Prerequisite check
if $WINDOWS; then
  echo "[3/3] Prerequisite check skipped on Windows (it checks an Ubuntu lab VM)"
else
  echo "[3/3] Prerequisite check"
  bash "$WS/prereq-check.sh" "$@"
fi

cat <<'MSG'

Next:
  - Install the Cline extension (Extensions view, search "Cline"), choose "Bring my own API key",
    API Provider OpenAI, model gpt-4.1, paste the workshop key, switch to Act mode.
  - In Cline's MCP Servers panel, flogo-fda-lab2 should be green (sw-water-mcp turns green once Lab 3 runs).
    If Cline was already open, reload the window (Ctrl+Shift+P > Developer: Reload Window).
  - Open guide/SydneyWater_Flogo_Workshop_Guide.pdf and start Lab 1.
MSG
