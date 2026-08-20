"""Stable ID generation for artifacts and runs."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any
from typing import Literal

IdPrefix = Literal[
    "raw",
    "clean",
    "chunks",
    "test",
    "index",
    "run",
    "proj",
    "doc",
    "chunk",
    "q",
]


def new_id(prefix: IdPrefix) -> str:
    """Return `{prefix}_{uuid4_hex}`."""
    return f"{prefix}_{uuid.uuid4().hex}"


def content_id(prefix: IdPrefix, *parts: Any) -> str:
    """Return a stable id for immutable generated content/configuration."""
    payload = json.dumps(
        parts,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:24]
    return f"{prefix}_{digest}"
