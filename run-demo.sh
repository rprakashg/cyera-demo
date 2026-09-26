#!/usr/bin/env bash
# Live demo script: submits a DSAR (erasure request) for Jordan Alvarez,
# waits for the agent to pick it up and process it, and shows the
# before/after state of the internal DB.
set -euo pipefail

echo "==> Port-forwarding control-plane and connector for local access..."
kubectl -n cyera-demo port-forward svc/control-plane 8081:8080 >/tmp/cp-pf.log 2>&1 &
CP_PID=$!
kubectl -n cyera-demo port-forward svc/connector 8082:8080 >/tmp/conn-pf.log 2>&1 &
CONN_PID=$!
sleep 3
trap "kill $CP_PID $CONN_PID 2>/dev/null || true" EXIT

echo ""
echo "==> BEFORE: current state of the internal contractor DB"
curl -s http://localhost:8082/debug/records | python3 -m json.tool

echo ""
echo "==> Submitting a right-to-erasure DSAR for jordan.alvarez@fieldpartner.com"
echo "    (this simulates a privacy team creating the request in the Cyera UI)"
TASK=$(curl -s -X POST http://localhost:8081/admin/dsr \
  -H "Content-Type: application/json" \
  -d '{"identifier": "jordan.alvarez@fieldpartner.com", "request_type": "erasure"}')
echo "$TASK" | python3 -m json.tool
TASK_ID=$(echo "$TASK" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo ""
echo "==> Waiting for the agent to poll, execute against the connector, and report back..."
for i in $(seq 1 15); do
  STATUS=$(curl -s "http://localhost:8081/admin/dsr/$TASK_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "    task status: $STATUS"
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 2
done

echo ""
echo "==> Final task record (as it would appear in the Cyera platform UI):"
curl -s "http://localhost:8081/admin/dsr/$TASK_ID" | python3 -m json.tool

echo ""
echo "==> AFTER: state of the internal contractor DB post-erasure"
curl -s http://localhost:8082/debug/records | python3 -m json.tool
