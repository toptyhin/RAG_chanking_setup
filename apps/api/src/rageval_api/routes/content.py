"""Read artifact manifest JSON from object store."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from rageval_api.deps import ArtifactRepoDep, ObjectStoreDep

router = APIRouter(tags=["artifacts"])


@router.get("/artifacts/{artifact_id}/content")
async def get_artifact_content(
    artifact_id: str,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> JSONResponse:
    record = await artifacts.get(artifact_id)
    if record is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    if not record.object_key:
        raise HTTPException(status_code=404, detail="artifact has no content")
    try:
        payload = json.loads(store.get(record.object_key).decode("utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="object missing in store") from exc
    return JSONResponse(payload)
