# Petragentic

> **Production-ready AI Agent platform on IBM Cloud** — two Granite-powered
> agents for enterprise integration design and Windows server security compliance.

[![CI](https://github.com/your-org/petragentic/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/your-org/petragentic/actions/workflows/build-and-test.yml)

---

## What is Petragentic?

Petragentic is a monorepo containing two autonomous AI agents deployed on
**Red Hat OpenShift on IBM Cloud (ROKS)**, secured behind a **FastAPI API Gateway**
with IBM App ID authentication.

| Agent | Description |
|---|---|
| **Agent 1 — Integration Design** | Accepts natural-language integration requirements and generates full end-to-end design documents using IBM Granite. Recommends the best approved tool (IBM Redwood, webMethods, Apache NiFi, Azure Logic Apps), protocol, data format, and authentication method. |
| **Agent 2 — Security Compliance** | Validates Windows server security baselines over WinRM/PSRemoting. Detects configuration drift against CIS Benchmark v3.0 + NIST 800-53 Rev 5 Gold Images, generates PowerShell remediation scripts, and produces HTML compliance reports. |
| **Orchestrate Agent** | Multi-turn ReAct (Reason + Act) orchestration layer using IBM Granite. Drives Agent 1 and Agent 2 as tools in a plan→act→observe loop. Supports combined tasks (e.g. "design an integration _and_ audit the target server"). Conversation memory is maintained per session. |

---

## Architecture

```
Internet
   │  HTTPS (TLS edge)
   ▼
OpenShift Route ──► gateway-svc:8080 (IBM App ID JWT auth)
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   agent1-svc:8001  agent2-svc:8002  orchestrate-svc:8003
   Integration        Security         ReAct loop
   Design             Compliance       (Granite + tools)
        │                 │               │
   watsonx.ai        watsonx.ai       watsonx.ai
   watsonx.data      watsonx.data      calls agent1+agent2
   COS artefacts     COS reports       as tools
   wx.governance     wx.governance
                      WinRM (via VPN)
```

All IBM Cloud service calls use **VPE gateways** — no public internet egress.
Secrets are injected at deploy time from **IBM Secrets Manager**.

---

## Repository Structure

```
petragentic/
├── agent1/                   # Integration Design & Automation (port 8001)
├── agent2/                   # Security Compliance & Audit (port 8002)
├── gateway/                  # API Gateway — IBM App ID auth, rate limiting (port 8080)
├── orchestrate/              # watsonx Orchestrate ReAct agent (port 8003)
│   ├── app/                  # FastAPI service (memory, tools, react_engine, routes)
│   ├── agents/               # Orchestrate agent YAML definition
│   └── skills/               # OpenAPI 3.1 specs + skill manifests for registration
├── shared/                   # Shared Python platform library
│   ├── config.py             # pydantic-settings BaseSettings
│   ├── logging.py            # Structured JSON logger + correlation ID
│   ├── exceptions.py         # 15 typed exception classes
│   ├── watsonx_client.py     # Granite inference wrapper
│   ├── wxdata_client.py      # watsonx.data Presto REST client
│   ├── cos_client.py         # IBM COS upload/download helpers
│   └── governance_logger.py  # watsonx.governance Factsheets logger
├── infra/
│   ├── openshift/            # ROKS Deployment, Service, ConfigMap, HPA, Route YAMLs
│   ├── seeds/                # Iceberg DDL + seed data SQL, Python seed runner
│   ├── terraform/            # IBM Cloud IaC (VPC, ROKS, COS, Secrets, IAM, watsonx)
│   └── docker-compose.yml    # Local development stack
├── tests/
│   ├── shared/               # Unit tests — exceptions, config, logging
│   ├── agent1/               # Unit tests — recommender, prompt builder
│   ├── agent2/               # Unit tests — drift detector, baseline comparator
│   ├── gateway/              # Unit tests — JWT auth, scope enforcement
│   └── e2e/                  # End-to-end API smoke tests
├── docs/
│   ├── api-reference.md      # Full REST API documentation
│   ├── runbook.md            # Operations runbook
│   └── local-dev.md          # Developer setup guide
└── .github/workflows/
    ├── build-and-test.yml    # PR gate: lint + pytest matrix
    ├── deploy-to-ibm-cloud.yml  # Push to main: build → ICR → VA scan → OCP deploy
    └── scheduled-audit.yml   # Daily 06:00 UTC cron audit
```

---

## IBM Cloud Components Used

| Component | Purpose |
|---|---|
| **watsonx.ai** (Granite-13b-chat, Granite-34b-code) | LLM inference for design documents and PowerShell remediation scripts |
| **watsonx.data** (Iceberg / Presto) | Learnable integration catalogue, Gold Image baselines, audit history |
| **watsonx.governance** (AI Factsheets) | Tool approval checks, model usage logging, bias/drift detection |
| **IBM App ID** | OIDC provider — JWT authentication for the API Gateway |
| **IBM Cloud Object Storage** | Report artefacts, generated design documents |
| **IBM Secrets Manager** | Runtime credential injection (no secrets in Git) |
| **ROKS** (Red Hat OpenShift on IBM Cloud) | Container orchestration, HPA, health probes |
| **IBM Container Registry** | Private container image registry with Vulnerability Advisor |
| **VPC + VPE Gateways** | Private connectivity to all IBM Cloud services |
| **VPN Gateway** | Site-to-site VPN to on-premises Windows servers for WinRM |

---

## Quick Start

See **[docs/local-dev.md](docs/local-dev.md)** for the full developer guide.

```bash
# Start the full stack locally (requires filled-in .env files)
docker compose -f infra/docker-compose.yml up --build

# Run tests
pytest

# Run tests with coverage
pytest --cov=shared --cov=agent1 --cov=agent2 --cov=gateway
```

---

## CI/CD

| Workflow | Trigger | What it does |
|---|---|---|
| `build-and-test.yml` | Pull Request | flake8 lint + pytest matrix [shared, agent1, agent2, gateway] |
| `deploy-to-ibm-cloud.yml` | Push to `main` | Docker build → push to ICR → VA scan → Secrets Manager pull → OCP rolling deploy |
| `scheduled-audit.yml` | Daily 06:00 UTC + manual | Fetch server inventory → POST /validate for each host → fail on HIGH findings |

---

## API Reference

See **[docs/api-reference.md](docs/api-reference.md)** for the full REST API documentation
including request/response schemas, required scopes, and error codes.

---

## Operations

See **[docs/runbook.md](docs/runbook.md)** for:
- Deployment and rollback procedures
- Log access and correlation ID tracing
- Secrets rotation
- HPA scaling configuration
- Incident response playbooks

---

## Architecture Plan

The living architecture plan, decisions log, and risk register are in
**[petragentic-architecture-plan.md](petragentic-architecture-plan.md)**.

---

## Contributing

1. Branch from `main` — naming: `feature/<topic>` or `fix/<issue>`
2. Run `pytest` and `flake8` locally before pushing
3. Open a pull request — the CI gate runs automatically
4. Squash-merge to `main` after review
