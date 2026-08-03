#!/usr/bin/env bash
# Launch the app against the local mock Alfresco, cleanly.
# Usage (Git Bash):  ./run_with_mock.sh
set -e
APPDIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/3] killing any stale instances on :8068 ..."
for pid in $(netstat -ano | grep ":8068" | grep -i listen | awk '{print $NF}' | sort -u); do
  taskkill //F //PID "$pid" 2>/dev/null || true
done
taskkill //F //IM alfresco_download_flogo_win.exe 2>/dev/null || true
sleep 1

echo "[2/3] starting mock Alfresco on :9090 ..."
python "$APPDIR/test/mock_alfresco.py" &
MOCK_PID=$!
sleep 2

echo "[3/3] starting Flogo app on :8068 (pointed at mock) ..."
export FLOGO_APP_PROPS_ENV=auto
export Alfresco_ServiceEndpoint='http://127.0.0.1:9090/alfresco/service/trafigura/1_3/contentRetrieve/workspace/SpacesStore/{nodeRef}'
export Alfresco_Username='SVC.ofcs.qa'
export Alfresco_Password='changeit'
echo "    endpoint = $Alfresco_ServiceEndpoint"
echo "    (mock PID $MOCK_PID — Ctrl-C stops the app; then: taskkill //F //PID $MOCK_PID)"
cd "$APPDIR/builds"
./alfresco_download_flogo_win.exe
