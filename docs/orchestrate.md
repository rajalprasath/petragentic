# watsonx Orchestrate Integration Guide

## Overview

Petragentic's migration to **watsonx Orchestrate** adds a multi-turn ReAct
(Reason + Act) agent layer that:

1. Accepts natural-language requests from users
2. Reasons step-by-step using **IBM Granite**
3. Dynamically calls Agent 1 (Integration Design) and Agent 2 (Security Compliance)
   as **Orchestrate skills**
4. Returns a structured final answer

---

## Architecture Before vs After

### Before (direct API calls)

```
User → Gateway → Agent 1 REST (single-shot)
                  └── watsonx.ai (one generate call)

User → Gateway → Agent 2 REST (single-shot)
                  └── watsonx.ai (one generate call)
```

### After (Orchestrate ReAct loop)

```
User → Gateway → Orchestrate Service ─── ReAct loop (Granite)
                       │                      │
                       ├── Tool call ──────► Agent 1 POST /design
                       ├── Tool call ──────► Agent 1 GET /catalogue/stats
                       ├── Tool call ──────► Agent 2 POST /validate
                       └── Tool call ──────► Agent 2 GET /report/{id}
```

**Agent 1 and Agent 2 are not changed** — they continue serving their existing
REST endpoints. The Orchestrate layer calls them as tools inside the reasoning loop.

---

## New Files

```
orchestrate/
├── Dockerfile                        # Multi-stage, port 8003, non-root uid 1001
├── requirements.txt                  # ibm-watsonx-ai, fastapi, httpx
├── .env.example                      # All required env vars with descriptions
├── agents/
│   └── petragentic_agent.yaml        # Orchestrate agent definition (UI/CLI import)
├── skills/
│   ├── skill_agent1.yaml             # Orchestrate skill manifest for Agent 1
│   ├── openapi_agent1.yaml           # OpenAPI 3.1 spec for Agent 1 (design + catalogue)
│   ├── skill_agent2.yaml             # Orchestrate skill manifest for Agent 2
│   └── openapi_agent2.yaml           # OpenAPI 3.1 spec for Agent 2 (validate + report)
└── app/
    ├── main.py                       # FastAPI app, lifespan, /health, /ready
    ├── config.py                     # OrchestrateSettings (pydantic-settings)
    ├── memory.py                     # In-process conversation MemoryStore
    ├── tools.py                      # Tool registry wrapping Agent 1/2 REST calls
    ├── react_engine.py               # ReAct engine: plan→act→observe loop over Granite
    ├── models/request.py             # ChatMessage schema
    ├── models/response.py            # ChatResponse, SessionInfo, AgentInfo schemas
    └── routes/agent.py               # POST /agent/chat, GET/DELETE /agent/session/{id}
```

---

## API Endpoints (via Gateway)

All endpoints require a valid IBM App ID Bearer JWT.

| Endpoint | Scope | Description |
|---|---|---|
| `POST /api/v1/agent/chat` | `agent:chat` | Send a message — returns Final Answer |
| `GET  /api/v1/agent/session/{id}` | `agent:read` | Inspect session turn count |
| `DELETE /api/v1/agent/session/{id}` | `agent:admin` | Clear session memory |
| `GET  /api/v1/agent/info` | `agent:read` | List registered tools |

### Example chat request

```bash
curl -X POST https://<gateway-route>/api/v1/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess-abc-123",
    "message": "Design an integration between SAP ECC and IBM Db2 Warehouse, then audit the target server WIN-DB-001."
  }'
```

### Example response

```json
{
  "session_id": "sess-abc-123",
  "answer": "## Integration Design\n\n**Recommended Tool**: IBM Redwood\n...\n\n## Server Audit\n\n**WIN-DB-001** — 3 findings (1 HIGH, 2 MEDIUM)\n...",
  "turn_count": 2,
  "responded_at": "2025-01-15T10:35:42Z"
}
```

---

## ReAct Loop Flow

The Orchestrate service drives IBM Granite through a structured reasoning loop:

