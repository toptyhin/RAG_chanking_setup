"""Key/value object store backed by DATA_DIR/objects."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


class FileSystemObjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        if not key or key.startswith("/") or ".." in Path(key).parts:
            raise ValueError(f"invalid object key: {key!r}")
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError(f"object key escapes root: {key!r}")
        return path

    def put(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def get(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.is_file():
            path.unlink()

    def delete_prefix(self, prefix: str) -> int:
        """Delete all objects under `{prefix}/` (and a bare file at `prefix`)."""
        if not prefix or prefix.startswith("/") or ".." in Path(prefix).parts:
            raise ValueError(f"invalid object prefix: {prefix!r}")
        root = self.root.resolve()
        base = (self.root / prefix).resolve()
        if base != root and not str(base).startswith(str(root) + "/"):
            raise ValueError(f"object prefix escapes root: {prefix!r}")
        removed = 0
        if base.is_file():
            base.unlink()
            return 1
        if base.is_dir():
            for path in base.rglob("*"):
                if path.is_file():
                    removed += 1
            shutil.rmtree(base)
        return removed
