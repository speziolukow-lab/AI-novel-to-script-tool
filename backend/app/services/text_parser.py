"""Novel text parser — split raw text into structured chapters."""

from __future__ import annotations

import re
from typing import TypedDict


class ChapterInfo(TypedDict):
    title: str
    content: str


# Common chapter title patterns in Chinese novels
CHAPTER_PATTERNS = [
    # 第X章 / 第X节 / Chapter X
    re.compile(r"^[ \t]*(?:第[零一二三四五六七八九十百千\d]+[章节回部集卷])[ 　\t]*[：:]*[ 　\t]*(?P<title>.*)", re.MULTILINE),
    # 第X章 without trailing title
    re.compile(r"^[ 　\t]*(?:第[零一二三四五六七八九十百千\d]+章)[ 　\t]*$", re.MULTILINE),
    # Chapter 1 / CH1
    re.compile(r"^[ 　\t]*(?:Chapter|CH|Ch)\s*\d+[ 　\t]*[：:]*[ 　\t]*(?P<title>.*)", re.MULTILINE | re.IGNORECASE),
    # 序章 / 楔子 / 引子 / 尾声 / 番外
    re.compile(r"^[ 　\t]*(?:序章|楔子|引子|前言|尾声|终章|番外|后记|附录)[ 　\t]*[：:]*[ 　\t]*(?P<title>.*)", re.MULTILINE),
    # === Chapter Title === style
    re.compile(r"^[ 　\t]*[=]{2,}[ 　\t]*([^=]+?)[ 　\t]*[=]{2,}[ 　\t]*$", re.MULTILINE),
]


def _detect_title_line(line: str) -> str | None:
    """Return the chapter title if this line looks like a title, else None."""
    for pattern in CHAPTER_PATTERNS:
        m = pattern.match(line)
        if m:
            return line.strip()
    return None


def _extract_author(text: str) -> str | None:
    """Try to extract author from text metadata."""
    # Common patterns: 作者：XXX / Author: XXX
    for pattern in [
        r"作者[：:]\s*(\S+)",
        r"Author[：:]\s*(\S+)",
        r"著[：:]\s*(\S+)",
        r"原作[：:]\s*(\S+)",
    ]:
        m = re.search(pattern, text[:500], re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_title(text: str) -> str | None:
    """Try to extract title from first few lines."""
    lines = text.strip().split("\n")
    first_line = lines[0].strip() if lines else ""
    # Remove common metadata prefixes
    first_line = re.sub(r"^(?:书名|标题|Title)[：:]\s*", "", first_line)
    if 2 <= len(first_line) <= 100 and not first_line.startswith("第"):
        return first_line
    return None


def parse_novel_text(text: str) -> tuple[str | None, str | None, list[ChapterInfo]]:
    """
    Parse a novel text into structured chapters.

    Returns:
        (title, author, list of ChapterInfo)
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    title = _extract_title(text)
    author = _extract_author(text)

    lines = text.split("\n")
    chapters: list[ChapterInfo] = []
    chapter_boundaries: list[int] = []  # line indices where chapters start

    # Find chapter boundaries
    for i, line in enumerate(lines):
        if _detect_title_line(line):
            chapter_boundaries.append(i)

    if not chapter_boundaries:
        # No chapter markers found — treat entire text as one chapter
        cleaned = text.strip()
        if cleaned:
            chapters.append(ChapterInfo(title="正文", content=cleaned))
        return title, author, chapters

    # Add end boundary
    chapter_boundaries.append(len(lines))

    for idx in range(len(chapter_boundaries) - 1):
        start = chapter_boundaries[idx]
        end = chapter_boundaries[idx + 1]
        chapter_title = lines[start].strip()
        # Strip the chapter marker and get the real title
        chapter_title = re.sub(
            r"^(?:第[零一二三四五六七八九十百千\d]+[章节回部集卷])[ 　\t]*[：:]*[ 　\t]*",
            "",
            chapter_title,
        )
        chapter_title = chapter_title or f"第{idx + 1}章"
        content = "\n".join(lines[start + 1:end]).strip()
        if content:
            chapters.append(ChapterInfo(title=chapter_title, content=content))

    return title, author, chapters


def split_long_chapter(
    content: str, max_length: int = 8000, overlap: int = 200
) -> list[str]:
    """
    Split an overlong chapter into overlapping chunks for LLM processing.
    Tries to break at natural paragraph boundaries.
    """
    if len(content) <= max_length:
        return [content]

    paragraphs = content.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para) + 1  # +1 for newline
        if current_len + para_len > max_length and current:
            chunks.append("\n".join(current))
            # Keep last `overlap` chars for context
            if overlap > 0:
                tail = chunks[-1][-overlap:]
                current = [tail] if tail else []
                current_len = len(tail)
            else:
                current = []
                current_len = 0
        current.append(para)
        current_len += para_len

    if current:
        chunks.append("\n".join(current))

    return chunks
