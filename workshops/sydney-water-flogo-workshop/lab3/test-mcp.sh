#!/usr/bin/env bash
# Lab 3 - test the SW_Water_MCP server with raw MCP JSON-RPC over HTTP (curl + python3, no SDK).
#
#   bash test-mcp.sh            # solution: API key required, guardrails expected to reject bad input
#   bash test-mcp.sh --no-key   # starter: no auth, no guardrails (everything is passed straight through)
#
# Needs Lab 1 (port 9999) and Lab 2 (port 9998) running, plus your Lab 3 app on port 9090.
# Override the endpoint with MCP_URL=http://host:port/mcp, the key with MCP_KEY=..., python with PYTHON=...
set -u

URL="${MCP_URL:-http://localhost:9090/mcp}"
KEY="${MCP_KEY:-sw-workshop-key}"
PY="${PYTHON:-python3}"
MODE=solution
[ "${1:-}" = "--no-key" ] && MODE=starter

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
SESSION=""
FAILS=0
ID=0

pass() { echo "  PASS  $*"; }
fail() { echo "  FAIL  $*"; FAILS=$((FAILS + 1)); }
info() { echo "  info  $*"; }

# post <json> [auth: yes|no|<token>] -> sets CODE, writes $TMP/body (JSON, SSE 'data:' unwrapped), $TMP/hdr
post() {
  local auth="${2:-yes}" args=(-s -o "$TMP/raw" -D "$TMP/hdr" -w '%{http_code}' -X POST "$URL"
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')
  if [ "$MODE" = solution ] && [ "$auth" = yes ]; then args+=(-H "Authorization: Bearer $KEY"); fi
  if [ "$auth" != yes ] && [ "$auth" != no ]; then args+=(-H "Authorization: Bearer $auth"); fi
  [ -n "$SESSION" ] && args+=(-H "Mcp-Session-Id: $SESSION")
  CODE="$(curl "${args[@]}" --data "$1")"
  local sid
  sid="$(tr -d '\r' < "$TMP/hdr" | awk -F': ' 'tolower($1)=="mcp-session-id"{print $2}')"
  [ -n "$sid" ] && SESSION="$sid"
  # Streamable HTTP may answer as SSE ("event: message" / "data: {...}"): keep the last data: payload.
  if grep -q '^data:' "$TMP/raw"; then grep '^data:' "$TMP/raw" | tail -1 | sed 's/^data: *//' > "$TMP/body"
  else cp "$TMP/raw" "$TMP/body"; fi
}

rpc() { ID=$((ID + 1)); post "{\"jsonrpc\":\"2.0\",\"id\":$ID,\"method\":\"$1\",\"params\":$2}"; }

# call <tool> <arguments-json> -> prints the tool result, sets ISERR=true|false and TEXT
call() {
  rpc tools/call "{\"name\":\"$1\",\"arguments\":$2}"
  local out
  out="$("$PY" - "$TMP/body" <<'PYEOF'
import json, sys
try:
    m = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    print("false\n(unparseable reply: %s)" % e); sys.exit()
if "error" in m:
    print("true\nJSON-RPC error: " + json.dumps(m["error"])); sys.exit()
r = m.get("result", {})
t = "".join(c.get("text", "") for c in r.get("content", []))
print(("true" if r.get("isError") else "false") + "\n" + t)
PYEOF
)"
  ISERR="$(echo "$out" | head -1)"
  TEXT="$(echo "$out" | tail -n +2)"
  echo "        -> HTTP $CODE isError=$ISERR: $TEXT"
}

# guard <label> <tool> <args>: solution must reject (isError + "Rejected by guardrail"); starter just passes through
guard() {
  echo "- $1"
  call "$2" "$3"
  if [ "$MODE" = solution ]; then
    if [ "$ISERR" = true ] && echo "$TEXT" | grep -q 'Rejected by guardrail'; then pass "rejected before the backend was called"
    else fail "expected 'Rejected by guardrail'"; fi
  else
    info "starter has no guardrail - this went straight to the backend"
  fi
}

echo "== Lab 3 MCP test ($MODE) against $URL"

if [ "$MODE" = solution ]; then
  echo "- G1: initialize WITHOUT an API key"
  SESSION=""; post '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test-mcp.sh","version":"1.0"}}}' no
  [ "$CODE" = 401 ] && pass "HTTP 401 ($(head -c 80 "$TMP/raw"))" || fail "expected HTTP 401, got $CODE"
  echo "- G1: initialize with a WRONG key (info only: the MCP SDK answers 500 'invalid API key')"
  SESSION=""; post '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test-mcp.sh","version":"1.0"}}}' wrong-key
  info "HTTP $CODE $(head -c 80 "$TMP/raw")"
  SESSION=""
