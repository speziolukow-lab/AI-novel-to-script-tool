"""Project management API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Project, ProjectStatus

router = APIRouter()


@router.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects, newest first."""
    result = await db.execute(
        select(Project)
        .order_by(Project.created_at.desc())
        .options(selectinload(Project.chapters), selectinload(Project.characters))
    )
    projects = result.scalars().unique().all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "author": p.author,
            "status": p.status.value,
            "style": p.style,
            "total_chapters": p.total_chapters,
            "completed_chapters": sum(
                1 for c in p.chapters if c.status.value == "completed"
            ),
            "created_at": p.created_at.isoformat(),
        }
        for p in projects
    ]


@router.get("/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single project with its chapters."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.chapters), selectinload(Project.characters))
    )
    project = result.scalars().unique().first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return {
        "id": project.id,
        "title": project.title,
        "author": project.author,
        "status": project.status.value,
        "style": project.style,
        "total_chapters": project.total_chapters,
        "chapters": [
            {
                "id": c.id,
                "chapter_num": c.chapter_num,
                "title": c.title,
                "status": c.status.value,
                "script_text": c.script_text,
                "scenes": c.scenes,
                "characters": c.characters_in_chapter,
                "error_message": c.error_message,
            }
            for c in sorted(project.chapters, key=lambda c: c.chapter_num)
        ],
        "characters": [
            {
                "id": c.id,
                "name": c.name,
                "aliases": c.aliases,
                "description": c.description,
                "traits": c.traits,
            }
            for c in project.characters
        ],
        "created_at": project.created_at.isoformat(),
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project and all associated data."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    await db.delete(project)
    await db.commit()
    return {"detail": "项目已删除"}
