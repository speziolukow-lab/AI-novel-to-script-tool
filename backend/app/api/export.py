"""Export API — download scripts in various formats."""

import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models import Project

router = APIRouter()


@router.get("/projects/{project_id}/export/markdown")
async def export_markdown(project_id: str, db: AsyncSession = Depends(get_db)):
    """Export the full script as a Markdown file."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.chapters))
    )
    project = result.scalars().unique().first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # Build markdown content
    lines = []
    lines.append(f"# {project.title}")
    if project.author:
        lines.append(f"\n**原著作者**：{project.author}")
    lines.append(f"\n**改编风格**：{project.style}")
    lines.append(f"\n**生成时间**：{project.updated_at.isoformat() if project.updated_at else ''}")
    lines.append("\n---\n")

    for chapter in sorted(project.chapters, key=lambda c: c.chapter_num):
        lines.append(f"## 第{chapter.chapter_num}章 {chapter.title or ''}\n")
        if chapter.script_text:
            lines.append(chapter.script_text)
        else:
            lines.append("（待改编...）\n")
        lines.append("\n---\n")

    content = "\n".join(lines)
    safe_title = project.title.replace(" ", "_").replace("/", "_")[:50]

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={safe_title}_剧本.md"},
    )


@router.get("/projects/{project_id}/export/txt")
async def export_txt(project_id: str, db: AsyncSession = Depends(get_db)):
    """Export the full script as a plain text file."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.chapters))
    )
    project = result.scalars().unique().first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    lines = []
    lines.append(f"{project.title}")
    if project.author:
        lines.append(f"原著：{project.author}")
    lines.append("=" * 50)
    lines.append("")

    for chapter in sorted(project.chapters, key=lambda c: c.chapter_num):
        lines.append(f"【第{chapter.chapter_num}章】{chapter.title or ''}")
        lines.append("-" * 40)
        lines.append(chapter.script_text or "（待改编...）")
        lines.append("")
        lines.append("")

    content = "\n".join(lines)
    safe_title = project.title.replace(" ", "_").replace("/", "_")[:50]

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={safe_title}_剧本.txt"},
    )


@router.get("/projects/{project_id}/export/docx")
async def export_docx(project_id: str, db: AsyncSession = Depends(get_db)):
    """Export the full script as a Word (.docx) file."""
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.chapters))
    )
    project = result.scalars().unique().first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    doc = Document()

    # Title
    title_para = doc.add_heading(project.title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Metadata
    if project.author:
        meta = doc.add_paragraph(f"原著作者：{project.author}")
        meta.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph("")  # spacer

    for chapter in sorted(project.chapters, key=lambda c: c.chapter_num):
        doc.add_heading(f"第{chapter.chapter_num}章  {chapter.title or ''}", level=1)

        if chapter.script_text:
            for line in chapter.script_text.split("\n"):
                doc.add_paragraph(line)
        else:
            doc.add_paragraph("（待改编...）")

        doc.add_page_break()

    # Save to buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    safe_title = project.title.replace(" ", "_").replace("/", "_")[:50]

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename={safe_title}_剧本.docx"
        },
    )
