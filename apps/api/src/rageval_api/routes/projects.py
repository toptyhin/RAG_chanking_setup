from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from rageval_api.deps import ProjectRepoDep
from rageval_api.schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, repo: ProjectRepoDep) -> ProjectOut:
    project = await repo.create(name=body.name, description=body.description)
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=list[ProjectOut])
async def list_projects(repo: ProjectRepoDep) -> list[ProjectOut]:
    projects = await repo.list()
    return [
        ProjectOut(
            id=p.id,
            name=p.name,
            description=p.description,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, repo: ProjectRepoDep) -> ProjectOut:
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
