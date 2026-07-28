"""
Tagged post outcomes — the creator's ground truth.

Reads the Workbench `actual_outcome` tags (succeeded / underperformed / failed)
the creator sets via the outcome pills, and splits them into winners vs losers,
each enriched with a detected hook pattern. Shared by the Playbook agent
(learns rules from wins vs misses) and the Weekly Brief planner (emulate
winners, avoid losers).
"""

import json
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "workbench.db"


def _caption_of(content) -> str:
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return content
    if isinstance(content, dict):
        return str(content.get("caption") or content.get("hook") or "")
    return ""


def gather_tagged_outcomes(db_path: Path = _DB_PATH) -> tuple[list[dict], list[dict]]:
    """
    Return (winners, losers) from the Workbench tags. Each item is
    {"caption": str, "hook_pattern": str}. Cheap SQLite read, no LLM.
    Never raises — returns ([], []) if the DB is missing/unreadable.
    """
    from src.generation.confidence_scorer import _detect_hook_pattern

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT content, actual_outcome FROM workbench_assets "
            "WHERE actual_outcome IS NOT NULL AND actual_outcome != ''"
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return [], []

    winners, losers = [], []
    for r in rows:
        caption = _caption_of(r["content"])
        if not caption:
            continue
        ep = {"caption": caption, "hook_pattern": _detect_hook_pattern(caption)}
        if r["actual_outcome"] == "succeeded":
            winners.append(ep)
        elif r["actual_outcome"] in ("underperformed", "failed"):
            losers.append(ep)
    return winners, losers
