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
        caption    = payload.get("caption", "")
        cluster_id = payload.get("cluster_id", 0)
        result     = self._image_gen.generate(caption, cluster_id)
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