```
Prompt (system + history + user message)
          │
          ▼ Granite output
    ┌─────────────────────────────────┐
    │ Thought: I need to design first │
    │ Action: generate_integration_design
    │ Action Input: {"requirement": "..."}
    └─────────────────────────────────┘
          │
          ▼ Engine calls Agent 1 POST /design
    ┌─────────────────────────────────┐
    │ Observation: {"recommended_tool":
    │   "IBM Redwood", ...}           │
    └─────────────────────────────────┘
          │
          ▼ Next Granite call
    ┌─────────────────────────────────┐
    │ Thought: Now audit the server   │
    │ Action: run_security_audit      │
    │ Action Input: {"servers": [...]}│
    └─────────────────────────────────┘
          │
          ▼ Engine calls Agent 2 POST /validate
    ┌─────────────────────────────────┐
    │ Observation: {"scan_id": "...", │
    │   "critical_findings": 0, ...}  │
    └─────────────────────────────────┘
          │
          ▼ Next Granite call
    ┌─────────────────────────────────┐
    │ Thought: I have enough info     │
    │ Final Answer: ## Integration... │
    └─────────────────────────────────┘
```

---

## Registered Tools

| Tool name | Calls | Purpose |
|---|---|---|
| `generate_integration_design` | `POST /design` on agent1-svc | Generate integration design doc |
| `get_catalogue_stats` | `GET /catalogue/stats` on agent1-svc | Historical tool usage context |
| `run_security_audit` | `POST /validate` on agent2-svc | Windows server baseline audit |
| `get_scan_report` | `GET /report/{id}` on agent2-svc | Retrieve previous audit report |

---

## Registering Skills in watsonx Orchestrate UI

1. Open IBM watsonx Orchestrate → **Skills** → **Add skill → Import from file**
2. Import `orchestrate/skills/openapi_agent1.yaml`
3. Import `orchestrate/skills/openapi_agent2.yaml`
4. Go to **Agents** → **New agent** → import `orchestrate/agents/petragentic_agent.yaml`
5. Set the server URL in each skill to your ROKS gateway route

### Or via CLI

```bash
# Install Orchestrate CLI
pip install ibm-watsonx-orchestrate-cli

# Login
orchestrate auth login --api-key $IBMCLOUD_API_KEY --instance-url $ORCHESTRATE_URL

# Register skills
orchestrate skills apply -f orchestrate/skills/skill_agent1.yaml
orchestrate skills apply -f orchestrate/skills/skill_agent2.yaml

# Register agent
orchestrate agents apply -f orchestrate/agents/petragentic_agent.yaml
```

---

## IBM App ID Scopes to Add

Add these scopes to your App ID application:

| Scope | Purpose |
|---|---|
| `agent:chat` | POST /api/v1/agent/chat |
| `agent:read` | GET session, info |
| `agent:admin` | DELETE session |

---

## Environment Variables

See `orchestrate/.env.example` for the full list. Key settings:

| Variable | Description |
|---|---|
| `IBM_CLOUD_API_KEY` | IBM Cloud IAM API key |
| `WATSONX_PROJECT_ID` | watsonx.ai project ID |
| `WATSONX_MODEL_ID` | Granite model (default: `ibm/granite-13b-chat-v2`) |
| `AGENT1_URL` | Agent 1 ClusterIP URL |
| `AGENT2_URL` | Agent 2 ClusterIP URL |
| `MAX_REACT_ITERATIONS` | Max plan→act cycles per turn (default: 8) |
| `MAX_CONVERSATION_TURNS` | Max turns stored per session (default: 20) |

---

## Scaling Considerations

- The Orchestrate service is stateful (in-process MemoryStore). Use session-sticky
  load balancing or replace `MemoryStore` with a **Redis** backend for horizontal
  scaling beyond 2 replicas.
- HPA is configured: min 2, max 6 pods, 60% CPU target.
- Each ReAct turn makes 1–8 Granite calls + N skill calls. Set `SKILL_READ_TIMEOUT`
  appropriately (default 120s).
