"""
orchestrate/app/react_engine.py
────────────────────────────────
ReAct (Reason + Act) orchestration engine for Petragentic.

Implements the plan → act → observe loop over IBM Granite using the
ibm-watsonx-ai ModelInference API.

ReAct loop (per user turn):
  1. Build prompt from system prompt + conversation history + user message
  2. Call Granite → parse Action / Action Input / Final Answer
  3. If "Action": look up tool, call it, append Observation
  4. Repeat up to max_iterations
  5. Return Final Answer or last assistant message

Granite output format expected:
    Thought: <reasoning step>
    Action: <tool_name>
    Action Input: <JSON dict>
    Observation: <tool result — injected by engine>
    ... (repeat)
    Final Answer: <response to user>
"""

from __future__ import annotations

import json
import re
from typing import AsyncGenerator

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

from orchestrate.app.config import OrchestrateSettings
from orchestrate.app.memory import MemoryStore, Turn
from orchestrate.app.tools import TOOL_REGISTRY, get_tools_description

# ── Regex patterns ────────────────────────────────────────────────────────────
_ACTION_RE = re.compile(r"Action:\s*(.+)", re.IGNORECASE)
_INPUT_RE = re.compile(r"Action Input:\s*(\{.*?\}|\[.*?\])", re.DOTALL | re.IGNORECASE)
_FINAL_RE = re.compile(r"Final Answer:\s*(.*)", re.DOTALL | re.IGNORECASE)

# ── System prompt template ────────────────────────────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = """You are Petragentic, an IBM enterprise AI agent.

{tools_description}

Use the following format EXACTLY for every response when you need to call a tool:

Thought: <reason step by step about what to do>
Action: <one of: {tool_names}>
Action Input: <JSON object — keys must exactly match the tool's parameters>
Observation: <will be provided by the system — do NOT generate this yourself>

When you have enough information to answer the user, output:

Thought: I now have enough information.
Final Answer: <your full, structured answer in markdown>

Rules:
- Never fabricate tool results.
- For security audits, present findings grouped by severity: CRITICAL → HIGH → MEDIUM → LOW.
- For integration designs, highlight the primary recommended tool and rationale clearly.
- If multiple steps are needed, complete them sequentially before giving a Final Answer.
- Always use valid JSON in Action Input.
"""


def _build_system_prompt() -> str:
    tools_desc = get_tools_description()
    tool_names = ", ".join(TOOL_REGISTRY.keys())
    return _SYSTEM_PROMPT_TEMPLATE.format(
        tools_description=tools_desc,
        tool_names=tool_names,
    )


def _make_model(settings: OrchestrateSettings) -> ModelInference:
    """Create an ibm-watsonx-ai ModelInference instance."""
    credentials = Credentials(
        url=settings.watsonx_url,
        api_key=settings.ibm_cloud_api_key,
    )
    client = APIClient(credentials)
    return ModelInference(
        model_id=settings.watsonx_model_id,
        api_client=client,
        project_id=settings.watsonx_project_id,
        params={
            "max_new_tokens": settings.watsonx_max_new_tokens,
            "temperature": settings.watsonx_temperature,
            "repetition_penalty": settings.watsonx_repetition_penalty,
            "stop_sequences": ["Observation:"],   # stop when Granite tries to self-generate a tool result
        },
    )


def _parse_action(text: str) -> tuple[str | None, dict | None]:
    """Extract (action_name, action_input_dict) from a Granite output block."""
    action_match = _ACTION_RE.search(text)
    input_match = _INPUT_RE.search(text)
    if not action_match:
        return None, None
    action_name = action_match.group(1).strip()
    action_input: dict = {}
    if input_match:
        try:
            action_input = json.loads(input_match.group(1))
        except json.JSONDecodeError:
            action_input = {"raw": input_match.group(1)}
    return action_name, action_input


def _parse_final_answer(text: str) -> str | None:
    """Extract the Final Answer content from a Granite output block."""
    match = _FINAL_RE.search(text)
    return match.group(1).strip() if match else None


class ReActEngine:
    """
    Drives a multi-turn ReAct loop for a single conversation session.

    One ReActEngine instance is shared across all sessions (stateless except
    for the injected MemoryStore).
    """

    def __init__(self, settings: OrchestrateSettings, memory: MemoryStore) -> None:
        self._settings = settings
        self._memory = memory
        self._model = _make_model(settings)
        self._system_prompt = _build_system_prompt()

    async def run_turn(
        self,
        session_id: str,
        user_message: str,
    ) -> str:
        """
        Process one user message through the full ReAct loop and return
        the Final Answer string.

        Side effects:
            - Appends the user message, all intermediate thought/action/observation
              steps, and the final answer to the session memory.
        """
        self._memory.add_turn(session_id, "user", user_message)

        for iteration in range(self._settings.max_react_iterations):
            # ── Build prompt ─────────────────────────────────────────────────
            prompt = self._build_prompt(session_id)

            # ── Call Granite ─────────────────────────────────────────────────
            response = self._model.generate_text(prompt=prompt)
            assistant_text: str = response if isinstance(response, str) else response.get("generated_text", "")
            assistant_text = assistant_text.strip()

            # ── Check for Final Answer ────────────────────────────────────────
            final = _parse_final_answer(assistant_text)
            if final:
                self._memory.add_turn(session_id, "assistant", assistant_text)
                return final

            # ── Check for Action ──────────────────────────────────────────────
            action_name, action_input = _parse_action(assistant_text)
            if action_name:
                self._memory.add_turn(session_id, "assistant", assistant_text)
                observation = await self._invoke_tool(action_name, action_input or {})
                obs_text = json.dumps(observation, indent=2, default=str)
                self._memory.add_turn(
                    session_id, "tool", obs_text, tool_name=action_name
                )
                continue

            # ── No recognised pattern — treat as final answer ─────────────────
            self._memory.add_turn(session_id, "assistant", assistant_text)
            return assistant_text

        # Max iterations reached — return last assistant output as-is
        history = self._memory.get_history(session_id)
        last_assistant = next(
            (t.content for t in reversed(history) if t.role == "assistant"), ""
        )
        return last_assistant or "I reached the maximum number of reasoning steps. Please rephrase your request."

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_prompt(self, session_id: str) -> str:
        """
        Assemble the full prompt: system + history + current state.
        Uses a simple text format that Granite-13b-chat follows reliably.
        """
        lines = [f"<|system|>\n{self._system_prompt}\n<|end|>"]
        for turn in self._memory.get_history(session_id):
            if turn.role == "user":
                lines.append(f"<|user|>\n{turn.content}\n<|end|>")
            elif turn.role == "tool":
                lines.append(f"<|assistant|>\nObservation: {turn.content}\n<|end|>")
            else:
                lines.append(f"<|assistant|>\n{turn.content}\n<|end|>")
        lines.append("<|assistant|>")
        return "\n".join(lines)

    async def _invoke_tool(self, tool_name: str, params: dict) -> dict:
        """Look up and call the named tool, returning its result dict."""
        tool_cls = TOOL_REGISTRY.get(tool_name)
        if tool_cls is None:
            return {"error": f"Unknown tool: {tool_name}. Available: {list(TOOL_REGISTRY.keys())}"}
        try:
            result = await tool_cls.call(self._settings, params)
            return result
        except Exception as exc:
            return {"error": f"Tool {tool_name} raised an exception: {exc}"}
