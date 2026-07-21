from __future__ import annotations

import io
import os
import shutil
import time
from pathlib import Path
from typing import BinaryIO

from pallisade_core.settings import get_settings
from pallisade_core.storage.backend import sign_url_token


class LocalDiskStorage:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or get_settings().storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        if not key or key.startswith("/"):
            raise ValueError(f"invalid storage key: {key!r}")
        candidate = (self.root / key).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as e:
            raise ValueError(f"key escapes storage root: {key!r}") from e
        return candidate

    def put(self, key: str, data: BinaryIO, content_type: str) -> None:
        target = self._path_for(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out:
            shutil.copyfileobj(data, out)

    def get(self, key: str) -> BinaryIO:
        target = self._path_for(key)
        return target.open("rb")

    def delete(self, key: str) -> None:
        target = self._path_for(key)
        if target.exists():
            target.unlink()

    def list(self, prefix: str) -> list[str]:
        base = self._path_for(prefix) if prefix else self.root
        if not base.exists():
            return []
        if base.is_file():
            return [str(base.relative_to(self.root)).replace(os.sep, "/")]
        out = []
        for p in base.rglob("*"):
            if p.is_file():
                out.append(str(p.relative_to(self.root)).replace(os.sep, "/"))
        return out

    def signed_url(self, key: str, expires_in: int = 3600) -> str:
        self._path_for(key)
        exp = int(time.time()) + expires_in
        sig = sign_url_token(key, exp=exp)
        return f"/storage/{key}?sig={sig}&exp={exp}"
