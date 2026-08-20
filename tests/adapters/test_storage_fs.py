"""Object store FS adapter tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from rageval_storage_fs import FileSystemObjectStore


def test_put_get_exists_delete(tmp_path: Path) -> None:
    store = FileSystemObjectStore(tmp_path / "objects")
    key = "raw_abc/files/hello.txt"
    digest = store.put(key, b"hello")
    assert len(digest) == 64
    assert store.exists(key)
    assert store.get(key) == b"hello"
    store.delete(key)
    assert not store.exists(key)


def test_rejects_path_escape(tmp_path: Path) -> None:
    store = FileSystemObjectStore(tmp_path / "objects")
    with pytest.raises(ValueError):
        store.put("../outside.txt", b"x")
