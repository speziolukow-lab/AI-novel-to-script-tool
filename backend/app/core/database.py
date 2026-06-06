"""Database engine and session management."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models import Base

# Async engine (for FastAPI endpoints)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine (for background tasks — avoids greenlet issues)
_sync_url = settings.DATABASE_URL.replace("+aiosqlite", "")
sync_engine = create_engine(
    _sync_url,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in _sync_url else {},
)

SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session, expire_on_commit=False)


async def init_db():
    """Create all tables and migrate existing data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ── Migrate existing Chapter.script_text → Adaptation(style="film") ──
    import asyncio
    from sqlalchemy import select as sa_select

    from app.models import Chapter, ChapterStatus, Adaptation

    def _migrate():
        with SyncSessionLocal() as db:
            # Check if adaptations column exists by querying
            try:
                chapters = db.execute(
                    sa_select(Chapter).where(Chapter.script_text.isnot(None))
                ).scalars().all()
            except Exception:
                # Table might not exist yet or column mismatch — skip
                return

            migrated = 0
            for ch in chapters:
                existing = db.execute(
                    sa_select(Adaptation).where(
                        Adaptation.chapter_id == ch.id,
                        Adaptation.style == "film",
                    )
                ).scalar_one_or_none()
                if existing:
                    continue  # already migrated

                # Determine status from chapter
                status = ch.status if ch.status else ChapterStatus.COMPLETED
                if isinstance(status, str):
                    try:
                        status = ChapterStatus(status)
                    except ValueError:
                        status = ChapterStatus.COMPLETED

                adaptation = Adaptation(
                    chapter_id=ch.id,
                    style="film",
                    script_text=ch.script_text,
                    status=status,
                    error_message=ch.error_message,
                    scenes=ch.scenes,
                    characters_in_chapter=ch.characters_in_chapter,
                )
                db.add(adaptation)
                migrated += 1

            if migrated:
                db.commit()
                logging.getLogger(__name__).info(
                    "Migrated %d chapter(s) to Adaptation table (style=film)", migrated
                )

    await asyncio.to_thread(_migrate)


async def get_db() -> AsyncSession:
    """Dependency: yield an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
