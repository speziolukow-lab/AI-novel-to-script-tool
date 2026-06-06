"""Chapters API — trigger AI adaptation for individual chapters."""

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Project, Chapter, ChapterStatus, ProjectStatus, Adaptation
from app.services.ai_adapter import ai_adapter
from app.services.text_parser import split_long_chapter
from app.core.config import settings

router = APIRouter()


@router.post("/chapters/{chapter_id}/adapt")
async def adapt_chapter(
    chapter_id: str,
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

    # Mark chapter & adaptation as adapting
    chapter.status = ChapterStatus.ADAPTING
    chapter.project.status = ProjectStatus.ADAPTING

    # Upsert adaptation record for the project's current style
    style = chapter.project.style
    adapt_result = await db.execute(
        select(Adaptation).where(
            Adaptation.chapter_id == chapter.id,
            Adaptation.style == style,
        )
    )
    adaptation = adapt_result.scalar_one_or_none()
    if not adaptation:
        adaptation = Adaptation(chapter_id=chapter.id, style=style)
        db.add(adaptation)
    adaptation.status = ChapterStatus.ADAPTING
    await db.commit()

    # Run adaptation in background (use asyncio.create_task instead of
    # BackgroundTasks to preserve the async greenlet context required by
    # SQLAlchemy's async engine).
    asyncio.create_task(
        _run_adaptation(
            chapter_id=chapter.id,
            project_id=chapter.project.id,
            style=chapter.project.style,
        )
    )

    return {
        "chapter_id": chapter.id,
        "status": "adapting",
        "message": f"章节「{chapter.title}」开始改编...",
    }


@router.post("/projects/{project_id}/adapt-all")
async def adapt_all_chapters(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger adaptation for all chapters in a project."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.chapters).selectinload(Chapter.adaptations),
        )
    )
    project = result.scalars().unique().first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    style = project.style

    def _is_pending_for_style(c: Chapter) -> bool:
        for a in (c.adaptations or []):
            if a.style == style:
                return a.status in (ChapterStatus.PENDING, ChapterStatus.FAILED)
        return True  # no adaptation record → pending

    pending_chapters = [c for c in project.chapters if _is_pending_for_style(c)]

    if not pending_chapters:
        raise HTTPException(status_code=400, detail="没有待改编的章节")

    project.status = ProjectStatus.ADAPTING
    await db.commit()

    for chapter in pending_chapters:
        chapter.status = ChapterStatus.ADAPTING
        # Upsert adaptation record
        for a in (chapter.adaptations or []):
            if a.style == style:
                a.status = ChapterStatus.ADAPTING
                break
        else:
            adaptation = Adaptation(chapter_id=chapter.id, style=style, status=ChapterStatus.ADAPTING)
            db.add(adaptation)
    await db.commit()

    for chapter in pending_chapters:
        asyncio.create_task(
            _run_adaptation(
                chapter_id=chapter.id,
                project_id=project.id,
                style=project.style,
            )
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

    Uses asyncio.to_thread() to avoid SQLAlchemy async greenlet issues
    with sqlite+aiosqlite in background coroutines.
    """
    from app.core.database import SyncSessionLocal

    def _sync_work() -> None:
        with SyncSessionLocal() as db:
            try:
                # Reload chapter
                result = db.execute(
                    select(Chapter).where(Chapter.id == chapter_id)
                )
                chapter = result.scalar_one_or_none()
                if not chapter:
                    return

                # Get or create adaptation record for this (chapter, style)
                result = db.execute(
                    select(Adaptation).where(
                        Adaptation.chapter_id == chapter_id,
                        Adaptation.style == style,
                    )
                )
                adaptation = result.scalar_one_or_none()
                if not adaptation:
                    adaptation = Adaptation(chapter_id=chapter_id, style=style)
                    db.add(adaptation)

                # Reload project for character context
                result = db.execute(
                    select(Project)
                    .where(Project.id == project_id)
                    .options(selectinload(Project.characters), selectinload(Project.chapters))
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

                # Get previous chapter's adaptation (same style) for continuity
                prev_context = None
                if project:
                    prev_chapters = sorted(
                        [c for c in project.chapters if c.chapter_num < chapter.chapter_num],
                        key=lambda c: c.chapter_num,
                    )
                    # Find the most recent prev chapter with a completed adaptation for this style
                    for prev_ch in reversed(prev_chapters):
                        # Check prev chapter's adaptations for same style
                        prev_adapt_result = db.execute(
                            select(Adaptation).where(
                                Adaptation.chapter_id == prev_ch.id,
                                Adaptation.style == style,
                                Adaptation.status == ChapterStatus.COMPLETED,
                            )
                        )
                        prev_adapt = prev_adapt_result.scalar_one_or_none()
                        if prev_adapt and prev_adapt.script_text:
                            prev_text = prev_adapt.script_text
                            prev_context = prev_text[-min(500, len(prev_text)):]
                            break

                # Split if too long
                chunks = split_long_chapter(
                    chapter.original_text or "",
                    max_length=settings.MAX_CHAPTER_LENGTH,
                    overlap=settings.CHAPTER_OVERLAP,
                )

                # Adapt each chunk (sync)
                script_parts = []
                for i, chunk in enumerate(chunks):
                    script_part = ai_adapter.adapt_chapter_sync(
                        chapter_text=chunk,
                        style=style,
                        character_context=character_context,
                        previous_scene_context=prev_context if i == 0 else script_parts[-1][-300:],
                    )
                    script_parts.append(script_part)

                full_script = "\n\n".join(script_parts)

                # Update adaptation record
                adaptation.script_text = full_script
                adaptation.status = ChapterStatus.COMPLETED
                # Also update chapter for backward compatibility
                chapter.script_text = full_script
                chapter.status = ChapterStatus.COMPLETED
                db.commit()

                # Check if all chapters done, update project
                _maybe_complete_project_sync(db, project_id, style)

            except Exception as e:
                logger.exception(f"Chapter adaptation failed: chapter_id={chapter_id}")
                try:
                    # Mark adaptation as failed
                    result = db.execute(
                        select(Adaptation).where(
                            Adaptation.chapter_id == chapter_id,
                            Adaptation.style == style,
                        )
                    )
                    adaptation = result.scalar_one_or_none()
                    if adaptation:
                        adaptation.status = ChapterStatus.FAILED
                        adaptation.error_message = str(e)
                        db.commit()

                    # Also mark chapter for backward compat
                    result = db.execute(select(Chapter).where(Chapter.id == chapter_id))
                    chapter = result.scalar_one_or_none()
                    if chapter:
                        chapter.status = ChapterStatus.FAILED
                        chapter.error_message = str(e)
                        db.commit()

                    # Update project status
                    result = db.execute(select(Project).where(Project.id == project_id))
                    project = result.scalar_one_or_none()
                    if project:
                        project.status = ProjectStatus.FAILED
                        db.commit()
                except Exception:
                    logger.exception("Failed to save error state")

    await asyncio.to_thread(_sync_work)


def _maybe_complete_project_sync(db, project_id: str, style: str = "film"):
    """Sync version: check if all chapters have completed/failed adaptation for the given style."""
    result = db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.chapters).selectinload(Chapter.adaptations),
        )
    )
    project = result.scalars().unique().first()
    if not project:
        return

    all_done = True
    any_completed = False
    for c in project.chapters:
        adaptation = db.execute(
            select(Adaptation).where(
                Adaptation.chapter_id == c.id,
                Adaptation.style == style,
            )
        ).scalar_one_or_none()
        if adaptation:
            if adaptation.status == ChapterStatus.COMPLETED:
                any_completed = True
            elif adaptation.status not in (ChapterStatus.COMPLETED, ChapterStatus.FAILED):
                all_done = False
        else:
            all_done = False  # no adaptation yet for this style

    if all_done:
        project.status = ProjectStatus.COMPLETED if any_completed else ProjectStatus.FAILED
        db.commit()


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
