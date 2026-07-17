"""
AgentMemoryStore — ChromaDB-backed three-tier memory for StyleSync agents.

WHAT CHANGED AND WHY:
upsert_episode previously stored only "Caption: X. Outcome: Y. Cluster: Z."
That meant the CopywritingAgent's performance_context block said "this caption
succeeded" with no signal data — it couldn't learn WHY it won. The new schema
stores hook_pattern, primary_signal, watch_time_secs, save_rate, and share_count
alongside every episode. The search_episodic method returns these fields so the
caption generator can say "this hook pattern drove 8s avg watch time in C1."

Three collections match the research-validated MIRIX Taxonomy subset:
  semantic   — brand-invariant voice rules, tone, vocabulary (from brand_profile.json)
  episodic   — campaign-specific outcomes WITH signal metrics (from workbench.db)
  procedural — platform formatting rules (hard-coded seed, platform-invariant)

Key architectural constraint:
  Never conflate semantic and episodic into a single overwriting summary —
  that causes catastrophic forgetting of brand-invariant tone rules when
  campaign-specific data overwrites them.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
except ImportError as exc:
    raise ImportError(
        "chromadb is required for AgentMemoryStore. "
        "Install it with `pip install chromadb`."
    ) from exc

# ---------------------------------------------------------------------------
# Platform rules — kept for callers that still use get_platform_rules()
# (copywriting_agent.py lines 77, 137)
# ---------------------------------------------------------------------------

_PLATFORM_RULES: dict[str, dict] = {
    "instagram": {
        "max_chars": "2200",
        "hook_position": "first line",
        "hashtag_count": "5-10",
        "cta_style": "save, share, comment",
        "formatting": "short paragraphs, line breaks, emojis welcome",
        "tone_register": "warm, personal, community-first",
    },
    "tiktok": {
        "max_chars": "2200",
        "hook_position": "first 3 seconds / first line",
        "hashtag_count": "3-5 trending",
        "cta_style": "follow, duet, stitch",
        "formatting": "punchy, conversational, hooks at start",
        "tone_register": "energetic, authentic, trending-aware",
    },
    "linkedin": {
        "max_chars": "3000",
        "hook_position": "opening sentence before 'see more'",
        "hashtag_count": "3-5",
        "cta_style": "comment, connect, share insight",
        "formatting": "line breaks, no emojis in first 2 lines, thought-leadership",
        "tone_register": "professional yet authentic, story-driven",
    },
    "facebook": {
        "max_chars": "63206",
        "hook_position": "first 2 sentences",
        "hashtag_count": "1-3",
        "cta_style": "like, share, tag a friend",
        "formatting": "conversational, story-first",
        "tone_register": "friendly, community-focused",
    },
}


@dataclass
class MemoryHit:
    id: str
    text: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None


class AgentMemoryStore:
    """
    ChromaDB-backed three-tier memory.

    Collections:
      - semantic
      - episodic
      - procedural
    """

    def __init__(
        self,
        persist_dir: str | os.PathLike = "data/chroma",
        collection_prefix: str = "stylesync",
        seed_procedural: bool = True,
    ) -> None:
        self.persist_dir = str(Path(persist_dir))
        self.collection_prefix = collection_prefix

        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        self.semantic = self.client.get_or_create_collection(
            name=f"{collection_prefix}_semantic",
            metadata={"description": "Brand-invariant voice memory"},
        )
        self.episodic = self.client.get_or_create_collection(
            name=f"{collection_prefix}_episodic",
            metadata={"description": "Campaign/post outcomes with signal metrics"},
        )
        self.procedural = self.client.get_or_create_collection(
            name=f"{collection_prefix}_procedural",
            metadata={"description": "Platform formatting and procedural rules"},
        )

        if seed_procedural:
            self._seed_procedural_rules()

    # ----------------------------
    # Public semantic API
    # ----------------------------
    def upsert_brand_profile(
        self,
        profile: Dict[str, Any],
        brand_id: str = "default_brand",
    ) -> str:
        """
        Stores stable brand voice / tone / vocabulary guidance.
        Safe to call repeatedly; overwrites by deterministic id.
        """
        doc = self._brand_profile_to_text(profile)
        metadata = {
            "memory_type": "semantic",
            "brand_id": brand_id,
            "source": "brand_profile",
            "tone": self._stringify(profile.get("tone")),
            "audience": self._stringify(profile.get("audience")),
            "updated_from": self._stringify(
                profile.get("updated_from", "brand_profile.json")
            ),
        }
        item_id = f"semantic::{brand_id}"
        self.semantic.upsert(
            ids=[item_id],
            documents=[doc],
            metadatas=[metadata],
        )
        return item_id

    def search_semantic(
        self,
        query: str,
        n_results: int = 5,
        brand_id: Optional[str] = None,
    ) -> List[MemoryHit]:
        where = {"brand_id": brand_id} if brand_id else None
        return self._query_collection(
            self.semantic, query, n_results=n_results, where=where
        )

    # ----------------------------
    # Public episodic API
    # ----------------------------
    def upsert_episode(
        self,
        caption: str,
        cluster_id: int | str,
        outcome: str,
        *,
        brand_id: str = "default_brand",
        post_id: Optional[str] = None,
        post_type: Optional[str] = None,
        hook_pattern: Optional[str] = None,
        primary_signal: Optional[str] = None,
        watch_time_secs: Optional[float] = None,
        avg_watch_time_secs: Optional[float] = None,
        save_rate: Optional[float] = None,
        share_count: Optional[int] = None,
        shares: Optional[int] = None,
        saves: Optional[int] = None,
        views: Optional[int] = None,
        reach: Optional[int] = None,
        likes: Optional[int] = None,
        comments: Optional[int] = None,
        verdict_label: Optional[str] = None,
        why_summary: Optional[str] = None,
        created_at: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Stores campaign/post outcome memory WITH signal data.

        This replaces the old underpowered episode text:
          "Caption: X. Outcome: Y. Cluster: Z."

        so downstream agents can reason about why the content won or lost.
        """
        resolved_watch = (
            watch_time_secs if watch_time_secs is not None else avg_watch_time_secs
        )
        resolved_shares = share_count if share_count is not None else shares

        metadata: Dict[str, Any] = {
            "memory_type": "episodic",
            "brand_id": brand_id,
            "cluster_id": str(cluster_id),
            "outcome": outcome,
            "post_id": post_id or "",
            "post_type": post_type or "",
            "hook_pattern": hook_pattern or "",
            "primary_signal": primary_signal or "",
            "watch_time_secs": self._safe_float(resolved_watch),
            "save_rate": self._safe_float(save_rate),
            "share_count": self._safe_int(resolved_shares),
            "saves": self._safe_int(saves),
            "views": self._safe_int(views),
            "reach": self._safe_int(reach),
            "likes": self._safe_int(likes),
            "comments": self._safe_int(comments),
            "verdict_label": verdict_label or "",
            "created_at": created_at or "",
            "source": "analytics_feedback_loop",
        }

        if extra_metadata:
            for k, v in extra_metadata.items():
                metadata[k] = self._coerce_metadata_value(v)

        doc = self._episode_to_text(
            caption=caption,
            cluster_id=cluster_id,
            outcome=outcome,
            hook_pattern=hook_pattern,
            primary_signal=primary_signal,
            watch_time_secs=resolved_watch,
            save_rate=save_rate,
            share_count=resolved_shares,
            post_type=post_type,
            why_summary=why_summary,
        )

        item_id = post_id or self._stable_episode_id(
            brand_id=brand_id,
            caption=caption,
            cluster_id=cluster_id,
            outcome=outcome,
            created_at=created_at,
        )

        self.episodic.upsert(
            ids=[f"episodic::{item_id}"],
            documents=[doc],
            metadatas=[metadata],
        )
        return f"episodic::{item_id}"

    def search_episodic(
        self,
        query: str,
        n_results: int = 5,
        *,
        brand_id: Optional[str] = None,
        cluster_id: Optional[int | str] = None,
        outcome: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns a richer structure than generic vector hits so generator agents
        can directly consume performance_context fields.
        """
        where = self._build_where(
            brand_id=brand_id,
            cluster_id=str(cluster_id) if cluster_id is not None else None,
            outcome=outcome,
        )
        hits = self._query_collection(
            self.episodic, query, n_results=n_results, where=where
        )
        enriched: List[Dict[str, Any]] = []
        for hit in hits:
            enriched.append(
                {
                    "id": hit.id,
                    "text": hit.text,
                    "caption": self._extract_caption_from_doc(hit.text),
                    "cluster_id": hit.metadata.get("cluster_id"),
                    "outcome": hit.metadata.get("outcome"),
                    "hook_pattern": hit.metadata.get("hook_pattern"),
                    "primary_signal": hit.metadata.get("primary_signal"),
                    "watch_time_secs": hit.metadata.get("watch_time_secs"),
                    "save_rate": hit.metadata.get("save_rate"),
                    "share_count": hit.metadata.get("share_count"),
                    "post_type": hit.metadata.get("post_type"),
                    "verdict_label": hit.metadata.get("verdict_label"),
                    "distance": hit.distance,
                    "metadata": hit.metadata,
                }
            )
        return enriched

    # ----------------------------
    # Public procedural API
    # ----------------------------
    def upsert_procedural_rule(
        self,
        rule_name: str,
        instruction: str,
        *,
        platform: str = "instagram",
        source: str = "seed",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        metadata: Dict[str, Any] = {
            "memory_type": "procedural",
            "platform": platform,
            "rule_name": rule_name,
            "source": source,
        }
        if extra_metadata:
            for k, v in extra_metadata.items():
                metadata[k] = self._coerce_metadata_value(v)

        item_id = f"procedural::{platform}::{self._slug(rule_name)}"
        self.procedural.upsert(
            ids=[item_id],
            documents=[instruction],
            metadatas=[metadata],
        )
        return item_id

    def search_procedural(
        self,
        query: str,
        n_results: int = 5,
        *,
        platform: Optional[str] = "instagram",
    ) -> List[MemoryHit]:
        where = {"platform": platform} if platform else None
        return self._query_collection(
            self.procedural, query, n_results=n_results, where=where
        )

    # ----------------------------
    # Convenience methods for agents
    # ----------------------------
    def build_copywriting_context(
        self,
        query: str,
        *,
        brand_id: str = "default_brand",
        cluster_id: Optional[int | str] = None,
        semantic_k: int = 3,
        episodic_k: int = 5,
        procedural_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Unified read helper for CopywritingAgent.
        Important: this READS from all three stores but does not merge them into
        one summary string, preserving the semantic/episodic boundary.
        """
        semantic_hits = self.search_semantic(
            query, n_results=semantic_k, brand_id=brand_id
        )
        episodic_hits = self.search_episodic(
            query,
            n_results=episodic_k,
            brand_id=brand_id,
            cluster_id=cluster_id,
        )
        procedural_hits = self.search_procedural(
            query, n_results=procedural_k, platform="instagram"
        )

        return {
            "semantic_rules": [
                {
                    "text": h.text,
                    "tone": h.metadata.get("tone"),
                    "audience": h.metadata.get("audience"),
                    "distance": h.distance,
                }
                for h in semantic_hits
            ],
            "performance_context": episodic_hits,
            "procedural_rules": [
                {
                    "rule_name": h.metadata.get("rule_name"),
                    "text": h.text,
                    "distance": h.distance,
                }
                for h in procedural_hits
            ],
        }

    def get_platform_rules(self, platform: str = "instagram") -> dict:
        """Return platform formatting rules dict. Used by CopywritingAgent."""
        return _PLATFORM_RULES.get(platform, _PLATFORM_RULES["instagram"])

    def status(self) -> dict:
        """Return collection sizes. Used by api/routers/orchestrate.py."""
        return {
            "semantic": self.semantic.count(),
            "episodic": self.episodic.count(),
            "procedural": self.procedural.count(),
        }

    # ----------------------------
    # Internal helpers
    # ----------------------------
    def _query_collection(
        self,
        collection: Any,
        query: str,
        *,
        n_results: int,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryHit]:
        result = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )

        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = (
            result.get("distances", [[]])[0]
            if result.get("distances")
            else [None] * len(ids)
        )

        hits: List[MemoryHit] = []
        for i, doc_id in enumerate(ids):
            hits.append(
                MemoryHit(
                    id=doc_id,
                    text=docs[i],
                    metadata=metas[i] or {},
                    distance=distances[i],
                )
            )
        return hits

    def _build_where(
        self,
        *,
        brand_id: Optional[str] = None,
        cluster_id: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        clauses: List[Dict[str, Any]] = []
        if brand_id:
            clauses.append({"brand_id": brand_id})
        if cluster_id:
            clauses.append({"cluster_id": cluster_id})
        if outcome:
            clauses.append({"outcome": outcome})

        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    def _brand_profile_to_text(self, profile: Dict[str, Any]) -> str:
        parts = [
            f"Brand voice: {self._stringify(profile.get('brand_voice'))}",
            f"Tone: {self._stringify(profile.get('tone'))}",
            f"Audience: {self._stringify(profile.get('audience'))}",
            f"Values: {self._stringify(profile.get('values'))}",
            f"Vocabulary to use: {self._stringify(profile.get('preferred_vocabulary'))}",
            f"Vocabulary to avoid: {self._stringify(profile.get('avoid_vocabulary'))}",
            f"Style rules: {self._stringify(profile.get('style_rules'))}",
            f"CTA style: {self._stringify(profile.get('cta_style'))}",
            f"Emoji policy: {self._stringify(profile.get('emoji_policy'))}",
        ]
        return "\n".join(parts)

    def _episode_to_text(
        self,
        *,
        caption: str,
        cluster_id: int | str,
        outcome: str,
        hook_pattern: Optional[str],
        primary_signal: Optional[str],
        watch_time_secs: Optional[float],
        save_rate: Optional[float],
        share_count: Optional[int],
        post_type: Optional[str],
        why_summary: Optional[str],
    ) -> str:
        parts = [
            f"Caption: {caption}",
            f"Cluster: {cluster_id}",
            f"Outcome: {outcome}",
            f"Post type: {post_type or 'unknown'}",
            f"Hook pattern: {hook_pattern or 'unknown'}",
            f"Primary signal: {primary_signal or 'unknown'}",
            f"Average watch time seconds: {watch_time_secs if watch_time_secs is not None else 'unknown'}",
            f"Save rate: {save_rate if save_rate is not None else 'unknown'}",
            f"Share count: {share_count if share_count is not None else 'unknown'}",
        ]
        if why_summary:
            parts.append(f"Why summary: {why_summary}")
        return ". ".join(parts)

    def _stable_episode_id(
        self,
        *,
        brand_id: str,
        caption: str,
        cluster_id: int | str,
        outcome: str,
        created_at: Optional[str],
    ) -> str:
        raw = f"{brand_id}|{caption}|{cluster_id}|{outcome}|{created_at or ''}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return digest

    def _extract_caption_from_doc(self, text: str) -> str:
        prefix = "Caption: "
        if text.startswith(prefix):
            end = text.find(". Cluster:")
            if end != -1:
                return text[len(prefix) : end]
        return text

    def _seed_procedural_rules(self) -> None:
        existing = self.procedural.count()
        if existing > 0:
            return

        seeds = [
            {
                "rule_name": "instagram_hook_first_line",
                "instruction": (
                    "Front-load the first line with a concrete payoff, tension, or curiosity gap. "
                    "Avoid generic intros because the opening line must earn continued reading."
                ),
            },
            {
                "rule_name": "instagram_caption_scannability",
                "instruction": (
                    "Use short paragraphs, clean line breaks, and visually scannable structure. "
                    "Put the strongest message before any long explanation."
                ),
            },
            {
                "rule_name": "instagram_single_cta",
                "instruction": (
                    "Prefer one primary CTA per caption. Asking for too many actions weakens response."
                ),
            },
            {
                "rule_name": "instagram_save_share_bias",
                "instruction": (
                    "Educational, checklist, mistake-avoidance, and reference-style captions should be framed "
                    "to maximize saves and shares, not only likes."
                ),
            },
            {
                "rule_name": "instagram_voice_consistency",
                "instruction": (
                    "Respect brand voice and audience sophistication. Formatting tactics should never overwrite "
                    "stable tone, vocabulary, or brand personality."
                ),
            },
        ]

        for seed in seeds:
            self.upsert_procedural_rule(
                rule_name=seed["rule_name"],
                instruction=seed["instruction"],
                platform="instagram",
                source="hard_coded_seed",
            )

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple, set)):
            return ", ".join(str(v) for v in value)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def _coerce_metadata_value(value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, (str, int, float, bool)):
            return value
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _slug(value: str) -> str:
        return (
            value.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
        )
