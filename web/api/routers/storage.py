from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from pallisade_core.storage.backend import verify_url_token
from pallisade_core.storage.local_disk import LocalDiskStorage

router = APIRouter(tags=["storage"])


@router.get("/storage/{key:path}")
def get_signed(key: str, sig: str, exp: int):
    if not verify_url_token(key, sig=sig, exp=exp):
        raise HTTPException(403, "invalid or expired signature")
    storage = LocalDiskStorage()
    try:
        f = storage.get(key)
    except FileNotFoundError:
        raise HTTPException(404, "not found")

    def stream():
        try:
            chunk = f.read(64 * 1024)
            while chunk:
                yield chunk
                chunk = f.read(64 * 1024)
        finally:
            f.close()

    return StreamingResponse(stream(), media_type="application/octet-stream")
