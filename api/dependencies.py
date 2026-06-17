"""
Singleton generator instances for FastAPI dependency injection.

Each factory is decorated with @lru_cache so the underlying model
(and its loaded brand_profile.json) is initialised exactly once —
equivalent to @st.cache_resource in the Streamlit version.

FastAPI sync endpoints call these as regular callables; the lru_cache
guarantees thread-safe single initialisation on first request.
"""

import sys
from functools import lru_cache
from pathlib import Path

# Ensure project root is importable when running via `uvicorn api.main:app`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@lru_cache(maxsize=1)
def get_caption_generator():
    from src.generation.caption_generator import CaptionGenerator
    return CaptionGenerator()


@lru_cache(maxsize=1)
def get_image_generator():
    from src.generation.image_prompt_generator import ImagePromptGenerator
    return ImagePromptGenerator()


@lru_cache(maxsize=1)
def get_why_engine():
    from src.generation.why_engine import WhyEngine
    return WhyEngine()


@lru_cache(maxsize=1)
def get_moment_analyzer():
    from src.generation.blank_page_solver import MomentAnalyzer
    return MomentAnalyzer()


@lru_cache(maxsize=1)
def get_direction_generator():
    from src.generation.blank_page_solver import DirectionGenerator
    return DirectionGenerator()


@lru_cache(maxsize=1)
def get_voice_timeline():
    from src.generation.voice_timeline import VoiceTimeline
    return VoiceTimeline()


@lru_cache(maxsize=1)
def get_strategic_insights():
    from src.generation.strategic_insights import StrategicInsights
    return StrategicInsights()


@lru_cache(maxsize=1)
def get_script_generator():
    from src.generation.script_generator import ScriptGenerator
    return ScriptGenerator()


@lru_cache(maxsize=1)
def get_recovery_brief_generator():
    from src.generation.recovery_brief import RecoveryBriefGenerator
    return RecoveryBriefGenerator()


@lru_cache(maxsize=1)
def get_boost_advisor():
    from src.generation.boost_advisor import BoostAdvisor
    return BoostAdvisor()
