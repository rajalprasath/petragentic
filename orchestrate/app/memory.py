"""
orchestrate/app/memory.py
──────────────────────────
In-process conversation memory store.

Each conversation session is keyed by a session_id string. A session holds
an ordered list of turns (role + content), trimmed to max_turns when it grows
too large.

This is intentionally a simple in-process dict — suitable for a single replica
or a session-sticky load balancer. For horizontal scaling, swap the
_store dict for a Redis or IBM Databases for Redis backend.

Usage:
    from orchestrate.app.memory import MemoryStore

    store = MemoryStore(max_turns=20)
    store.add_turn("session-abc", "user", "Design an integration for SAP to Db2")
    store.add_turn("session-abc", "assistant", "Thought: I need to call...")
    history = store.get_history("session-abc")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass
class Turn:
    role: Literal["user", "assistant", "tool"]
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tool_name: str | None = None        # set when role == "tool"
    tool_call_id: str | None = None


class MemoryStore:
    """
    Thread-safe (GIL-guarded) in-process conversation memory.

    Each session stores up to max_turns turns. When the limit is reached
    the oldest non-system turn is discarded (sliding window).
    """

    def __init__(self, max_turns: int = 20) -> None:
        self._max_turns = max_turns
        self._sessions: dict[str, list[Turn]] = {}

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_turn(
        self,
        session_id: str,
        role: Literal["user", "assistant", "tool"],
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        """Append a turn to the session, trimming when at capacity."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(
            Turn(
                role=role,
                content=content,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
            )
        )
        # Sliding window trim
        while len(self._sessions[session_id]) > self._max_turns:
            self._sessions[session_id].pop(0)

    def clear_session(self, session_id: str) -> None:
        """Remove all turns for a session (e.g. after user says 'start over')."""
        self._sessions.pop(session_id, None)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_history(self, session_id: str) -> list[Turn]:
        """Return the full turn list for a session (empty list if unknown)."""
        return list(self._sessions.get(session_id, []))

    def get_history_as_messages(self, session_id: str) -> list[dict]:
        """
        Return turns in the OpenAI-compatible messages format used by
        ibm-watsonx-ai ModelInference.

        Tool turns are represented as assistant content with an
        [OBSERVATION] prefix so Granite can follow the ReAct pattern.
        """
        messages = []
        for turn in self.get_history(session_id):
            if turn.role == "tool":
                messages.append({
                    "role": "assistant",
                    "content": f"[OBSERVATION from {turn.tool_name}]\n{turn.content}",
                })
            else:
                messages.append({"role": turn.role, "content": turn.content})
        return messages

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def session_turn_count(self, session_id: str) -> int:
        return len(self._sessions.get(session_id, []))

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())
