# Petragentic — Operations Runbook

## Table of Contents

1. [Service Overview](#1-service-overview)
2. [Deployment Procedure](#2-deployment-procedure)
3. [Health & Readiness Checks](#3-health--readiness-checks)
4. [Log Access](#4-log-access)
5. [Secrets Rotation](#5-secrets-rotation)
6. [Scaling](#6-scaling)
7. [Incident Response](#7-incident-response)
8. [Daily Audit Workflow](#8-daily-audit-workflow)
9. [Rollback Procedure](#9-rollback-procedure)
10. [Terraform Lifecycle](#10-terraform-lifecycle)

---

## 1. Service Overview

| Service | Namespace | Port | ClusterIP Service |
|---|---|---|---|
| Gateway | petragentic | 8080 | gateway-svc |
| Agent 1 | petragentic | 8001 | agent1-svc |
| Agent 2 | petragentic | 8002 | agent2-svc |

External traffic enters via the OpenShift **Route** (`gateway-route`) — TLS edge
termination, redirect HTTP → HTTPS. Only the gateway has a Route; agent services
are internal ClusterIP only.

---

## 2. Deployment Procedure

Deployments are driven by **GitHub Actions** (see `.github/workflows/deploy-to-ibm-cloud.yml`).

### Manual deploy (emergency)

```bash
# 1. Authenticate to IBM Cloud
ibmcloud login --apikey $IBMCLOUD_API_KEY -r us-south

# 2. Target the ROKS cluster
ibmcloud oc cluster config --cluster petragentic-cluster

# 3. Set namespace context
kubectl config set-context --current --namespace=petragentic

# 4. Apply latest manifests
kubectl apply -f infra/openshift/namespace.yaml
kubectl apply -f infra/openshift/gateway/
kubectl apply -f infra/openshift/agent1/
kubectl apply -f infra/openshift/agent2/

# 5. Force rollout (if image tag unchanged)
kubectl rollout restart deployment/gateway
kubectl rollout restart deployment/agent1
kubectl rollout restart deployment/agent2
```

### Rollout status

```bash
kubectl rollout status deployment/gateway -n petragentic
kubectl rollout status deployment/agent1  -n petragentic
kubectl rollout status deployment/agent2  -n petragentic
```

---

## 3. Health & Readiness Checks

```bash
# Liveness (returns 200 if pod is alive)
kubectl exec -n petragentic deploy/agent1 -- \
  python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/health').read())"

# Readiness (returns 503 if watsonx.ai or watsonx.data unreachable)
curl -sf https://<gateway-route>/ready

# All pods status
kubectl get pods -n petragentic -o wide
```

---

## 4. Log Access

Logs are structured JSON. Each log line includes `correlation_id`, `service`, and `level`.

```bash
# Stream all gateway logs
kubectl logs -f -n petragentic -l app=gateway

# Stream agent1 logs
kubectl logs -f -n petragentic -l app=agent1

# Filter for errors only
kubectl logs -n petragentic -l app=agent2 | grep '"level":"ERROR"'

# Trace a specific request by correlation ID
kubectl logs -n petragentic -l app=agent1 | grep '"correlation_id":"<uuid>"'
```

Log retention: IBM Log Analysis instance (`petragentic-logs`) stores 7 days of logs.

---

## 5. Secrets Rotation

All secrets live in **IBM Secrets Manager** (`petragentic-secrets`). The deployment
workflow injects them into OCP Secrets at deploy time.

### Rotate a secret

1. Update the secret value in IBM Secrets Manager (Cloud console or CLI):
   ```bash
   ibmcloud secrets-manager secret-version-create \
     --secret-id <secret-id> \
     --secret-version-prototype '{"payload":"<new-value>"}'
   ```

2. Re-run the deploy workflow to push new values into OCP Secrets:
   ```bash
   gh workflow run deploy-to-ibm-cloud.yml --ref main
   ```

3. Rolling restart is triggered automatically by the workflow. Verify:
   ```bash
   kubectl rollout status deployment/agent1 -n petragentic
   ```

---

## 6. Scaling

### Manual scale

```bash
kubectl scale deployment/agent1 --replicas=4 -n petragentic
```

### HPA configuration

Each service has an HPA configured via `infra/openshift/{service}/hpa.yaml`:

| Service | Min | Max | CPU Target |
|---|---|---|---|
| gateway | 2 | 8 | 65% |
| agent1  | 2 | 6 | 70% |
| agent2  | 2 | 6 | 70% |

Check current HPA status:

```bash
kubectl get hpa -n petragentic
```

---

## 7. Incident Response

### Service returns 502 (upstream error)

1. Check agent health: `kubectl get pods -n petragentic`
2. Check logs: `kubectl logs -n petragentic -l app=agent1 | grep ERROR`
3. Check watsonx.ai endpoint reachability from within the cluster:
   ```bash
   kubectl exec -n petragentic deploy/agent1 -- \
     python -c "import requests; print(requests.get('https://private.us-south.ml.cloud.ibm.com').status_code)"
   ```
4. Verify VPE gateway is healthy: IBM Cloud console → VPC → Endpoints.

### Compliance scan fails with `WinRMConnectionError`

1. Verify VPN gateway is up: IBM Cloud console → VPC → VPN gateways.
2. Test from agent2 pod: `kubectl exec -n petragentic deploy/agent2 -- nc -zv <target-ip> 5985`
3. Check Windows firewall and WinRM service on target server.

### watsonx.ai quota exceeded (429)

1. Check quota in IBM Cloud watsonx.ai dashboard.
2. Reduce request rate or upgrade the service plan.
3. Temporarily reduce agent replicas to shed load.

---

## 8. Daily Audit Workflow

The `scheduled-audit.yml` workflow runs at **06:00 UTC** and also supports
manual dispatch. It:

1. Fetches the list of registered Windows servers from watsonx.data.
2. Posts a `POST /api/v1/validate` for each server in the inventory.
3. Uploads HTML reports to COS bucket `petragentic-data`.
4. Fails the workflow if any server returns `HIGH` severity findings.

### Manual trigger

```bash
gh workflow run scheduled-audit.yml \
  --field host=10.0.1.50 \
  --field server_class=web-server
```

### Check last run

```bash
gh run list --workflow=scheduled-audit.yml --limit=5
```

---

## 9. Rollback Procedure

```bash
# View rollout history
kubectl rollout history deployment/agent1 -n petragentic

# Rollback to previous revision
kubectl rollout undo deployment/agent1 -n petragentic

# Rollback to specific revision
kubectl rollout undo deployment/agent1 --to-revision=2 -n petragentic

# Verify rollback
kubectl rollout status deployment/agent1 -n petragentic
```

---

## 10. Terraform Lifecycle

```bash
cd infra/terraform

# Plan changes
terraform plan -var-file=terraform.tfvars

# Apply (requires IBMCLOUD_API_KEY environment variable)
terraform apply -var-file=terraform.tfvars

# View outputs (cluster endpoint, COS bucket names, etc.)
terraform output

# Destroy (DANGER — confirm before running in production)
terraform destroy -var-file=terraform.tfvars
```

State is stored remotely in IBM Cloud Object Storage. The `terraform.tfvars.example`
shows all required variables. Never commit a real `terraform.tfvars` file.
