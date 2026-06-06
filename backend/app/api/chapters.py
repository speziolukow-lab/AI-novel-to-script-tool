"""Chapters API — trigger AI adaptation for individual chapters."""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Project, Chapter, ChapterStatus, ProjectStatus
from app.services.ai_adapter import ai_adapter
from app.services.text_parser import split_long_chapter
from app.core.config import settings

router = APIRouter()


@router.post("/chapters/{chapter_id}/adapt")
async def adapt_chapter(
    chapter_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger AI adaptation for a single chapter.

    If the chapter is very long, it will be split into chunks,
    each processed sequentially with context overlap.
    """
    result = await db.execute(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(selectinload(Chapter.project))
    )
    chapter = result.scalars().unique().first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if not chapter.original_text:
        raise HTTPException(status_code=400, detail="章节没有原始文本")

    # Mark as adapting
    chapter.status = ChapterStatus.ADAPTING
    chapter.project.status = ProjectStatus.ADAPTING
    await db.commit()

    # Run adaptation in background
    background_tasks.add_task(
        _run_adaptation,
        chapter_id=chapter.id,
        project_id=chapter.project.id,
        style=chapter.project.style,
    )

    return {
        "chapter_id": chapter.id,
        "status": "adapting",
        "message": f"章节「{chapter.title}」开始改编...",
    }


@router.post("/projects/{project_id}/adapt-all")
async def adapt_all_chapters(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger adaptation for all chapters in a project."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.chapters))
    )
    project = result.scalars().unique().first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    pending_chapters = [
        c for c in project.chapters
        if c.status in (ChapterStatus.PENDING, ChapterStatus.FAILED)
    ]

    if not pending_chapters:
        raise HTTPException(status_code=400, detail="没有待改编的章节")

    project.status = ProjectStatus.ADAPTING
    await db.commit()

    for chapter in pending_chapters:
        chapter.status = ChapterStatus.ADAPTING
    await db.commit()

    for chapter in pending_chapters:
        background_tasks.add_task(
            _run_adaptation,
            chapter_id=chapter.id,
            project_id=project.id,
            style=project.style,
        )

    return {
        "project_id": project.id,
        "chapters_queued": len(pending_chapters),
        "message": f"开始改编 {len(pending_chapters)} 个章节...",
    }


async def _run_adaptation(
    chapter_id: str,
    project_id: str,
    style: str = "film",
):
    """
    Background task: run AI adaptation on a chapter.

    Handles chapter splitting, character context, and updating the DB.
    """
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Reload chapter
            result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
            chapter = result.scalar_one_or_none()
            if not chapter:
                return

            # Reload project for character context
            result = await db.execute(
                select(Project)
                .where(Project.id == project_id)
                .options(selectinload(Project.characters))
            )
            project = result.scalars().unique().first()

            # Build character context
            character_context = None
            if project and project.characters:
                char_lines = [
                    f"- {c.name}（{''.join(c.traits or [])}）：{c.description or ''}"
                    for c in project.characters
                ]
                character_context = "\n".join(char_lines)

            # Get previous chapter's last scene for continuity
            prev_context = None
            if project:
                prev_chapters = sorted(
                    [c for c in project.chapters if c.chapter_num < chapter.chapter_num],
                    key=lambda c: c.chapter_num,
                )
                if prev_chapters and prev_chapters[-1].script_text:
                    # Take last 500 chars as context
                    prev_text = prev_chapters[-1].script_text
                    prev_context = prev_text[-min(500, len(prev_text)):]

            # Split if too long
            chunks = split_long_chapter(
                chapter.original_text or "",
                max_length=settings.MAX_CHAPTER_LENGTH,
                overlap=settings.CHAPTER_OVERLAP,
            )

            # Adapt each chunk
            script_parts = []
            for i, chunk in enumerate(chunks):
                script_part = await ai_adapter.adapt_chapter(
                    chapter_text=chunk,
                    style=style,
                    character_context=character_context,
                    previous_scene_context=prev_context if i == 0 else script_parts[-1][-300:],
                )
                script_parts.append(script_part)

            full_script = "\n\n".join(script_parts)

            # Update chapter
            chapter.script_text = full_script
            chapter.status = ChapterStatus.COMPLETED
            await db.commit()

            # Check if all chapters done, update project
            await _maybe_complete_project(db, project_id)

        except Exception as e:
            logger.exception(f"Chapter adaptation failed: chapter_id={chapter_id}")
            # Mark as failed
            result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
            chapter = result.scalar_one_or_none()
            if chapter:
                chapter.status = ChapterStatus.FAILED
                chapter.error_message = str(e)
                await db.commit()

            # Update project status
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            if project:
                project.status = ProjectStatus.FAILED
                await db.commit()


async def _maybe_complete_project(db: AsyncSession, project_id: str):
    """Check if all chapters are done and mark project as completed."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.chapters))
    )
    project = result.scalars().unique().first()
    if not project:
        return

    all_done = all(
        c.status in (ChapterStatus.COMPLETED, ChapterStatus.FAILED)
        for c in project.chapters
    )
    any_completed = any(c.status == ChapterStatus.COMPLETED for c in project.chapters)

    if all_done:
        project.status = ProjectStatus.COMPLETED if any_completed else ProjectStatus.FAILED
        await db.commit()
