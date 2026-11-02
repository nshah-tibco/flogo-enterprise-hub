#!/usr/bin/env bash
# Lab 2 - test your SW_LeakReport app (POST http://localhost:9998/leak-reports) with curl.
#
#   bash test-leak.sh
#
# Contract: request {reportId, address, suburb, description, severity}
#           reply   201 {reportId, workOrderRef, priority, status}
#           severity HIGH -> P1, MEDIUM -> P2, anything else -> P3; workOrderRef = "WO-" + reportId; status RECEIVED
# Override the endpoint with LAB2_URL=..., python with PYTHON=...
set -u
URL="${LAB2_URL:-http://localhost:9998/leak-reports}"
PY="${PYTHON:-python3}"
FAILS=0
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT

check() {  # check <reportId> <severity> <expected priority> <address> <suburb> <description>
  local body code
  body="{\"reportId\":\"$1\",\"address\":\"$4\",\"suburb\":\"$5\",\"description\":\"$6\",\"severity\":\"$2\"}"
  echo "== $1 severity $2"
  code="$(curl -s -o "$OUT" -w '%{http_code}' -X POST "$URL" \
          -H 'Content-Type: application/json' --data "$body")" || { echo "   curl failed - is Lab 2 running on port 9998?"; FAILS=$((FAILS+1)); return; }
  echo "   HTTP $code  $(cat "$OUT")"
  if "$PY" - "$OUT" "$code" "$1" "$3" <<'PYEOF'
import json, sys
path, code, rid, prio = sys.argv[1:5]
r = json.load(open(path))
ok = (code == "201" and r.get("reportId") == rid and r.get("workOrderRef") == "WO-" + rid
      and r.get("priority") == prio and r.get("status") == "RECEIVED")
sys.exit(0 if ok else 1)
PYEOF
  then echo "   PASS  201, WO-$1, priority $3, RECEIVED"
  else echo "   FAIL  expected 201 {reportId:$1, workOrderRef:WO-$1, priority:$3, status:RECEIVED}"; FAILS=$((FAILS+1)); fi
}

check LR-1001 HIGH   P1 "12 Church St" "Parramatta" "Water bubbling up through the footpath"
check LR-1002 MEDIUM P2 "4 Smith St"   "Burwood"    "Steady trickle from the water meter pit"
check LR-1003 LOW    P3 "7 King St"    "Newtown"    "Damp patch on the nature strip after a dry week"

echo
echo "Your Lab 2 terminal should show, for each call: 'Leak report LR-100x at ...', 'AUDIT leak-report ...' and"
echo "'Work order created: WO-LR-100x'. To see the work order the Field Service SaaS receives, set the app property"
echo "FieldService.URL to your https://webhook.site/<id> URL and run this again."
[ "$FAILS" = 0 ] && echo "== ALL CHECKS PASSED" || echo "== $FAILS CHECK(S) FAILED"
exit "$FAILS"
