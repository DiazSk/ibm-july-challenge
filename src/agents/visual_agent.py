"""
Visual & Multimedia Strategy Agent — wraps ImagePromptGenerator.

Responsibilities:
  - generate_image_prompt: Midjourney/DALL-E image direction from a caption
  - generate_storyboard:   Shot-by-shot visual breakdown for a Reel script

The storyboard mode extracts structured shot directions from an existing Reel
script without an additional Granite call — it parses the shot_suggestions
field already produced by ScriptGenerator, enriching them with visual cues.
"""

from src.agents.base import AgentResult, AgentTask, BaseAgent, OLLAMA_MODEL
from src.data.pillars import pillar_label


class VisualAgent(BaseAgent):
    name = "VisualAgent"

    def __init__(self, memory=None, model: str = OLLAMA_MODEL):
        super().__init__(memory, model)
        from src.generation.image_prompt_generator import ImagePromptGenerator
        self._image_gen = ImagePromptGenerator(model=model)

    def run(self, task: AgentTask) -> AgentResult:
        t = task.task_type
        if t == "generate_image_prompt":
            return self._image_prompt(task.payload)
        if t == "generate_storyboard":
            return self._storyboard(task.payload)
        return AgentResult(
            agent_name=self.name,
            success=False,
            error_message=f"Unknown task_type '{t}' for VisualAgent",
        )

    def _image_prompt(self, payload: dict) -> AgentResult:
        # generate()'s 2nd arg is the product NAME, not a cluster id — a raw int
        # renders "Product being shown: 0" in the prompt template. Callers that
        # only know the cluster get its pillar label instead.
        caption = payload.get("caption", "")
        product = str(payload.get("product") or "").strip() or pillar_label(
            int(payload.get("cluster_id", 0) or 0)
        )
        result  = self._image_gen.generate(caption, product)
        return AgentResult(
            agent_name=self.name,
            output={
                "prompt":      result.get("prompt", ""),
                "style_notes": result.get("style_notes", ""),
            },
        )

    def _storyboard(self, payload: dict) -> AgentResult:
        """
        Build a shot-by-shot storyboard from a Reel script dict.
        Parses shot_suggestions and enriches with timing and visual direction.
        No additional Granite call needed — ScriptGenerator already produces shots.
        """
        script       = payload.get("script", {})
        caption      = payload.get("caption", "")
        hook         = script.get("hook", "")
        shots_raw    = script.get("shot_suggestions", [])
        voiceover    = script.get("voiceover_script", "")

        if not shots_raw and voiceover:
            # Fallback: split voiceover into pseudo-shots
            sentences = [s.strip() for s in voiceover.replace(".", ".|").split("|") if s.strip()]
            shots_raw = sentences[:10]

        shots = []
        for i, shot_desc in enumerate(shots_raw[:10], start=1):
            shots.append({
                "shot_number":   i,
                "duration_secs": 3 if i == 1 else 2,
                "visual":        shot_desc,
                "text_overlay":  hook if i == 1 else "",
                "transition":    "cut" if i < len(shots_raw) else "fade",
            })

        return AgentResult(
            agent_name=self.name,
            output={
                "storyboard":   shots,
                "total_shots":  len(shots),
                "est_duration": sum(s["duration_secs"] for s in shots),
                "caption":      caption,
            },
        )


# ── Standalone self-check ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    agent = VisualAgent()

    # 1. Regression guard (offline, no Granite). Whatever lands in generate()'s
    #    `product` slot must be a human-readable name — never a bare cluster id.
    seen: list[str] = []
    real_gen = agent._image_gen

    class _SpyGen:
        def generate(self, caption, product):
            seen.append(product)
            return {"prompt": "x", "style_notes": "", "video_prompt": "", "motion_notes": ""}

    agent._image_gen = _SpyGen()
    for payload in (
        {"caption": "c", "cluster_id": 1},                              # no product key
        {"caption": "c", "product": "", "cluster_id": 1},               # blank product
        {"caption": "c", "product": "Nutella Bomboloni", "cluster_id": 1},
    ):
        agent.run(AgentTask("generate_image_prompt", payload))
    agent._image_gen = real_gen

    for product in seen:
        assert isinstance(product, str), f"product must be str, got {type(product)}"
        assert not product.strip().lstrip("-").isdigit(), (
            f"product reaching ImagePromptGenerator is a bare number ({product!r}) — "
            "a caller is passing cluster_id where the product name belongs"
        )
    assert seen[-1] == "Nutella Bomboloni", seen
    print(f"OK — products passed to generator: {seen}")

    # 2. End-to-end (needs Ollama + granite3.1-dense:8b).
    result = agent.run(AgentTask("generate_image_prompt", {
        "caption": "Fresh Bomboloni, still warm from the fryer — comfort in every bite ☕🍩",
        "product": "Nutella Bomboloni",
        "cluster_id": 1,
    }))
    assert result.success, result.error_message
    assert result.output["prompt"], "Granite returned an empty prompt"
    print("\nPrompt:", result.output["prompt"][:220])
    print("\nStyle notes:", result.output["style_notes"])
