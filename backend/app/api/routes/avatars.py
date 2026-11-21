"""Locally stored photos for creators and chatters.

The Infloww API exposes no profile images, so photos are uploaded by the agency and stored on this
server only (next to the SQLite cache). Nothing here talks to Infloww.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.api.deps import Auth
from app.core.config import get_settings

router = APIRouter(prefix="/api/avatars", dependencies=[Auth])

KINDS = {"creator", "employee"}
MAX_BYTES = 2 * 1024 * 1024
TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def avatar_dir() -> Path:
    d = get_settings().database_path.parent / "avatars"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sniff(data: bytes) -> str | None:
    """Trust magic bytes, never the client's Content-Type."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _check(kind: str, ident: str) -> None:
    if kind not in KINDS or not ident.isdigit() or len(ident) > 32:
        raise HTTPException(400, "invalid avatar target")


def _existing(kind: str, ident: str) -> Path | None:
    for ext in TYPES:
        p = avatar_dir() / f"{kind}-{ident}.{ext}"
        if p.exists():
            return p
    return None


def index() -> dict[str, int]:
    """{"creator:123": mtime, ...} so the UI knows who has a photo and can bust its cache on change."""
    out: dict[str, int] = {}
    for p in avatar_dir().iterdir():
        stem, _, ext = p.name.rpartition(".")
        kind, _, ident = stem.partition("-")
        if ext in TYPES and kind in KINDS and ident.isdigit():
            out[f"{kind}:{ident}"] = int(p.stat().st_mtime)
    return out


@router.get("/{kind}/{ident}")
def get_avatar(kind: str, ident: str):
    _check(kind, ident)
    p = _existing(kind, ident)
    if not p:
        raise HTTPException(404, "no photo")
    return Response(p.read_bytes(), media_type=TYPES[p.suffix[1:]], headers={"Cache-Control": "private, max-age=300"})


@router.put("/{kind}/{ident}")
async def put_avatar(kind: str, ident: str, request: Request):
    _check(kind, ident)
    data = await request.body()
    if not data:
        raise HTTPException(400, "empty upload")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "photo must be 2 MB or smaller")
    ext = _sniff(data)
    if not ext:
        raise HTTPException(415, "photo must be PNG, JPEG or WebP")
    old = _existing(kind, ident)
    if old:
        old.unlink()
    target = avatar_dir() / f"{kind}-{ident}.{ext}"
    tmp = target.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)
    return {"ok": True, "key": f"{kind}:{ident}", "version": int(target.stat().st_mtime)}


@router.delete("/{kind}/{ident}")
def delete_avatar(kind: str, ident: str):
    _check(kind, ident)
    p = _existing(kind, ident)
    if p:
        p.unlink()
    return {"ok": True}
