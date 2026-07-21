"""
agent1/app/services/prompt_builder.py
───────────────────────────────────────
Constructs the structured prompt sent to Granite-13b-chat for design
document generation.

The prompt is structured in four sections:
  [SYSTEM]      — Role and output format instructions
  [CONTEXT]     — Approved tools + ranked catalogue data
  [REQUIREMENT] — The NL integration requirement
  [OUTPUT]      — JSON schema that Granite must populate

Keeping the schema explicit in the prompt maximises parse reliability
without requiring JSON-mode fine-tuning.
"""

from agent1.app.models.response import ToolRecommendation
from agent1.app.models.request import DesignRequest

_SYSTEM_BLOCK = """You are an IBM Integration Architect AI assistant.
Your job is to analyse an integration requirement and produce a complete,
production-ready integration design document.

You MUST respond with a single valid JSON object that conforms exactly to
the OUTPUT SCHEMA below. Do not include any text outside the JSON object.
Do not include markdown fences. If you are uncertain, provide your best
engineering judgment — never leave a required field empty.
""".strip()

_OUTPUT_SCHEMA = """
{
  "primary_tool": "<one of the APPROVED_TOOLS listed in CONTEXT>",
  "protocol": "<REST|SOAP|file-based|AMQP|Kafka|SFTP|JMS>",
  "data_format": "<JSON|XML|CSV|Avro|Parquet>",
  "auth_method": "<OAuth 2.0|mTLS / certificate|API key|service principal / managed identity|basic auth>",
  "executive_summary": "<2-3 sentence summary of the integration design>",
  "integration_overview": "<paragraph describing the end-to-end integration>",
  "data_flow_description": "<step-by-step data flow from source to target>",
  "implementation_steps": ["<step 1>", "<step 2>", "..."],
  "security_considerations": [
    {
      "area": "<e.g. Transport Security>",
      "risk": "<identified risk>",
      "mitigation": "<recommended mitigation>",
      "reference": "<e.g. NIST 800-53 SC-8>"
    }
  ],
  "architectural_decisions": [
    {
      "decision_id": "ADR-001",
      "title": "<decision title>",
      "context": "<why this decision was needed>",
      "decision": "<what was decided>",
      "consequences": "<trade-offs and implications>",
      "status": "Accepted"
    }
  ],
  "testing_strategy": "<how to validate the integration end-to-end>",
  "open_issues": ["<any open questions or risks>"],
  "tool_alternatives": [
    {
      "rank": 2,
      "tool": "<second best tool>",
      "rationale": "<why it was not chosen>",
      "governance_status": "<Approved|Pending|Rejected|Unknown>",
      "usage_count": 0
    }
  ],
  "auth_alternatives": [
    {
      "method": "<alternative auth method>",
      "rationale": "<why it was not chosen>",
      "config_notes": ""
    }
  ]
}
""".strip()


def build_design_prompt(
    request: DesignRequest,
    ranked_tools: list[ToolRecommendation],
) -> str:
    """
    Build the full Granite prompt for integration design document generation.

    Returns the prompt string ready to pass to watsonx_client.generate_text().
    """
    tool_lines = "\n".join(
        f"  {rec.rank}. {rec.tool.value} "
        f"(governance: {rec.governance_status.value}, "
        f"usage_count: {rec.usage_count})"
        for rec in ranked_tools
    )

    prompt = f"""[SYSTEM]
{_SYSTEM_BLOCK}

[CONTEXT]
APPROVED_TOOLS (ranked by enterprise catalogue usage):
{tool_lines}

AUTHENTICATION_PATTERNS:
  - OAuth 2.0        — preferred for REST APIs; use IBM App ID or Azure AD
  - mTLS / certificate — preferred for high-security B2B and file-based integrations
  - API key          — acceptable for internal APIs with low data sensitivity
  - service principal / managed identity — preferred for cloud-to-cloud integrations
  - basic auth       — discouraged; use only when no alternative is available

DATA_FORMATS:
  JSON (default for REST), XML (SOAP/legacy), CSV (file-based batch),
  Avro (Kafka streaming), Parquet (analytics pipelines)

[REQUIREMENT]
{request.requirement.strip()}

Pattern hint: {request.pattern_hint.value}

[OUTPUT]
Respond with ONLY a JSON object matching this schema:
{_OUTPUT_SCHEMA}

<output>"""

    return prompt
