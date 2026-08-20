"""Local HF hub cache directory scanning."""

from __future__ import annotations

from pathlib import Path

from rageval_hf_hub.local_cache import list_cached_hub_models


def test_list_cached_hub_models_from_dirs(tmp_path: Path) -> None:
    hub = tmp_path / "hub"
    st = tmp_path / "sentence-transformers"
    (hub / "models--unsloth--Qwen3-Embedding-0.6B" / "snapshots" / "abc").mkdir(
        parents=True
    )
    blob = hub / "models--unsloth--Qwen3-Embedding-0.6B" / "snapshots" / "abc" / "model.safetensors"
    blob.write_bytes(b"x" * 1000)
    (st / "models--sentence-transformers--all-MiniLM-L6-v2" / "blobs").mkdir(
        parents=True
    )
    (st / "models--sentence-transformers--all-MiniLM-L6-v2" / "blobs" / "w").write_bytes(
        b"y" * 50
    )
    # Noise
    (hub / ".locks").mkdir()
    (hub / "not-a-model").mkdir()

    rows = list_cached_hub_models(roots=[hub, st])
    ids = {r.model_id for r in rows}
    assert "unsloth/Qwen3-Embedding-0.6B" in ids
    assert "sentence-transformers/all-MiniLM-L6-v2" in ids

    qwen = next(r for r in rows if r.model_id.startswith("unsloth/"))
    assert qwen.size_bytes == 1000

    filtered = list_cached_hub_models(roots=[hub, st], query="qwen3")
    assert [r.model_id for r in filtered] == ["unsloth/Qwen3-Embedding-0.6B"]
