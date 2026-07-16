"""
AgentMemoryStore — ChromaDB-backed three-tier memory for StyleSync agents.

Three collections match the research-validated MIRIX taxonomy subset:
  semantic   — brand-invariant voice rules, tone, vocabulary (from brand_profile.json)
  episodic   — campaign-specific outcomes (from workbench.db actual_outcome column)
  procedural — platform formatting rules (hard-coded seed, platform-invariant)

Key architectural constraint (confirmed 3-0 by adversarial verification):
  Never conflate semantic and episodic into a single overwriting summary —
  that causes catastrophic forgetting of brand-invariant tone rules when
  campaign-specific data overwrites them.
"""

import json
import sqlite3
import uuid
from pathlib import Path

import chromadb
from chromadb.config import Settings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

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

_CLUSTER_NAMES: dict[int, str] = {
    0: "Homemade Classics",
    1: "Fusion Specials",
    2: "Behind the Scenes",
    3: "Nutella Series",
    4: "Bomboloni",
}


class AgentMemoryStore:
    """
    Persistent ChromaDB memory store for all StyleSync agents.

    Instantiate once via get_memory_store() in api/dependencies.py.
    Call reseed() after onboarding resets so brand voice stays current.
    """

    def __init__(
        self,
        brand_profile_path: Path = _PROJECT_ROOT / "data" / "brand_profile.json",
        workbench_db_path: Path  = _PROJECT_ROOT / "data" / "workbench.db",
        chroma_path: Path        = _PROJECT_ROOT / "data" / "chroma",
    ):
        self._brand_profile_path = brand_profile_path
        self._workbench_db_path  = workbench_db_path

        self._client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self._semantic   = self._client.get_or_create_collection("semantic")
        self._episodic   = self._client.get_or_create_collection("episodic")
        self._procedural = self._client.get_or_create_collection("procedural")

        self._seed_semantic(brand_profile_path)
        self._seed_episodic(workbench_db_path)
        self._seed_procedural()

    # ── Seeding ───────────────────────────────────────────────────────────────

    def _seed_semantic(self, path: Path) -> None:
        if not path.exists():
            return
        # Skip if already seeded — sentinel ID "brand_meta" present
        if self._semantic.get(ids=["brand_meta"])["ids"]:
            return

        profile = json.loads(path.read_text(encoding="utf-8"))
        brand_name = profile.get("brand_name", "")
        docs, metas, ids = [], [], []

        docs.append(
            f"Brand: {brand_name}. "
            f"Handle: {profile.get('ig_handle', '')}. "
            f"Bio: {profile.get('brand_bio', '')}."
        )
        metas.append({"type": "brand_meta", "brand_name": brand_name})
        ids.append("brand_meta")

        for cp in profile.get("cluster_profiles", []):
            cid = cp["cluster_id"]
            p   = cp["profile"]
            voc = p.get("vocabulary_patterns", {})
            doc = (
                f"Content pillar: {p.get('content_pillar', '')}. "
                f"Tone: {', '.join(p.get('tone_descriptors', []))}. "
                f"Recurring words: {', '.join(voc.get('recurring_words', []))}. "
                f"Signature phrases: {', '.join(voc.get('signature_phrases', []))}. "
                f"Avoided terms: {', '.join(p.get('avoided_terms', []))}. "
                f"Structural pattern: {p.get('structural_signature', '')}."
            )
            docs.append(doc)
            metas.append({
                "type":             "cluster_voice",
                "cluster_id":       cid,
                "content_pillar":   p.get("content_pillar", ""),
                "tone":             ", ".join(p.get("tone_descriptors", [])),
                "signature_phrases": ", ".join(voc.get("signature_phrases", [])),
                "avoided_terms":    ", ".join(p.get("avoided_terms", [])),
            })
            ids.append(f"cluster_{cid}")

        if docs:
            self._semantic.add(documents=docs, metadatas=metas, ids=ids)

    def _seed_episodic(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            conn = sqlite3.connect(str(path))
            rows = conn.execute(
                """
                SELECT id, content, cluster_id, cluster_label, actual_outcome, created_at
                FROM workbench_assets
                WHERE actual_outcome IS NOT NULL
                  AND asset_type IN ('caption','reel_script','carousel','static_script')
                ORDER BY created_at DESC
                LIMIT 200
                """
            ).fetchall()
            conn.close()
        except sqlite3.OperationalError:
            return

        docs, metas, ids_to_add = [], [], []
        existing = set(self._episodic.get()["ids"])

        for row_id, content_json, cluster_id, cluster_label, outcome, created_at in rows:
            if row_id in existing:
                continue
            try:
                content = json.loads(content_json)
                caption_text = (
                    content.get("caption")
                    or content.get("refined_caption")
                    or content.get("text")
                    or str(content)[:300]
                )
            except (json.JSONDecodeError, TypeError):
                caption_text = str(content_json)[:300]

            cname = _CLUSTER_NAMES.get(cluster_id or 0, cluster_label or "")
            docs.append(
                f"Caption: {caption_text}. "
                f"Outcome: {outcome}. "
                f"Cluster: {cname}."
            )
            metas.append({
                "type":          "campaign_outcome",
                "outcome":       outcome or "unknown",
                "cluster_id":    cluster_id or 0,
                "cluster_label": cname,
                "created_at":    created_at or "",
            })
            ids_to_add.append(row_id)

        if docs:
            self._episodic.add(documents=docs, metadatas=metas, ids=ids_to_add)

    def _seed_procedural(self) -> None:
        for platform, rules in _PLATFORM_RULES.items():
            rule_id = f"platform_{platform}"
            if self._procedural.get(ids=[rule_id])["ids"]:
                continue
            doc = (
                f"Platform: {platform}. "
                f"Max chars: {rules['max_chars']}. "
                f"Hook position: {rules['hook_position']}. "
                f"Hashtags: {rules['hashtag_count']}. "
                f"CTA style: {rules['cta_style']}. "
                f"Formatting: {rules['formatting']}. "
                f"Tone register: {rules['tone_register']}."
            )
            self._procedural.add(
                documents=[doc],
                metadatas=[{"type": "platform_rules", "platform": platform, **rules}],
                ids=[rule_id],
            )

    # ── Query API ─────────────────────────────────────────────────────────────

    def search_semantic(self, query: str, n: int = 5) -> list[dict]:
        """Search brand voice rules by semantic similarity."""
        count = self._semantic.count()
        if count == 0:
            return []
        results = self._semantic.query(
            query_texts=[query], n_results=min(n, count)
        )
        return [
            {"text": doc, "metadata": meta}
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ]

    def search_episodic(
        self, query: str, cluster_id: int | None = None, n: int = 5
    ) -> list[dict]:
        """Search past campaign outcomes, optionally filtered by cluster."""
        count = self._episodic.count()
        if count == 0:
            return []
        where = {"cluster_id": cluster_id} if cluster_id is not None else None
        try:
            results = self._episodic.query(
                query_texts=[query],
                n_results=min(n, count),
                where=where,
            )
            return [
                {"text": doc, "metadata": meta}
                for doc, meta in zip(results["documents"][0], results["metadatas"][0])
            ]
        except Exception:
            return []

    def upsert_episode(
        self,
        caption: str,
        cluster_id: int,
        outcome: str,
        episode_id: str | None = None,
    ) -> str:
        """Add or update a campaign outcome in episodic memory."""
        eid    = episode_id or str(uuid.uuid4())
        cname  = _CLUSTER_NAMES.get(cluster_id, f"Cluster {cluster_id}")
        doc    = f"Caption: {caption}. Outcome: {outcome}. Cluster: {cname}."
        meta   = {
            "type":          "campaign_outcome",
            "outcome":       outcome,
            "cluster_id":    cluster_id,
            "cluster_label": cname,
            "created_at":    "",
        }
        if self._episodic.get(ids=[eid])["ids"]:
            self._episodic.update(documents=[doc], metadatas=[meta], ids=[eid])
        else:
            self._episodic.add(documents=[doc], metadatas=[meta], ids=[eid])
        return eid

    def get_platform_rules(self, platform: str) -> dict:
        """Return formatting rules for a platform; falls back to instagram."""
        pid     = f"platform_{platform.lower()}"
        results = self._procedural.get(ids=[pid])
        if results["ids"]:
            return results["metadatas"][0]
        fallback = self._procedural.get(ids=["platform_instagram"])
        return fallback["metadatas"][0] if fallback["ids"] else _PLATFORM_RULES["instagram"]

    # ── Maintenance ───────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Collection counts — used by GET /api/orchestrate/memory-status."""
        return {
            "semantic":   self._semantic.count(),
            "episodic":   self._episodic.count(),
            "procedural": self._procedural.count(),
        }

    def reseed(self) -> None:
        """Re-seed semantic collection from current brand_profile.json.
        Called after onboarding resets so brand voice stays fresh."""
        try:
            self._client.delete_collection("semantic")
        except Exception:
            pass
        self._semantic = self._client.get_or_create_collection("semantic")
        self._seed_semantic(self._brand_profile_path)
        self._seed_episodic(self._workbench_db_path)
