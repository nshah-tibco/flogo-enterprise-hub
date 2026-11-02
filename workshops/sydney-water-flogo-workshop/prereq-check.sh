#!/usr/bin/env bash
# Sydney Water x TIBCO Flogo workshop - prerequisite check for the Ubuntu lab VM.
#   bash ~/FlogoLab/prereq-check.sh            # run in a VS Code terminal (so PATH matches what VS Code sees)
#   bash ~/FlogoLab/prereq-check.sh --no-net   # skip the internet checks
# Prints PASS / WARN / FAIL per check and exits non-zero if anything FAILs. Changes nothing.

KIT="${FLOGOLAB:-$HOME/FlogoLab}"
VSCODE_MIN="1.101.0"   # Cline 4.1.26 package.json engines.vscode "^1.101.0"
GO_MIN="1.25.7"        # TIBCO Flogo 2.26.x extension: Go go1.25.7 or above to build and run apps
NET=1; [ "${1:-}" = "--no-net" ] && NET=0

pass=0; warn=0; fail=0
if [ -t 1 ]; then G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; N=$'\e[0m'; else G=; Y=; R=; N=; fi
PASS() { printf '%sPASS%s  %s\n' "$G" "$N" "$*"; pass=$((pass+1)); }
WARN() { printf '%sWARN%s  %s\n' "$Y" "$N" "$*"; warn=$((warn+1)); }
FAIL() { printf '%sFAIL%s  %s\n' "$R" "$N" "$*"; fail=$((fail+1)); }
# ver_ge A B  -> true if version A >= version B
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }

echo "== Sydney Water Flogo workshop - prerequisite check ($(date '+%Y-%m-%d %H:%M'))"

# --- OS
if grep -qi ubuntu /etc/os-release 2>/dev/null; then
  PASS "OS: $(. /etc/os-release; echo "$PRETTY_NAME")"
else
  WARN "OS: not Ubuntu ($(. /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-unknown}")) - the guide assumes Ubuntu"
fi

# --- VS Code
if command -v code >/dev/null 2>&1; then
  v=$(code --version 2>/dev/null | head -n1)
  if [ -n "$v" ] && ver_ge "$v" "$VSCODE_MIN"; then PASS "VS Code $v (Cline needs >= $VSCODE_MIN)"
  else FAIL "VS Code '${v:-?}' is older than $VSCODE_MIN (Cline's minimum) - update VS Code"; fi
else
  FAIL "VS Code: 'code' command not found on PATH"
fi

# --- TIBCO Flogo extension (Linux build) + FDA binary
EXT=$(ls -d "$HOME"/.vscode/extensions/tibco.flogo-2.26.* 2>/dev/null | sort -V | tail -n1)
if [ -n "$EXT" ]; then
  PASS "Flogo extension: $(basename "$EXT")"
  FDA="$EXT/bin/flogodesign-cli"
  if [ -f "$FDA" ]; then
    if [ ! -x "$FDA" ]; then
      FAIL "FDA binary is not executable - fix with: chmod +x '$FDA'"
    elif out=$("$FDA" version 2>&1 | grep -m1 -iE '[0-9]+\.[0-9]+'); then
      PASS "Flogo Design Assistant runs: $(echo "$out" | tr -s ' ' | cut -c1-80)"
    else
      FAIL "FDA binary did not print a version: $FDA version"
    fi
  else
    FAIL "FDA binary not found: $FDA (is this the Linux build of the extension?)"
  fi
else
  FAIL "Flogo extension: no ~/.vscode/extensions/tibco.flogo-2.26.* folder (install the Linux .vsix 2.26.x)"
fi

# --- Go (the Flogo extension builds and runs apps with Go)
if command -v go >/dev/null 2>&1; then
  gv=$(go version | awk '{print $3}' | sed 's/^go//')
  if ver_ge "$gv" "$GO_MIN"; then PASS "Go $gv (>= $GO_MIN) at $(command -v go)"
  else FAIL "Go $gv is older than $GO_MIN"; fi
else
  FAIL "Go: 'go' not on PATH in this shell. Install Go >= $GO_MIN and put it on PATH for the desktop session (e.g. /etc/profile.d/go.sh), then log out/in"
