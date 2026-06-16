"""
Content Workbench — persistent scratchpad for saved creative assets.

SQLite-backed. Hybrid schema: JSON blob for content (handles all asset shapes
without migrations), typed columns only for fields actually queried.

DB location: data/workbench.db  (created on first request)

Endpoints:
  POST   /api/workbench/assets           save a generated asset
  GET    /api/workbench/assets           list all (?pinned=true|false)
  PATCH  /api/workbench/assets/{id}      toggle pin / record outcome
  DELETE /api/workbench/assets/{id}      remove asset
"""

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _PROJECT_ROOT / "data" / "workbench.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS workbench_assets (
    id           TEXT PRIMARY KEY,
    asset_type   TEXT NOT NULL,
    cluster_label TEXT,
    cluster_id   INTEGER,
    content      TEXT NOT NULL,
    pinned       INTEGER NOT NULL DEFAULT 0,
    source_tab   TEXT,
    actual_outcome       TEXT,
    recovery_brief_generated INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@lru_cache(maxsize=1)
def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["pinned"] = bool(d["pinned"])
    d["recovery_brief_generated"] = bool(d["recovery_brief_generated"])
    try:
        d["content"] = json.loads(d["content"])
    except (json.JSONDecodeError, TypeError):
        pass
    return d


# ── Pydantic models ────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    asset_type: str
    content: Any
    cluster_label: str | None = None
    cluster_id: int | None = None
    source_tab: str | None = None


class AssetUpdate(BaseModel):
    pinned: bool | None = None
    actual_outcome: str | None = None
    recovery_brief_generated: bool | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/assets", status_code=201)
def save_asset(req: AssetCreate) -> dict:
    conn = _get_conn()
    asset_id = str(uuid4())
    content_str = (
        json.dumps(req.content)
        if not isinstance(req.content, str)
        else req.content
    )
    conn.execute(
        """
        INSERT INTO workbench_assets
            (id, asset_type, cluster_label, cluster_id, content, source_tab)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (asset_id, req.asset_type, req.cluster_label, req.cluster_id,
         content_str, req.source_tab),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM workbench_assets WHERE id = ?", (asset_id,)
    ).fetchone()
    return _row_to_dict(row)


@router.get("/assets")
def list_assets(pinned: bool | None = None) -> list[dict]:
    conn = _get_conn()
    if pinned is True:
        rows = conn.execute(
            "SELECT * FROM workbench_assets WHERE pinned = 1 ORDER BY created_at DESC"
        ).fetchall()
    elif pinned is False:
        rows = conn.execute(
            "SELECT * FROM workbench_assets WHERE pinned = 0 ORDER BY created_at DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM workbench_assets ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.patch("/assets/{asset_id}")
def update_asset(asset_id: str, req: AssetUpdate) -> dict:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM workbench_assets WHERE id = ?", (asset_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found.")

    updates: list[str] = []
    params: list[Any] = []

    if req.pinned is not None:
        updates.append("pinned = ?")
        params.append(1 if req.pinned else 0)
    if req.actual_outcome is not None:
        updates.append("actual_outcome = ?")
        params.append(req.actual_outcome)
    if req.recovery_brief_generated is not None:
        updates.append("recovery_brief_generated = ?")
        params.append(1 if req.recovery_brief_generated else 0)

    if not updates:
        return _row_to_dict(row)

    params.append(asset_id)
    conn.execute(
        f"UPDATE workbench_assets SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM workbench_assets WHERE id = ?", (asset_id,)
    ).fetchone()
    return _row_to_dict(row)


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: str) -> None:
    conn = _get_conn()
    result = conn.execute(
        "DELETE FROM workbench_assets WHERE id = ?", (asset_id,)
    )
    conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Asset not found.")
