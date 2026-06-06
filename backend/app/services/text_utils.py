"""
Text utilities for AI adaptation pipeline.

- Paragraph numbering for original-to-script alignment
- Alignment footer parsing from LLM output
"""

from __future__ import annotations

import re

# Regex for alignment footer entries: S{scene}:{start}-{end}
_ALIGN_LINE_RE = re.compile(r"S(\d+)\s*:\s*(\d+)\s*-\s*(\d+)")


def number_paragraphs(text: str, start_num: int = 0) -> tuple[str, int]:
    """
    Prefix non-empty lines with [¶N] markers for LLM alignment.

    Args:
        text: Raw chapter text.
        start_num: Starting paragraph number (for chunked text continuity).

    Returns:
        (numbered_text, total_paragraph_count) where total_paragraph_count
        is the number of non-empty lines numbered.
    """
    lines = text.split("\n")
    numbered_lines: list[str] = []
    count = 0

    for line in lines:
        if line.strip():
            numbered_lines.append(f"[¶{start_num + count}] {line}")
            count += 1
        else:
            numbered_lines.append(line)

    return "\n".join(numbered_lines), count


def parse_alignment_footer(response_text: str) -> tuple[str, list[dict]]:
    """
    Parse alignment footer from LLM response.

    Expected format:
        ¶ALIGN¶
        S1:0-3
        S2:4-7
        ¶ENDALIGN¶

    Args:
        response_text: Raw LLM response (may contain alignment footer).

    Returns:
        (cleaned_text, alignment_list) where cleaned_text has the footer
        stripped, and alignment_list is a list of dicts:
        [{"scene": 1, "para_start": 0, "para_end": 3}, ...].
        Returns (response_text, []) if no valid footer found.
    """
    # Find the alignment block
    match = re.search(r"¶ALIGN¶\s*\n(.*?)\n\s*¶ENDALIGN¶", response_text, re.DOTALL)
    if not match:
        return response_text, []

    alignment_block = match.group(1)
    cleaned_text = response_text[:match.start()] + response_text[match.end():]
    # Remove trailing whitespace/newlines left by footer removal
    cleaned_text = cleaned_text.rstrip()

    alignment: list[dict] = []
    for line in alignment_block.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = _ALIGN_LINE_RE.match(line)
        if m:
            alignment.append({
                "scene": int(m.group(1)),
                "para_start": int(m.group(2)),
                "para_end": int(m.group(3)),
            })

    return cleaned_text, alignment
