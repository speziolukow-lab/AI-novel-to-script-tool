"""Database models for the novel-to-script tool."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


class ProjectStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    ADAPTING = "adapting"
    COMPLETED = "completed"
    FAILED = "failed"


class ChapterStatus(str, enum.Enum):
    PENDING = "pending"
    ADAPTING = "adapting"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), default="default")
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus), default=ProjectStatus.UPLOADED
    )
    style: Mapped[str] = mapped_column(String(50), default="film")  # film / comic / stage
    total_chapters: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict | None] = mapped_column(JSON, nullable=True, name="metadata")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter", back_populates="project", cascade="all, delete-orphan"
    )
    characters: Mapped[list["Character"]] = relationship(
        "Character", back_populates="project", cascade="all, delete-orphan"
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"))
    chapter_num: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    characters_in_chapter: Mapped[list | None] = mapped_column(JSON, nullable=True, name="characters")
    status: Mapped[ChapterStatus] = mapped_column(
        SAEnum(ChapterStatus), default=ChapterStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project: Mapped["Project"] = relationship("Project", back_populates="chapters")


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    aliases: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # list of aliases
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    traits: Mapped[dict | None] = mapped_column(JSON, nullable=True)    # list of traits
    relationships: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {name: relation_desc}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="characters")


class Adaptation(Base):
    """Per-style adaptation result for a chapter.

    Each chapter can have independent adaptations for film / comic / stage.
    """

    __tablename__ = "adaptations"
    __table_args__ = (
        UniqueConstraint("chapter_id", "style", name="uq_adaptation_chapter_style"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id: Mapped[str] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"))
    style: Mapped[str] = mapped_column(String(50), default="film")  # film / comic / stage
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ChapterStatus] = mapped_column(
        SAEnum(ChapterStatus), default=ChapterStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    characters_in_chapter: Mapped[list | None] = mapped_column(JSON, nullable=True, name="characters")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="adaptations")


# Add adaptations relationship to Chapter
Chapter.adaptations: Mapped[list["Adaptation"]] = relationship(
    "Adaptation", back_populates="chapter", cascade="all, delete-orphan"
)
