# Petragentic — Local Development Guide

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker Desktop | 4.x+ | Build and run containers |
| Python | 3.11+ | Run tests without Docker |
| IBM Cloud CLI | Latest | Cluster access, secrets |
| `oc` / `kubectl` | 4.x+ | OpenShift interactions |
| `gh` | Latest | GitHub Actions triggers |
| Terraform | 1.6+ | Infrastructure provisioning |

---

## Quick Start (Docker Compose)

```bash
# 1. Clone and enter the repo
git clone https://github.com/your-org/petragentic.git
cd petragentic

# 2. Copy env templates and fill in credentials
cp agent1/.env.example  agent1/.env
cp agent2/.env.example  agent2/.env
cp gateway/.env.example gateway/.env

# Edit each .env file with real watsonx.ai / watsonx.data / App ID credentials

# 3. Start all services
docker compose -f infra/docker-compose.yml up --build

# Services will be available at:
#   Gateway:  http://localhost:8080
#   Agent 1:  http://localhost:8001  (direct, no auth)
#   Agent 2:  http://localhost:8002  (direct, no auth)
```

---

## Run Tests (without Docker)

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test module
pytest tests/shared/ -v

# Run with coverage
pytest --cov=shared --cov=agent1 --cov=agent2 --cov=gateway --cov-report=term-missing
```

---

## Environment Variables Reference

See `.env.example` files in `agent1/`, `agent2/`, and `gateway/` directories.
Common required variables:

```
IBM_CLOUD_API_KEY=           # IBM Cloud IAM API key
WATSONX_PROJECT_ID=          # watsonx.ai project ID
WXDATA_PRESTO_URL=           # watsonx.data Presto REST endpoint
WXDATA_AUTH_TOKEN=           # watsonx.data bearer token
WXGOV_URL=                   # watsonx.governance endpoint
WXGOV_SPACE_ID=              # watsonx.governance deployment space
COS_API_KEY=                 # IBM COS HMAC API key
COS_INSTANCE_ID=             # IBM COS instance CRN
```

---

## Seed the watsonx.data Iceberg Tables

```bash
cd infra/seeds
pip install -r requirements.txt   # requests, python-dotenv

# Copy and configure runner env
cp .env.example .env
# Set WXDATA_PRESTO_URL and WXDATA_AUTH_TOKEN

python run_seeds.py
```

This creates all 4 Iceberg tables and loads the initial baseline data.

---

## Calling the API

### Get an App ID token (production)

```bash
TOKEN=$(curl -s -X POST \
  "https://us-south.appid.cloud.ibm.com/oauth/v4/<tenantId>/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=<clientId>&client_secret=<secret>" \
  | jq -r .access_token)
```

### Generate an integration design

```bash
curl -s -X POST http://localhost:8080/api/v1/design \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": "Send daily sales CSV from SAP ECC to IBM Db2 Warehouse",
    "source_system": "SAP ECC",
    "target_system": "IBM Db2 Warehouse",
    "integration_pattern": "batch",
    "data_volume_gb": 2.5,
    "sla_minutes": 60
  }' | jq
```

### Run a security audit

```bash
curl -s -X POST http://localhost:8080/api/v1/validate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "10.0.1.50",
    "server_class": "web-server",
    "scan_type": "new_server",
    "winrm_username": "svc_audit",
    "winrm_password": "your-password"
  }' | jq
```
