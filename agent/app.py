"""
Agent stand-in.
Maps directly to: the real Cyera Privacy Agent container
(contairium.privacy.cyera.io/rm-agent), which a customer deploys inside
their own Kubernetes/ECS/Cloud Run environment.

Real agent behavior, per Cyera's public docs, that this reproduces:
  1. Runs entirely inside the customer's environment (no inbound exposure -
     it only makes outbound calls).
  2. Authenticates to the Cyera platform with an API key pulled from a
     credentials manager / k8s Secret.
  3. Polls the platform for pending privacy tasks.
  4. Executes each task against the relevant internal system via a
     configured connector (here: the Custom API Connection to Meridian
     Grid Co.'s contractor DB).
  5. Reports the result back to the platform.
"""
import os
import time
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s agent %(message)s")
log = logging.getLogger(__name__)

CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "http://control-plane:8080")
CONNECTOR_URL = os.environ.get("CONNECTOR_URL", "http://connector:8080")
API_KEY = os.environ.get("AGENT_API_KEY", "demo-privacy-api-key")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "5"))

HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def poll_for_tasks():
    resp = requests.get(f"{CONTROL_PLANE_URL}/v1/agent/tasks", headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json().get("tasks", [])


def execute_task(task):
    identifier = task["identifier"]
    request_type = task["request_type"]
    log.info("Executing task %s: %s for %s", task["id"], request_type, identifier)

    if request_type == "access":
        r = requests.post(f"{CONNECTOR_URL}/search", json={"identifier": identifier}, timeout=10)
        r.raise_for_status()
        records = r.json()["records"]
        result = {"action": "access", "records_found": len(records), "records": records}

    elif request_type == "erasure":
        r = requests.post(f"{CONNECTOR_URL}/redact", json={"identifier": identifier}, timeout=10)
        r.raise_for_status()
        redacted = r.json()["redacted_records"]
        result = {"action": "erasure", "records_redacted": redacted}

    else:
        result = {"action": "unknown", "error": f"unsupported request_type {request_type}"}

    return result


def report_completion(task_id, result):
    requests.post(
        f"{CONTROL_PLANE_URL}/v1/agent/tasks/{task_id}/complete",
        headers=HEADERS,
        json={"result": result},
        timeout=10,
    )
    log.info("Reported completion for task %s", task_id)


def main_loop():
    log.info("Cyera Privacy Agent (demo) starting. Polling %s every %ss", CONTROL_PLANE_URL, POLL_INTERVAL)
    while True:
        try:
            tasks = poll_for_tasks()
            for task in tasks:
                result = execute_task(task)
                report_completion(task["id"], result)
        except Exception as e:
            log.error("Poll cycle error: %s", e)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main_loop()
