#!/usr/bin/env bash
# Lab 1 - Rainfall Risk (SW_RainfallRisk, POST http://localhost:9999/rainfall-risk/assessments)
#
#   bash sample-requests.sh          # forecastDays 1, 3 and 7 for Parramatta pumping station PS-102
#   bash sample-requests.sh 3        # just one of them (1, 3 or 7)
#
# Weather is LIVE (Open-Meteo), so the risk level depends on the real forecast on the day: more forecastDays =
# more rain summed = higher risk. Thresholds (app properties): Risk.HighMm = 25, Risk.MediumMm = 5.
# Override the endpoint with LAB1_URL=..., python with PYTHON=...
set -u
URL="${LAB1_URL:-http://localhost:9999/rainfall-risk/assessments}"
PY="${PYTHON:-python3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DAYS="${1:-1 3 7}"
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT

for d in $DAYS; do
  f="$HERE/parramatta-${d}day.json"
  [ -f "$f" ] || { echo "no such sample: $f (use 1, 3 or 7)"; continue; }
  echo "== forecastDays=$d   (request: $(cat "$f"))"
  code="$(curl -s -o "$OUT" -w '%{http_code}' -X POST "$URL" \
          -H 'Content-Type: application/json' --data "@$f")" || { echo "   curl failed - is Lab 1 running on port 9999?"; continue; }
  echo "   HTTP $code"
  "$PY" -m json.tool "$OUT" 2>/dev/null | sed 's/^/   /' || cat "$OUT"
  echo
done

cat <<'EOF'
Expected shape (dry run 1 Nov 2026 - your values will differ):
  forecastDays=1 -> 200 {"riskLevel":"LOW",    "totalRainfallMm":2.9,  "inspectionRequested":false, "message":"Rainfall risk LOW - no inspection needed"}
  forecastDays=3 -> 200 {"riskLevel":"MEDIUM", "totalRainfallMm":19.2, "inspectionRequested":true,  "message":"Inspection requested in Field Service (HTTP 200)"}
  forecastDays=7 -> 200 {"riskLevel":"HIGH",   "totalRainfallMm":27.2, "inspectionRequested":true,  "message":"Inspection requested in Field Service (HTTP 200)"}

DRY DAY? Force a ticket: in the designer set App Property Risk.MediumMm = 0 and run again (any rain, even
0 mm, is then >= MEDIUM, so an inspection is raised). For a built executable use an environment override
(every "." in the property name becomes "_"):
  FLOGO_APP_PROPS_ENV=auto Risk_MediumMm=0 ./SW_RainfallRisk

ERROR BRANCH (GetForecast -> ReturnError, HTTP 502): set Weather.URL to https://api.open-meteo.invalid/v1/forecast
  (or FLOGO_APP_PROPS_ENV=auto Weather_URL=https://api.open-meteo.invalid/v1/forecast ./SW_RainfallRisk)
  -> 502 {"riskLevel":"UNKNOWN","inspectionRequested":false,"message":"Weather service unavailable: ... no such host"}

SEE THE INSPECTION REQUEST: open https://webhook.site, copy "Your unique URL", set FieldService.URL to it, call with
forecastDays=7 and watch the request arrive. webhook.site answers text/plain, so CreateInspection's Response Type
must be "text/plain" (it is in the solution) - with "application/json" the caller gets HTTP 400.
EOF
