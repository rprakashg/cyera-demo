"""
Cyera Platform stand-in (control plane).
Maps directly to: the real Cyera SaaS backend the Privacy Agent polls.
https://integrations.privacy.cyera.io/docs/integrations/internal-systems-integrations/request-manager-agent/quick-start

This implements the same shape of contract described in Cyera's public docs:
  - Agent authenticates with a Bearer API key
  - Agent polls GET /v1/agent/tasks for pending work
  - Agent executes the task against the internal system via the connector
  - Agent reports completion back with POST /v1/agent/tasks/<id>/complete

/admin/* endpoints stand in for actions a privacy team would take in the
real Cyera UI (e.g. "Integration Network > Agents", submitting a DSAR).
"""
import os
import uuid
import logging
from datetime import datetime
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format="%(asctime)s control-plane %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

API_KEY = os.environ.get("AGENT_API_KEY", "demo-privacy-api-key")

# In-memory task store - fine for a demo control plane
TASKS = {}


def require_agent_auth():
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {API_KEY}"


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


# ---- Privacy team actions (stand-in for the Cyera platform UI) ----

@app.post("/admin/dsr")
def create_dsr():
    """Simulates a privacy team submitting a Data Subject Request in Cyera."""
    body = request.get_json(force=True)
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "id": task_id,
        "request_type": body.get("request_type", "erasure"),
        "identifier": body["identifier"],
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
    }
    log.info("New DSR created: %s (%s) for %s", task_id, body.get("request_type"), body["identifier"])
    return jsonify(TASKS[task_id]), 201


@app.get("/admin/dsr")
def list_dsr():
    return jsonify(list(TASKS.values())), 200


@app.get("/admin/dsr/<task_id>")
def get_dsr(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify(error="not found"), 404
    return jsonify(task), 200


# ---- Agent-facing API (this is the part that mirrors Cyera's real agent contract) ----

@app.get("/v1/agent/tasks")
def agent_poll():
    if not require_agent_auth():
        return jsonify(error="unauthorized"), 401
    pending = [t for t in TASKS.values() if t["status"] == "pending"]
    if pending:
        log.info("Agent polled: returning %d pending task(s)", len(pending))
    return jsonify(tasks=pending), 200


@app.post("/v1/agent/tasks/<task_id>/complete")
def agent_complete(task_id):
    if not require_agent_auth():
        return jsonify(error="unauthorized"), 401
    task = TASKS.get(task_id)
    if not task:
        return jsonify(error="not found"), 404
    body = request.get_json(force=True)
    task["status"] = "completed"
    task["result"] = body.get("result")
    task["completed_at"] = datetime.utcnow().isoformat()
    log.info("Task %s marked complete by agent: %s", task_id, task["result"])
    return jsonify(task), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
