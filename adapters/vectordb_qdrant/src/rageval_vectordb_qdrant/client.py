"""Thin Qdrant wrapper for create / upsert / search / delete."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


@dataclass(slots=True)
class SearchHit:
    id: str
    score: float


@dataclass(slots=True)
class IndexSizeStats:
    """Best-effort collection storage stats.

    Prefer Qdrant telemetry when available. Otherwise fall back to a
    points × dim × bytes estimate (proxy), or nulls if even that fails.
    """

    index_ram_mb: float | None
    index_disk_mb: float | None
    source: str  # "telemetry" | "estimate" | "unavailable"


def _binary_quant_config() -> qm.BinaryQuantization:
    return qm.BinaryQuantization(binary=qm.BinaryQuantizationConfig())


def _scalar_quant_config() -> qm.ScalarQuantization:
    return qm.ScalarQuantization(
        scalar=qm.ScalarQuantizationConfig(
            type=qm.ScalarType.INT8,
            quantile=0.99,
            always_ram=False,
        )
    )


def quantization_to_qdrant(quantization: dict[str, Any] | None) -> qm.QuantizationConfig | None:
    if not quantization:
        return None
    method = str(quantization.get("method") or "").lower()
    if method in {"", "none"}:
        return None
    if method == "binary":
        return _binary_quant_config()
    if method == "scalar":
        return _scalar_quant_config()
    raise ValueError(f"unsupported quantization method: {method!r}")


def parse_quantization_axis(value: Any) -> tuple[dict[str, Any] | None, bool | None]:
    """Normalize swept/fixed quantization axis → (index config, search rescore).

    Accepted forms:
    - None / "none" / false
    - "binary" / "binary+rescore"
    - "scalar" / "scalar+rescore"
    - {"method": "binary"|"scalar", "rescore": true, ...}
    """
    if value is None or value is False or value == "none":
        return None, None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"", "none"}:
            return None, None
        if lowered == "binary":
            return {"method": "binary", "rescore": False}, False
        if lowered in {"binary+rescore", "binary_rescore"}:
            return {"method": "binary", "rescore": True}, True
        if lowered == "scalar":
            return {"method": "scalar", "rescore": False}, False
        if lowered in {"scalar+rescore", "scalar_rescore"}:
            return {"method": "scalar", "rescore": True}, True
        raise ValueError(f"unsupported quantization axis value: {value!r}")
    if isinstance(value, dict):
        if not value.get("enabled", True):
            return None, None
        method = str(value.get("method") or "none").lower()
        if method in {"", "none"}:
            return None, None
        if method not in {"binary", "scalar"}:
            raise ValueError(f"unsupported quantization method: {method!r}")
        rescore = value.get("rescore")
        rescore_bool = bool(rescore) if rescore is not None else None
        config = {
            "method": method,
            "rescore": bool(rescore_bool) if rescore_bool is not None else False,
        }
        config.update({k: v for k, v in value.items() if k not in config})
        return config, rescore_bool
    raise ValueError(f"unsupported quantization axis value: {value!r}")


def hnsw_to_qdrant(hnsw: dict[str, Any] | None) -> qm.HnswConfigDiff | None:
    if not hnsw:
        return None
    kwargs: dict[str, Any] = {}
    if "m" in hnsw and hnsw["m"] is not None:
        kwargs["m"] = int(hnsw["m"])
    if "ef_construct" in hnsw and hnsw["ef_construct"] is not None:
        kwargs["ef_construct"] = int(hnsw["ef_construct"])
    if not kwargs:
        return None
    return qm.HnswConfigDiff(**kwargs)


class QdrantVectorStore:
    def __init__(self, url: str, *, upsert_batch_size: int = 512) -> None:
        self._client = QdrantClient(url=url)
        self._upsert_batch_size = max(1, int(upsert_batch_size))
        self._size_cache: dict[str, IndexSizeStats] = {}

    @property
    def client(self) -> QdrantClient:
        return self._client

    def recreate_collection(
        self,
        name: str,
        dimension: int,
        *,
        quantization: dict[str, Any] | None = None,
        hnsw: dict[str, Any] | None = None,
    ) -> None:
        self._size_cache.pop(name, None)
        if self._client.collection_exists(name):
            self._client.delete_collection(name)
        self._client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=dimension, distance=qm.Distance.COSINE),
            quantization_config=quantization_to_qdrant(quantization),
            hnsw_config=hnsw_to_qdrant(hnsw),
        )

    def delete_collection(self, name: str) -> None:
        self._size_cache.pop(name, None)
        if self._client.collection_exists(name):
            self._client.delete_collection(name)

    def upsert(
        self,
        collection: str,
        ids: list[str],
        vectors: np.ndarray,
        payloads: list[dict] | None = None,
    ) -> None:
        if len(ids) != len(vectors):
            raise ValueError("ids and vectors length mismatch")
        for start in range(0, len(ids), self._upsert_batch_size):
            end = min(start + self._upsert_batch_size, len(ids))
            points = []
            for i in range(start, end):
                point_id = ids[i]
                payload = payloads[i] if payloads else {"chunk_id": point_id}
                points.append(
                    qm.PointStruct(
                        id=self._point_uuid(point_id),
                        vector=vectors[i].astype(float).tolist(),
                        payload={**payload, "chunk_id": point_id},
                    )
                )
            self._client.upsert(collection_name=collection, points=points)
        self._size_cache.pop(collection, None)

    def search(
        self,
        collection: str,
        vector: np.ndarray,
        top_k: int,
        *,
        rescore: bool | None = None,
        ef_search: int | None = None,
    ) -> list[SearchHit]:
        quant_params = None
        if rescore is not None:
            quant_params = qm.QuantizationSearchParams(rescore=rescore)
        search_params = None
        if quant_params is not None or ef_search is not None:
            search_params = qm.SearchParams(
                quantization=quant_params,
                hnsw_ef=ef_search,
            )
        results = self._client.query_points(
            collection_name=collection,
            query=vector.astype(float).tolist(),
            limit=top_k,
            with_payload=True,
            search_params=search_params,
        )
        hits: list[SearchHit] = []
        for point in results.points:
            payload = point.payload or {}
            chunk_id = str(payload.get("chunk_id") or point.id)
            hits.append(SearchHit(id=chunk_id, score=float(point.score or 0.0)))
        return hits

    def get_collection_info(self, name: str) -> Any:
        return self._client.get_collection(name)

    def get_index_size_mb(
        self,
        name: str,
        *,
        dimension: int | None = None,
        quantization: dict[str, Any] | None = None,
    ) -> IndexSizeStats:
        """Best-effort RAM/disk size for a collection.

        Fallback (documented): when telemetry is unavailable, estimate
        ``points_count * dimension * bytes_per_dim`` as both RAM and disk proxy.
        Binary quantization uses 1 bit/dim. Scalar int8 uses 1 byte/dim.
        Otherwise float32.
        """
        cached = self._size_cache.get(name)
        if cached is not None:
            return cached

        telem = self._size_from_telemetry(name)
        if telem is not None:
            self._size_cache[name] = telem
            return telem

        try:
            info = self._client.get_collection(name)
        except Exception:  # noqa: BLE001
            return IndexSizeStats(index_ram_mb=None, index_disk_mb=None, source="unavailable")

        points = int(info.points_count or 0)
        dim = dimension
        if dim is None:
            vectors = info.config.params.vectors
            if hasattr(vectors, "size"):
                dim = int(vectors.size)
            elif isinstance(vectors, dict) and vectors:
                first = next(iter(vectors.values()))
                dim = int(getattr(first, "size", 0)) or None
        if not dim or points <= 0:
            return IndexSizeStats(index_ram_mb=None, index_disk_mb=None, source="unavailable")

        method = (quantization or {}).get("method") if quantization else None
        if method == "binary":
            bytes_per = 1.0 / 8.0
        elif method == "scalar":
            bytes_per = 1.0
        else:
            bytes_per = 4.0
        mb = (points * dim * bytes_per) / (1024.0 * 1024.0)
        result = IndexSizeStats(index_ram_mb=mb, index_disk_mb=mb, source="estimate")
        self._size_cache[name] = result
        return result

    @staticmethod
    def _accumulate_shard_sizes(shard: Any) -> tuple[float, float, bool]:
        ram = 0.0
        disk = 0.0
        found = False
        vectors_size = getattr(shard, "vectors_size_bytes", None)
        payloads_size = getattr(shard, "payloads_size_bytes", None)
        if vectors_size is not None:
            ram += float(vectors_size)
            found = True
        if payloads_size is not None:
            disk += float(payloads_size)
            found = True
        for seg in getattr(shard, "segments", None) or []:
            info = getattr(seg, "info", seg)
            ram_usage = getattr(info, "ram_usage_bytes", None)
            disk_usage = getattr(info, "disk_usage_bytes", None)
            if ram_usage is not None:
                ram += float(ram_usage)
                found = True
            if disk_usage is not None:
                disk += float(disk_usage)
                found = True
        return ram, disk, found

    @staticmethod
    def _stats_from_collection_telemetry(coll: Any) -> IndexSizeStats | None:
        ram = 0.0
        disk = 0.0
        found = False
        for shard in getattr(coll, "shards", None) or []:
            shard_ram, shard_disk, shard_found = QdrantVectorStore._accumulate_shard_sizes(
                shard
            )
            ram += shard_ram
            disk += shard_disk
            found = found or shard_found
        if not found:
            return None
        ram_mb = ram / (1024.0 * 1024.0) if ram else None
        if disk:
            disk_mb = disk / (1024.0 * 1024.0)
        elif ram:
            disk_mb = ram / (1024.0 * 1024.0)
        else:
            disk_mb = None
        return IndexSizeStats(index_ram_mb=ram_mb, index_disk_mb=disk_mb, source="telemetry")

    def _size_from_telemetry(self, name: str) -> IndexSizeStats | None:
        try:
            telem = self._client.cluster_telemetry(details_level=3)
        except Exception:  # noqa: BLE001
            return None
        try:
            collections = getattr(telem, "collections", None)
            items = getattr(collections, "collections", None) if collections is not None else None
            if not items:
                return None
            for coll in items:
                coll_id = getattr(coll, "id", None) or getattr(coll, "name", None)
                if str(coll_id) != name:
                    continue
                return self._stats_from_collection_telemetry(coll)
        except Exception:  # noqa: BLE001
            return None
        return None

    @staticmethod
    def _point_uuid(chunk_id: str) -> str:
        # Qdrant accepts UUID or int; derive stable UUID5-like from sha1 hex.
        import hashlib
        import uuid

        digest = hashlib.sha1(
            chunk_id.encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()
        return str(uuid.UUID(digest[:32]))
