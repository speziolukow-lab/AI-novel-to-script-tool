"""File upload API — accept novel files."""

from pathlib import Path
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import Project, ProjectStatus
from app.services.text_parser import parse_novel_text

router = APIRouter()

ALLOWED_EXTENSIONS = {".txt", ".epub"}


@router.post("/upload")
async def upload_novel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a novel file (.txt or .epub) and create a project."""
    # Validate extension
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式：{ext}。仅支持 {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Validate size
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大（{size_mb:.1f}MB）。最大支持 {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Save to disk
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    file_path = settings.UPLOAD_DIR / safe_filename
    file_path.write_bytes(contents)

    # Try to decode and parse
    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = contents.decode("gbk")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="无法识别文件编码，请使用 UTF-8 或 GBK 编码")

    # Parse chapters
    title, author, chapters = parse_novel_text(text)

    # Create project in DB
    project = Project(
        title=title or Path(file.filename).stem,
        author=author or "未知",
        original_filename=file.filename,
        file_path=str(file_path),
        status=ProjectStatus.PARSED,
        total_chapters=len(chapters),
    )
    db.add(project)
    await db.flush()  # get project.id

    # Create chapter records
    from app.models import Chapter
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
            for i, ch in enumerate(chapters)
        ],
    }