fi

echo "- initialize$([ "$MODE" = solution ] && echo ' with Authorization: Bearer <key>')"
rpc initialize '{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test-mcp.sh","version":"1.0"}}'
if [ "$CODE" = 200 ] && [ -n "$SESSION" ]; then
  pass "HTTP 200, Mcp-Session-Id $SESSION, server $("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["result"]["serverInfo"])' "$TMP/body")"
else
  fail "initialize returned HTTP $CODE: $(head -c 200 "$TMP/raw")"; echo "Is the Lab 3 app running on $URL?"; exit 1
fi
post '{"jsonrpc":"2.0","method":"notifications/initialized"}'

echo "- tools/list"
rpc tools/list '{}'
"$PY" - "$TMP/body" <<'PYEOF'
import json, sys
tools = json.load(open(sys.argv[1], encoding="utf-8"))["result"]["tools"]
for t in tools:
    print("        %-22s %s" % (t["name"], json.dumps(t.get("annotations", {}))))
    print("        %-22s args: %s" % ("", ", ".join(t.get("inputSchema", {}).get("properties", {}))))
names = sorted(t["name"] for t in tools)
print("  " + ("PASS " if names == ["assess_rainfall_risk", "report_leak"] else "FAIL ") + " exactly 2 tools: " + ", ".join(names))
PYEOF

echo
echo "== G2 input validation (solution rejects WITHOUT calling Lab 1 / Lab 2)"
guard "assess_rainfall_risk forecastDays=14" assess_rainfall_risk \
  '{"siteId":"PS-102","siteName":"Parramatta Sewage Pumping Station SP0102","latitude":-33.815,"longitude":151.001,"forecastDays":14}'
guard "assess_rainfall_risk for a site in Melbourne (-37.81, 144.96)" assess_rainfall_risk \
  '{"siteId":"MEL-001","siteName":"Melbourne CBD","latitude":-37.81,"longitude":144.96,"forecastDays":3}'
guard "report_leak reportId=12345" report_leak \
  '{"reportId":"12345","address":"12 Church St","suburb":"Parramatta","description":"Water bubbling up through the footpath","severity":"HIGH"}'
guard "report_leak severity=URGENT" report_leak \
  '{"reportId":"LR-2002","address":"12 Church St","suburb":"Parramatta","description":"Water bubbling up through the footpath","severity":"URGENT"}'
guard "report_leak description too short ('leak')" report_leak \
  '{"reportId":"LR-2003","address":"12 Church St","suburb":"Parramatta","description":"leak","severity":"LOW"}'

echo
echo "== G3 PII masking: valid report_leak whose description has a phone number and an email"
echo "- report_leak LR-2001 (description: '... call me on 0412 345 678 or email jo.citizen@example.com')"
call report_leak '{"reportId":"LR-2001","address":"12 Church St","suburb":"Parramatta","description":"Water bubbling up through the footpath - call me on 0412 345 678 or email jo.citizen@example.com","severity":"HIGH"}'
if [ "$ISERR" = false ] && echo "$TEXT" | grep -q 'WO-LR-2001'; then pass "work order WO-LR-2001 created by Lab 2"
else fail "expected a reply with workOrderRef WO-LR-2001"; fi
if echo "$TEXT" | grep -q -E '0412|jo\.citizen'; then fail "reply contains PII"; fi
if [ "$MODE" = solution ]; then
  info "WHERE TO LOOK: your Lab 3 terminal shows the text that was sent to Lab 2, e.g."
  info "  report_leak LR-2001 forwarded to Lab 2 with description: Water bubbling up through the footpath - call me on [redacted] or email [redacted]"
  info "To see it arrive at the 'Field Service SaaS', set Lab 2's FieldService.URL to your https://webhook.site/<id> URL."
else
  info "starter: the phone number and email went to Lab 2 and on to Field Service unmasked (check the Lab 3 terminal log)."
fi

echo
echo "== Valid assess_rainfall_risk (PS-102, Parramatta, 3 days)"
call assess_rainfall_risk '{"siteId":"PS-102","siteName":"Parramatta Sewage Pumping Station SP0102","latitude":-33.815,"longitude":151.001,"forecastDays":3}'
if [ "$ISERR" = false ] && echo "$TEXT" | grep -q '"riskLevel"'; then pass "risk assessed by Lab 1"
else fail "expected a riskLevel from Lab 1"; fi

echo
if [ "$FAILS" = 0 ]; then echo "== ALL CHECKS PASSED ($MODE)"; else echo "== $FAILS CHECK(S) FAILED ($MODE)"; fi
exit "$FAILS"