fi
if [ "${TERM_PROGRAM:-}" != "vscode" ]; then
  WARN "Not running inside a VS Code terminal - re-run there to prove VS Code sees Go on its PATH"
fi

# --- GCC (recommended: production binaries)
if command -v gcc >/dev/null 2>&1; then PASS "GCC $(gcc -dumpversion)"
else WARN "GCC not found (recommended - Flogo docs require it for production binaries): sudo apt-get install -y build-essential"; fi

# --- curl, python3, browser
for t in curl python3; do
  if command -v "$t" >/dev/null 2>&1; then PASS "$t: $("$t" --version 2>&1 | head -n1 | cut -c1-60)"
  else FAIL "$t missing: sudo apt-get install -y curl python3"; fi
done
if command -v firefox >/dev/null 2>&1 || command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1; then
  PASS "Browser present (for webhook.site)"
else
  WARN "No Firefox/Chrome found - needed to open webhook.site"
fi

# --- Cline (students install it themselves)
if ls -d "$HOME"/.vscode/extensions/saoudrizwan.claude-dev-* >/dev/null 2>&1; then
  PASS "Cline installed: $(basename "$(ls -d "$HOME"/.vscode/extensions/saoudrizwan.claude-dev-* | sort -V | tail -n1)")"
else
  WARN "Cline not installed yet - you install it from the VS Code Marketplace (guide 1.3)"
fi

# --- Lab kit
missing=()
for f in lab1/parramatta-1day.json lab1/sample-requests.sh lab2/leak-report-process.png lab2/prompts.md \
         lab2/test-leak.sh lab3/starter/SW_Water_MCP_Starter.flogo lab3/test-mcp.sh lab3/prompts.md \
         cline/print-mcp-settings.sh .clinerules/cline-rules-flogo-fda.md \
         solutions/Lab1_SW_RainfallRisk.flogo solutions/Lab2_SW_LeakReport.flogo solutions/Lab3_SW_Water_MCP.flogo; do
  [ -e "$KIT/$f" ] || missing+=("$f")
done
if [ ${#missing[@]} -eq 0 ]; then PASS "Lab kit complete in $KIT"
else FAIL "Lab kit in $KIT is missing: ${missing[*]}"; fi

# --- Ports
for p in 9999 9998 9090; do
  if command -v ss >/dev/null 2>&1 && ss -ltnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$p\$"; then
    WARN "Port $p is in use (fine if it is your own running lab app; otherwise: fuser -k $p/tcp)"
  else
    PASS "Port $p free"
  fi
done

# --- Network egress (HTTPS)
if [ $NET -eq 1 ] && command -v curl >/dev/null 2>&1; then
  check_url() {  # name url  -> any HTTP status = reachable
    code=$(curl -s -o /dev/null -m 12 -w '%{http_code}' "$2" 2>/dev/null)
    if [ -n "$code" ] && [ "$code" != "000" ]; then PASS "Internet: $1 reachable (HTTP $code)"
    else FAIL "Internet: $1 NOT reachable ($2) - ask for egress to be allowed"; fi
  }
  check_url "api.open-meteo.com (Lab 1 weather)" "https://api.open-meteo.com/v1/forecast?latitude=-33.815&longitude=151.001&daily=precipitation_sum&forecast_days=1"
  check_url "webhook.site (field-service SaaS)" "https://webhook.site/"
  check_url "postman-echo.com (fallback SaaS)" "https://postman-echo.com/get"
  check_url "api.openai.com (Cline LLM)" "https://api.openai.com/v1/models"
  check_url "marketplace.visualstudio.com (install Cline)" "https://marketplace.visualstudio.com/"
  code=$(curl -s -o /dev/null -m 12 -w '%{http_code}' https://proxy.golang.org/ 2>/dev/null)
  if [ -n "$code" ] && [ "$code" != "000" ]; then PASS "Internet: proxy.golang.org reachable (HTTP $code)"
  else WARN "proxy.golang.org not reachable - not known to be needed; allow it if Flogo builds fail"; fi
fi

echo "== $pass PASS, $warn WARN, $fail FAIL"
[ $fail -eq 0 ]
