# Cyera Privacy Agent — Working Demo
### Use case: fulfilling a GDPR/CCPA erasure request for a field contractor's
### PII trapped in a legacy on-prem system

## Business Scenario

Meridian Grid Co. is a regulated utility. A field contractor (Jordan
Alvarez) submits a right-to-erasure request. Their PII — badge ID,
substation access list, phone number — lives in an on-prem PostgreSQL
HR/contractor database. That database isn't cloud-native, so agentless
SaaS-only privacy tools can't reach it, and no one wants to open an inbound
hole in the firewall just to let a vendor's scanner in.

This is exactly the deployment model Cyera built the **Privacy Agent** for:
a lightweight container the customer runs *inside their own environment*
(Kubernetes, ECS, Cloud Run — anywhere they already run workloads). It
makes only **outbound** connections to Cyera's platform, polls for pending
privacy tasks, executes them against internal systems through a connector,
and reports results back. Zero inbound exposure, no agent-initiated
connections into the customer's network from the outside — which is the
detail that actually matters to a security-conscious critical-infrastructure
customer.

## What's real vs. what's a stand-in

I don't have a live Cyera account/registry credentials, so I couldn't pull
their actual `rm-agent` image or talk to their actual backend. Rather than
fake it with screenshots, I built a **functionally equivalent system that
implements the same documented contract** and actually runs on Kubernetes:

| In this demo | Maps to (real Cyera product) |
|---|---|
| `agent/` container | **Cyera Privacy Agent** (`contairium.privacy.cyera.io/rm-agent`) — same responsibilities: authenticate with an API key, poll for tasks, execute, report back |
| `control-plane/` container | The **Cyera platform itself** — in production this doesn't run in the customer's cluster at all; it's Cyera's SaaS backend the agent polls over the internet |
| `connector/` container | A **Custom API Connection** — the thin adapter pattern Cyera documents for exposing an internal system to the agent |
| Postgres + seed data | Meridian Grid Co.'s legacy on-prem contractor/HR database |
| k8s Secret for the API key | Stand-in for what production wires through a real credentials manager (Vault, AWS Secrets Manager, etc.) via Cyera's `CredentialsManagerProvider` |

Everything in `agent/app.py` and `control-plane/app.py` mirrors the actual
polling contract described in Cyera's public integration docs
(`GET /v1/agent/tasks`, `POST /v1/agent/tasks/<id>/complete`, Bearer-token
auth) — so what you're demoing is the real architecture, with a stand-in
backend instead of production credentials.

## Architecture

```
                     ┌────────────────────────-─┐
   (real world:      │   Cyera Platform (SaaS)  │
    outside the      │   - privacy team submits │
    cluster) ────────│     DSARs here           │
                     │   - agent polls this     │◄── in this demo, stood in
                     └-─────────────────────────┘     by control-plane/ pod
                                  ▲  │
                          outbound│  │ tasks + results
                                  │  ▼
        ┌─────────────────────────────────────────────--─┐
        │  Customer's Kubernetes cluster (cyera-demo ns) │
        │                                                │
        │   ┌────────────────────┐                       │
        │   │ cyera-privacy-agent │──────┐               │
        │   └────────────────────┘       │               │
        │                                ▼               │
        │                        ┌──────────────┐        │
        │                        │  connector   │        │
        │                        │ (Custom API  │        │
        │                        │  Connection) │        │
        │                        └──────┬───────┘        │
        │                               ▼                │
        │                        ┌──────────────┐        │
        │                        │   postgres   │        │
        │                        │ (meridian_hr)│        │
        │                        └──────────────┘        │
        └──────────────────────────────────────────────--┘
```

## Running it

Requires: podman, `kubectl` with a cluster already running.

```bash
cd cyera-demo

# 1. Build the three demo container images and push them to container registry
make build

# 2. Deploy everything
# Deploy an EKS cluster first
make deploy-cluster

# Update local kubeconfig
make update-kubeconfig 

# Deploy workloads
make deploy-workloads

# 3. Run the live demo: submits a DSAR, watches the agent process it,
#    shows before/after state of the internal DB
make run
```

## What happens when demo runs

1. **BEFORE state** — Jordan Alvarez's full PII sitting in the internal DB,
   completely invisible to any tool that can't reach inside this cluster.
2. **DSAR submitted** — this is the moment a privacy team would click
   "New Request" in the real Cyera UI. In this demo it's a curl to
   `/admin/dsr`, deliberately standing in for that click.
3. **Agent polling loop** — point out that the agent found the task on its
   *next poll cycle*, not because anything pushed to it — it's a pull
   model, which is exactly why it needs no inbound network access.
4. **Connector execution** — the agent didn't touch Postgres directly; it
   called the connector's documented `/redact` contract. This is the seam
   a customer's own engineering team would build once, for their own
   internal systems, using Cyera's Custom API Connection spec.
5. **AFTER state** — PII fields redacted, record retained (for audit
   purposes) but no longer exposing the contractor's personal data.
6. **Close the loop** — mention that in production, this same task would
   show up as completed in the Cyera platform UI, with a full audit trail
   for compliance evidence (GDPR Article 17 accountability, in this case).

## Talking points if asked "why this use case"

- It's a **real, currently-shipping Cyera product** (not their core DSPM,
  which is agentless SaaS scanning — a different and much larger surface
  that isn't something a candidate can stand up in a take-home).
- It's genuinely **deployed the way the question asked**: on Kubernetes,
  inside a customer's own environment — matching Cyera's actual
  documented architecture for this component.
- It plays to real, defensible domain expertise: regulated,
  security-conscious environments where "no inbound exposure" isn't a nice-
  to-have, it's the reason a customer would pick this deployment model over
  a SaaS-only competitor at all.
- It shows you understand Cyera's product portfolio goes beyond DSPM into
  actual privacy operations (DSAR fulfillment) — which is a meaningfully
  different sale and different buyer (privacy/legal, not just security) than DSPM alone.

## Caveats worth understanding

- This is a simulation of the *integration contract*, not Cyera's actual
  code — say so plainly;
- The real agent's actual polling behavior, error handling, retry/backoff,
  and credentials-manager integrations are almost certainly more
  sophisticated than what's modeled here in ~150 lines of Python.
- If asked to extend it live, natural next steps: add the `access`
  (data export) request type to the demo script, show idempotent retry
  behavior if a poll cycle fails mid-task, or discuss how you'd handle
  multiple internal systems needing different connectors for the same DSAR.
