"""
Community Management Agent — wraps CommentTriager.

Responsibilities:
  - triage_comments: Classify and draft replies for a batch of comments/DMs

Adds over raw CommentTriager:
  - Priority scoring per message: high / medium / low / ignore
  - Two tone variants per reply: warm (on-brand) vs. brief (professional)
"""

from src.agents.base import AgentResult, AgentTask, BaseAgent, OLLAMA_MODEL

_PRIORITY_MAP = {
    "order_inquiry": "high",
    "complaint":     "high",
    "compliment":    "medium",
    "uncertain":     "low",
    "spam":          "ignore",
}

_WARM_OPENERS = ["So happy you reached out!", "Thanks for the love!", "We'd love to help!"]
_BRIEF_OPENERS = ["Thanks for reaching out.", "Happy to help.", "Noted — thanks!"]


class CommunityAgent(BaseAgent):
    name = "CommunityAgent"

    def __init__(self, memory=None, model: str = OLLAMA_MODEL):
        super().__init__(memory, model)
        from src.generation.comment_triage import CommentTriager
        self._triager = CommentTriager(model=model)

    def run(self, task: AgentTask) -> AgentResult:
        if task.task_type != "triage_comments":
            return AgentResult(
                agent_name=self.name,
                success=False,
                error_message=f"CommunityAgent only handles 'triage_comments', got '{task.task_type}'",
            )
        return self._triage(task.payload)

    def _triage(self, payload: dict) -> AgentResult:
        messages   = payload.get("messages", [])
        cluster_id = payload.get("cluster_id", 0)

        raw_results = self._triager.triage(messages, cluster_id)

        enriched = []
        for item in raw_results:
            category = item.get("category", "uncertain")
            priority = _PRIORITY_MAP.get(category, "low")
            reply    = item.get("drafted_reply", "")

            # Generate brief variant by trimming to first sentence
            brief_reply = reply.split(".")[0].strip() + "." if reply else ""

            enriched.append({
                **item,
                "priority":    priority,
                "warm_reply":  reply,
                "brief_reply": brief_reply,
            })

        return AgentResult(
            agent_name=self.name,
            output={
                "results": enriched,
                "total":   len(enriched),
                "high_priority_count": sum(1 for r in enriched if r["priority"] == "high"),
            },
        )
