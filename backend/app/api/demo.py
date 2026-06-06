"""Demo API — load sample novel from backend/data/samples/."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import Project, Chapter, ProjectStatus
from app.services.text_parser import parse_novel_text

router = APIRouter()

# Limit chapters returned in response to avoid huge payloads
MAX_RESPONSE_CHAPTERS = 100


@router.post("/demo")
async def load_demo(
    force: bool = Query(False, description="Force re-parse even if demo project exists"),
    db: AsyncSession = Depends(get_db),
):
    """Load a sample novel from the samples directory and create a project.

    If a demo project already exists, returns it immediately unless ?force=true.
    """
    # Look for sample files to determine the sample filename
    sample_dir = settings.SAMPLE_DIR
    sample_files = sorted(sample_dir.glob("*.txt")) if sample_dir.exists() else []
    sample_filename = sample_files[0].name if sample_files else None

    # Return existing demo project if available (unless forced)
    if not force and sample_filename:
        existing = await db.execute(
            select(Project).where(
                Project.original_filename == sample_filename,
                Project.status == ProjectStatus.PARSED,
            ).limit(1)
        )
        existing_project = existing.scalar_one_or_none()
        if existing_project:
            # Load chapter summaries
            chapters_result = await db.execute(
                select(Chapter)
                .where(Chapter.project_id == existing_project.id)
                .order_by(Chapter.chapter_num)
                .limit(MAX_RESPONSE_CHAPTERS)
            )
            chapters = chapters_result.scalars().all()
            return {
                "project_id": existing_project.id,
                "title": existing_project.title,
                "author": existing_project.author,
                "total_chapters": existing_project.total_chapters,
                "chapters": [
                    {"id": None, "chapter_num": ch.chapter_num, "title": ch.title or ""}
                    for ch in chapters
                ],
            }

    # Validate sample file availability
    if not sample_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"示例目录不存在：{sample_dir}",
        )

    if not sample_files:
        raise HTTPException(
            status_code=404,
            detail=f"示例目录中没有找到 .txt 文件：{sample_dir}",
        )

    sample_path = sample_files[0]

    # Read and decode
    try:
        raw = sample_path.read_bytes()
    except Exception:
        raise HTTPException(status_code=500, detail="无法读取示例文件")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gbk")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="无法识别文件编码，请使用 UTF-8 或 GBK 编码")

    # Parse chapters
    title, author, chapters = parse_novel_text(text)

    # Create project
    project = Project(
        title=title or sample_path.stem,
        author=author or "未知",
        original_filename=sample_path.name,
        file_path=str(sample_path),
        status=ProjectStatus.PARSED,
        total_chapters=len(chapters),
    )
    db.add(project)
    await db.flush()

    # Create chapter records
    for i, ch in enumerate(chapters, start=1):
        chapter = Chapter(
            project_id=project.id,
            chapter_num=i,
            title=ch.get("title", f"第{i}章"),
            original_text=ch.get("content", ""),
        )
        db.add(chapter)

    project.total_chapters = len(chapters)
    await db.commit()
    await db.refresh(project)

    return {
        "project_id": project.id,
        "title": project.title,
        "author": project.author,
        "total_chapters": project.total_chapters,
        "chapters": [
            {"id": None, "chapter_num": i + 1, "title": ch.get("title", "")}
            for i, ch in enumerate(chapters[:MAX_RESPONSE_CHAPTERS])
        ],
    }
