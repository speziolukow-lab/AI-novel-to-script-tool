"""Chapters API — trigger AI adaptation for individual chapters."""

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Project, Chapter, ChapterStatus, ProjectStatus, Adaptation, Character
from app.services.ai_adapter import ai_adapter
from app.services.text_parser import split_long_chapter
from app.services.text_utils import number_paragraphs
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


@router.post("/chapters/{chapter_id}/extract-characters")
async def extract_chapter_characters(
    chapter_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Extract characters for a single chapter using the 5-chapter sliding window
    rule (chapters N-2 to N+2), then merge into the project's characters table.
    """
    result = await db.execute(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(selectinload(Chapter.project).selectinload(Project.chapters),
                 selectinload(Chapter.project).selectinload(Project.characters))
    )
    chapter = result.scalars().unique().first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    project = chapter.project
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # Build 5-chapter sliding window
    all_chapters = sorted(project.chapters, key=lambda c: c.chapter_num)
    chapter_num = chapter.chapter_num
    win_start = max(1, chapter_num - 2)
    win_end = min(
        max(c.chapter_num for c in all_chapters), chapter_num + 2
    )
    window_texts = [
        c.original_text for c in all_chapters
        if win_start <= c.chapter_num <= win_end and c.original_text
    ]
    window_text = "\n\n".join(window_texts)
    if not window_text.strip():
        raise HTTPException(status_code=400, detail="章节没有文本内容")

    # Extract characters
    characters = await asyncio.to_thread(
        ai_adapter.extract_characters_sync, window_text
    )

    if not characters:
        raise HTTPException(status_code=500, detail="角色提取失败，未获取到任何角色")

    # Merge into characters table by name
    existing_chars = {c.name: c for c in project.characters}
    for c_data in characters:
        name = c_data.get("name", "").strip()
        if not name:
            continue
        if name in existing_chars:
            # Merge with existing
            existing = existing_chars[name]
            existing_aliases = list(set(existing.aliases or []) | set(c_data.get("aliases") or []))
            existing_traits = list(set(existing.traits or []) | set(c_data.get("traits") or []))
            new_desc = c_data.get("description") or ""
            if len(new_desc) > len(existing.description or ""):
                existing.description = new_desc
            existing.aliases = existing_aliases
            existing.traits = existing_traits
        else:
            char = Character(
                project_id=project.id,
                name=name,
                aliases=c_data.get("aliases", []),
                description=c_data.get("description", ""),
                traits=c_data.get("traits", []),
                relationships=c_data.get("relationships"),
            )
            db.add(char)
            existing_chars[name] = char

    await db.commit()

    # Reload to get updated list
    result = await db.execute(
        select(Project)
        .where(Project.id == project.id)
        .options(selectinload(Project.characters))
    )
    project = result.scalars().unique().first()

    return {
        "chapter_id": chapter_id,
        "window": f"第{win_start}-{win_end}章",
        "characters": [
            {
                "id": c.id,
                "name": c.name,
                "aliases": c.aliases,
                "description": c.description,
                "traits": c.traits,
            }
            for c in (project.characters if project else [])
        ],
        "count": len(project.characters if project else []),
    }


from pydantic import BaseModel


class AdaptBatchRequest(BaseModel):
    chapter_ids: list[str]
    style: str = ""  # optional; if not provided, uses project.style


class UpdateAdaptationRequest(BaseModel):
    script_text: str


@router.put("/chapters/{chapter_id}/adaptations/{style}")
async def update_adaptation(
    chapter_id: str,
    style: str,
    req: UpdateAdaptationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually update the script text for a chapter's adaptation."""
    if style not in ("film", "comic", "stage"):
        raise HTTPException(status_code=422, detail=f"不支持的风格：{style}")

    result = await db.execute(
        select(Adaptation).where(
            Adaptation.chapter_id == chapter_id,
            Adaptation.style == style,
        )
    )
    adaptation = result.scalar_one_or_none()
    if not adaptation:
        raise HTTPException(status_code=404, detail="改编记录不存在，请先执行改编")

    adaptation.script_text = req.script_text
    adaptation.status = ChapterStatus.COMPLETED
    await db.commit()

    return {
        "chapter_id": chapter_id,
        "style": style,
        "message": "剧本已更新",
    }


@router.post("/projects/{project_id}/adapt-batch")
async def adapt_batch_chapters(
    project_id: str,
    req: AdaptBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger adaptation for a selection of chapters (1-5 at a time)."""
    if not req.chapter_ids or len(req.chapter_ids) < 1:
        raise HTTPException(status_code=400, detail="请至少选择 1 个章节")
    if len(req.chapter_ids) > 5:
        raise HTTPException(status_code=400, detail="一次最多批量改编 5 个章节")

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

    style = req.style if req.style in ("film", "comic", "stage") else project.style
    valid_ids = set(req.chapter_ids)

    chapters_to_adapt: list[Chapter] = []
    for c in project.chapters:
        if c.id not in valid_ids:
            continue
        # Check if already completed for this style — skip those
        for a in (c.adaptations or []):
            if a.style == style and a.status == ChapterStatus.COMPLETED:
                break
        else:
            chapters_to_adapt.append(c)

    if not chapters_to_adapt:
        raise HTTPException(status_code=400, detail="所选章节均已完成改编，无需重复改编")

    project.status = ProjectStatus.ADAPTING
    await db.commit()

    for chapter in chapters_to_adapt:
        chapter.status = ChapterStatus.ADAPTING
        for a in (chapter.adaptations or []):
            if a.style == style:
                a.status = ChapterStatus.ADAPTING
                break
        else:
            adaptation = Adaptation(chapter_id=chapter.id, style=style, status=ChapterStatus.ADAPTING)
            db.add(adaptation)
    await db.commit()

    for chapter in chapters_to_adapt:
        asyncio.create_task(
            _run_adaptation(
                chapter_id=chapter.id,
                project_id=project.id,
                style=style,
            )
        )

    return {
        "project_id": project.id,
        "chapters_queued": len(chapters_to_adapt),
        "message": f"开始改编 {len(chapters_to_adapt)} 个章节...",
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

                # ── Load character profiles from Character table ──
                # Characters are generated via the "生成角色档案" button
                # (POST /projects/{id}/extract-characters) and saved to the DB.
                character_context = None
                if project and project.characters:
                    char_lines = [
                        f"- {c.name}"
                        + (f"（{'、'.join(c.traits or [])}）" if c.traits else "")
                        + f"：{c.description or ''}"
                        for c in project.characters
                    ]
                    if char_lines:
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

                # Number paragraphs globally for alignment tracking
                numbered_text, total_paras = number_paragraphs(
                    chapter.original_text or ""
                )

                # Split into chunks (paragraph-level overlap)
                chunks = split_long_chapter(
                    numbered_text,
                    max_length=settings.MAX_CHAPTER_LENGTH,
                    overlap_paras=3,
                )

                # Adapt each chunk with alignment
                script_parts: list[str] = []
                all_alignment: list[dict] = []
                all_structured_scenes: list[dict] = []
                cumulative_scenes = 0

                for i, chunk_info in enumerate(chunks):
                    chunk_text = chunk_info["text"]

                    prev = (
                        prev_context if i == 0
                        else script_parts[-1][-300:]
                    )

                    chunk_prose, chunk_scenes, chunk_alignment = (
                        ai_adapter.adapt_chapter_sync_with_alignment(
                            chapter_text=chunk_text,
                            style=style,
                            character_context=character_context,
                            previous_scene_context=prev,
                        )
                    )

                    # Remap scene numbers: chunk-local → global
                    for entry in chunk_alignment:
                        entry["scene"] += cumulative_scenes
                    for s in chunk_scenes:
                        s["scene_num"] = s.get("scene_num", 0) + cumulative_scenes

                    if chunk_alignment:
                        cumulative_scenes = max(
                            e["scene"] for e in chunk_alignment
                        )
                    elif chunk_scenes:
                        cumulative_scenes = max(
                            s.get("scene_num", 0) for s in chunk_scenes
                        )

                    all_alignment.extend(chunk_alignment)
                    all_structured_scenes.extend(chunk_scenes)
                    script_parts.append(chunk_prose)

                full_script = "\n\n".join(script_parts)

                # Update adaptation record
                adaptation.script_text = full_script
                adaptation.scenes = {
                    "alignment": all_alignment,
                    "total_paras": total_paras,
                    "version": 2,
                    "structured_scenes": all_structured_scenes,
                }
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
