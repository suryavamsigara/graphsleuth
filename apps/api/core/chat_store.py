from dataclasses import dataclass
from supabase import Client


@dataclass
class ChatMessageRow:
    id: str
    role: str
    content: str
    steps: list
    confidence: float | None
    latency_ms: float | None
    trace_id: str | None
    created_at: str


class ChatStore:
    """One user's chat within one project."""
    def __init__(self, client: Client):
        self.client = client

    def list_messages(self, project_id: str, user_id: str, limit: int = 200) -> list[ChatMessageRow]:
        resp = (
            self.client.table("chat_messages")
            .select("*")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .order("created_at")
            .limit(limit)
            .execute()
        )
        return [self._row_to_message(r) for r in resp.data]

    def save_turn(
        self,
        project_id: str,
        user_id: str,
        question: str,
        answer: str,
        steps: list,
        confidence: float,
        latency_ms: float,
        trace_id: str | None,
    ) -> None:
        """Persists one full chat turn as two rows (user question,
        assistant answer) — matches the shape the frontend already renders,
        so loading history back is just `setMessages(rows)` with no
        reshaping needed."""
        self.client.table("chat_messages").insert([
            {
                "project_id": project_id,
                "user_id": user_id,
                "role": "user",
                "content": question,
                "steps": [],
                "confidence": None,
                "latency_ms": None,
                "trace_id": None,
            },
            {
                "project_id": project_id,
                "user_id": user_id,
                "role": "assistant",
                "content": answer,
                "steps": steps,
                "confidence": confidence,
                "latency_ms": latency_ms,
                "trace_id": trace_id,
            },
        ]).execute()

    def clear(self, project_id: str, user_id: str) -> None:
        self.client.table("chat_messages").delete().eq("project_id", project_id).eq("user_id", user_id).execute()

    @staticmethod
    def _row_to_message(row: dict) -> ChatMessageRow:
        return ChatMessageRow(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            steps=row.get("steps") or [],
            confidence=row.get("confidence"),
            latency_ms=row.get("latency_ms"),
            trace_id=row.get("trace_id"),
            created_at=row["created_at"],
        )
