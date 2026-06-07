"""
AI Adapter — core engine for novel-to-script adaptation.

Uses Claude API (or other LLMs) to transform novel prose into structured
scene JSON, then renders display-format prose text from that JSON.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TypedDict

from app.core.config import settings

logger = logging.getLogger(__name__)


class SceneInfo(TypedDict):
    scene_num: int
    time: str
    location: str
    characters: list[str]
    stage_direction: str
    dialogues: list[dict]  # [{"character": "XX", "line": "..."}]


# ── Prompt Templates (JSON output) ─────────────────────────────

# Shared alignment instructions embedded in each style prompt.
_ALIGNMENT_JSON_INSTRUCTION = """
## 原著段落对应（alignment）
原著每个自然段前标注了 `[¶数字]`（如 `[¶0]`、`[¶1]`）。
在输出 JSON 的 `alignment` 数组中，为每个场景标注其改编自的段落范围：
- `scene`：场景编号（与 scenes[].scene_num 一致）
- `para_start`：起始段落编号
- `para_end`：结束段落编号（包含）
确保段落到场景的映射覆盖所有已改编的原著段落，不遗漏。"""

_ELEMENTS_INSTRUCTION = """
## 使用 elements 数组按原文顺序组织内容
每个场景使用一个 `elements` 数组，按原著故事发展的时间顺序排列内容。
数组中的元素为以下两种类型：
- `{"type": "stage_direction", "text": "……"}` — 环境描写、动作描写、心理描写
- `{"type": "dialogue", "character": "……", "line": "……", "parenthetical": null}` — 对白

请按原文中描写和对话的实际出现顺序来排列 elements，让 stage_direction 和 dialogue 自然穿插：
```json
"elements": [
  {"type": "stage_direction", "text": "大厅内烛火摇曳，窗外雨声淅沥"},
  {"type": "dialogue", "character": "张三", "line": "你来了。", "parenthetical": "冷冷地"},
  {"type": "stage_direction", "text": "张三冷笑一声，端起酒杯一饮而尽"},
  {"type": "dialogue", "character": "李四", "line": "我一直在等你。", "parenthetical": null},
  {"type": "dialogue", "character": "张三", "line": "我知道。", "parenthetical": null},
  {"type": "stage_direction", "text": "李四站起身，走到窗前，沉默良久"}
]
```"""

SYSTEM_PROMPT_FILM = """你是一位资深的影视编剧，擅长将小说改编为剧本格式。

## 改编规则：
1. **保留原著核心情节**：不要删减重要情节和人物对话
2. **叙述转舞台指示**：将环境描写、动作描写、心理描写转换为舞台指示
3. **对白精炼**：保留人物原话，可适当精炼但不改变原意，语气、个性要保留
4. **场景拆分**：每次场景切换（时间/地点变化）都拆分为新的一场
5. **JSON 输出**：严格按照以下 JSON 格式输出
""" + _ELEMENTS_INSTRUCTION + """

## 输出格式（JSON）：
返回一个 JSON 对象，包含 `scenes` 和 `alignment` 两个字段：

```json
{
  "scenes": [
    {
      "scene_num": 1,
      "time": "黄昏",
      "location": "城主府大厅",
      "characters": ["张三", "李四"],
      "elements": [
        {"type": "stage_direction", "text": "大厅内烛火摇曳，窗外雨声淅沥"},
        {"type": "dialogue", "character": "张三", "line": "你来了。", "parenthetical": "冷冷地"},
        {"type": "stage_direction", "text": "张三冷笑一声，端起酒杯一饮而尽"},
        {"type": "dialogue", "character": "李四", "line": "我一直在等你。", "parenthetical": null},
        {"type": "dialogue", "character": "张三", "line": "我知道。", "parenthetical": null},
        {"type": "stage_direction", "text": "李四站起身，走到窗前，沉默良久"}
      ]
    }
  ],
  "alignment": [
    {"scene": 1, "para_start": 0, "para_end": 6}
  ]
}
```

## 字段说明
- `scene_num`：整数，场景序号，从 1 开始递增
- `time`：时间描述（如"黄昏"、"深夜"），未知填 null
- `location`：地点描述，未知填 null
- `characters`：出场人物姓名数组（顿号分隔的拆分为数组元素）
- `elements`：按原文时间顺序排列的内容数组，每个元素为 stage_direction 或 dialogue
  - stage_direction：`{"type": "stage_direction", "text": "舞台指示文本"}`
  - dialogue：`{"type": "dialogue", "character": "角色名", "line": "对白内容", "parenthetical": null}`（parenthetical 为括号内表演指示，无可为 null）
""" + _ALIGNMENT_JSON_INSTRUCTION + """

只返回 JSON，不要其他内容。"""

SYSTEM_PROMPT_COMIC = """你是一位专业的漫画分镜师和编剧，擅长将小说改编为漫画分镜剧本。

## 改编规则：
1. **视觉化呈现**：将所有叙述转换为可视化的画面描述
2. **分格设计**：为每个重要画面标注分格
3. **对话气泡**：对白改为适合漫画的简短对话
4. **画面说明**：用画面描述标注场景视觉内容
5. **节奏感**：控制每页的信息量，保持阅读节奏
6. **JSON 输出**：严格按照以下 JSON 格式输出
""" + _ELEMENTS_INSTRUCTION + """

## 输出格式（JSON）：
返回一个 JSON 对象，包含 `scenes` 和 `alignment` 两个字段：

```json
{
  "scenes": [
    {
      "scene_num": 1,
      "time": null,
      "location": "城主府大厅",
      "characters": ["张三", "李四"],
      "elements": [
        {"type": "stage_direction", "text": "全景：大厅内烛火摇曳"},
        {"type": "dialogue", "character": "张三", "line": "你来了。", "parenthetical": "冷冷地"},
        {"type": "stage_direction", "text": "特写：张三紧握的拳头"},
        {"type": "dialogue", "character": "李四", "line": "我一直在等你。", "parenthetical": null}
      ]
    }
  ],
  "alignment": [
    {"scene": 1, "para_start": 0, "para_end": 3}
  ]
}
```

## 字段说明
- `elements`：按原文时间顺序排列的内容数组
  - stage_direction：`{"type": "stage_direction", "text": "[景别]：画面描述"}`
  - dialogue：`{"type": "dialogue", "character": "角色名", "line": "对白", "parenthetical": null}`""" + _ALIGNMENT_JSON_INSTRUCTION + """

只返回 JSON，不要其他内容。"""

SYSTEM_PROMPT_STAGE = """你是一位舞台剧编剧，擅长将小说改编为舞台剧剧本。

## 改编规则：
1. **舞台空间**：考虑舞台空间限制，合理设计场景
2. **戏剧冲突**：强化戏剧张力和人物冲突
3. **台词节奏**：台词要有舞台感和韵律感
4. **动作指示**：标注演员走位和动作
5. **JSON 输出**：严格按照以下 JSON 格式输出
""" + _ELEMENTS_INSTRUCTION + """

## 输出格式（JSON）：
返回一个 JSON 对象，包含 `scenes` 和 `alignment` 两个字段：

```json
{
  "scenes": [
    {
      "scene_num": 1,
      "time": null,
      "location": "城主府大厅",
      "characters": ["张三", "李四"],
      "elements": [
        {"type": "stage_direction", "text": "张三从左门入，缓步走向舞台中央"},
        {"type": "dialogue", "character": "张三", "line": "你来了。", "parenthetical": "低沉地"},
        {"type": "stage_direction", "text": "李四从右侧暗处现身"},
        {"type": "dialogue", "character": "李四", "line": "我一直在等你。", "parenthetical": null}
      ]
    }
  ],
  "alignment": [
    {"scene": 1, "para_start": 0, "para_end": 3}
  ]
}
```

## 字段说明
- `elements`：按原文时间顺序排列的内容数组
  - stage_direction：`{"type": "stage_direction", "text": "走位/动作描述"}`
  - dialogue：`{"type": "dialogue", "character": "角色名", "line": "台词", "parenthetical": null}`""" + _ALIGNMENT_JSON_INSTRUCTION + """

只返回 JSON，不要其他内容。"""

STYLE_PROMPTS = {
    "film": SYSTEM_PROMPT_FILM,
    "comic": SYSTEM_PROMPT_COMIC,
    "stage": SYSTEM_PROMPT_STAGE,
}


# ── Character Extraction Prompt ────────────────────────────────

CHARACTER_EXTRACTION_PROMPT = """请从以下小说片段中提取所有出场人物信息。

请以 JSON 格式返回：
```json
{
  "characters": [
    {
      "name": "人物姓名",
      "aliases": ["别名1", "别名2"],
      "description": "角色描述",
      "traits": ["性格特征1", "性格特征2"],
      "role": "主角/配角/反派/路人"
    }
  ]
}
```

只返回 JSON，不要其他内容。"""


# ── Prose Renderer ─────────────────────────────────────────────

def structured_scenes_to_prose(scenes: list[dict], style: str = "film") -> str:
    """
    Convert structured scene dicts back to prose-format script text
    for frontend display and legacy exports.

    Args:
        scenes: List of scene dicts with scene_num, time, location,
                characters, stage_directions, dialogues.
        style: "film" | "comic" | "stage"

    Returns:
        Prose-format script text matching the original display format.
    """
    if not scenes:
        return ""

    parts: list[str] = []
    for scene in scenes:
        lines: list[str] = []
        sn = scene.get("scene_num", 0)
        time_val = scene.get("time") or ""
        location = scene.get("location") or ""
        characters = scene.get("characters") or []
        elements = scene.get("elements") or []

        def _render_direction(text: str) -> str:
            if style == "film":
                return f"【{text}】"
            elif style == "comic":
                return f"[画面：{text}]"
            else:
                return f"[{text}]"

        if style == "film":
            lines.append(f"第 {sn} 场")
            if time_val:
                lines.append(f"时间：{time_val}")
            if location:
                lines.append(f"地点：{location}")
            if characters:
                lines.append(f"人物：{'、'.join(characters)}")

        elif style == "comic":
            loc_str = f" - {location}" if location else ""
            lines.append(f"第 {sn} 场{loc_str}")

        elif style == "stage":
            lines.append(f"第一幕 第{sn}场")
            if location:
                lines.append(f"场景：{location}")
            if characters:
                lines.append(f"出场人物：{'、'.join(characters)}")

        # Render elements in order — they're already interleaved by the AI
        for elem in elements:
            etype = elem.get("type", "")
            if etype == "stage_direction":
                lines.append(_render_direction(elem.get("text", "")))
            elif etype == "dialogue":
                char = elem.get("character", "")
                line = elem.get("line", "")
                paren = elem.get("parenthetical")
                if style == "film":
                    if paren:
                        lines.append(f"{char}：（{paren}）{line}")
                    else:
                        lines.append(f"{char}：{line}")
                elif style == "comic":
                    lines.append(f"{char}：{line}")
                elif style == "stage":
                    if paren:
                        lines.append(f"{char}：（{paren}）{line}")
                    else:
                        lines.append(f"{char}：（{line}）")

        parts.append("\n".join(lines))

    return "\n\n---\n\n".join(parts)


# ── AI Client Interface ────────────────────────────────────────

class AIAdapter:
    """
    Abstraction over LLM providers.
    Currently supports Anthropic Claude, with extension points for
    OpenAI GPT-4 and Qwen.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER

    async def adapt_chapter(
        self,
        chapter_text: str,
        style: str = "film",
        character_context: str | None = None,
        previous_scene_context: str | None = None,
    ) -> str:
        """
        Adapt a single chapter of novel into script format.

        Args:
            chapter_text: Raw novel chapter text.
            style: One of "film", "comic", "stage".
            character_context: Pre-extracted character info to maintain consistency.
            previous_scene_context: Last scene of previous chapter for continuity.

        Returns:
            Formatted script text.
        """
        system_prompt = STYLE_PROMPTS.get(style, SYSTEM_PROMPT_FILM)

        user_lines = [
            "## 提示：请按原文顺序自然穿插 stage_direction 和 dialogue，避免全部描写堆在一起、全部对白堆在一起。\n",
        ]
        if character_context:
            user_lines.append(f"## 已知人物信息\n{character_context}\n")
        if previous_scene_context:
            user_lines.append(f"## 上一场结尾\n{previous_scene_context}\n")
        user_lines.append(f"## 需要改编的小说片段\n\n{chapter_text}")

        user_message = "\n".join(user_lines)

        if self.provider == "anthropic":
            return await self._call_anthropic(system_prompt, user_message)
        elif self.provider == "openai":
            return await self._call_openai(system_prompt, user_message)
        elif self.provider == "qwen":
            return await self._call_qwen(system_prompt, user_message)
        elif self.provider == "deepseek":
            return await self._call_deepseek(system_prompt, user_message)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def extract_characters(self, chapter_text: str) -> list[dict]:
        """Extract character information from a chapter."""
        user_message = (
            f"## 小说片段\n\n{chapter_text}\n\n" + CHARACTER_EXTRACTION_PROMPT
        )
        system_prompt = "你是一个专业的文学分析师，擅长从小说中提取人物信息。请严格按 JSON 格式返回。"

        if self.provider == "anthropic":
            result = await self._call_anthropic(system_prompt, user_message)
        elif self.provider == "openai":
            result = await self._call_openai(system_prompt, user_message)
        elif self.provider == "qwen":
            result = await self._call_qwen(system_prompt, user_message)
        elif self.provider == "deepseek":
            result = await self._call_deepseek(system_prompt, user_message)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        return self._parse_character_json(result)

    def extract_characters_sync(self, chapter_text: str) -> list[dict]:
        """Synchronous version of extract_characters for use in thread pools."""
        from openai import OpenAI

        user_message = (
            f"## 小说片段\n\n{chapter_text}\n\n" + CHARACTER_EXTRACTION_PROMPT
        )
        system_prompt = "你是一个专业的文学分析师，擅长从小说中提取人物信息。请严格按 JSON 格式返回。"

        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
            timeout=120.0,
        )

        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            timeout=120.0,
            extra_body={"thinking": {"type": "disabled"}},
        )

        return self._parse_character_json(response.choices[0].message.content or "")

    def extract_characters_for_project(
        self, chapters: list[dict]
    ) -> list[dict]:
        """
        Extract characters from a project using the 5-chapter sliding window
        rule (same as the original adaptation flow). For each chapter N, use
        chapters [N-2, N+2] as the context window, then deduplicate across
        all windows.

        Args:
            chapters: List of {"chapter_num": int, "text": str} sorted by chapter_num.

        Returns:
            List of deduplicated character dicts.
        """
        if not chapters:
            return []

        total = len(chapters)
        all_characters: list[dict] = []

        for i, ch in enumerate(chapters):
            chapter_num = ch["chapter_num"]
            # Sliding window: max(1, N-2) to min(total, N+2)
            win_start = max(1, chapter_num - 2)
            win_end = min(
                max(c["chapter_num"] for c in chapters), chapter_num + 2
            )
            window_texts = [
                c["text"] for c in chapters
                if win_start <= c["chapter_num"] <= win_end and c["text"]
            ]
            window_text = "\n\n".join(window_texts)
            if not window_text.strip():
                continue

            try:
                chars = self.extract_characters_sync(window_text)
                all_characters.extend(chars)
            except Exception:
                logger.exception(
                    "Character extraction failed for chapter %d (window %d-%d)",
                    chapter_num, win_start, win_end,
                )
                continue

        # Deduplicate by name
        return self._deduplicate_characters(all_characters)

    @staticmethod
    def _deduplicate_characters(characters: list[dict]) -> list[dict]:
        """
        Merge characters by name. For the same name:
        - traits: union
        - aliases: union
        - description: keep the longest
        - role: keep the first non-empty
        """
        merged: dict[str, dict] = {}
        for c in characters:
            name = c.get("name", "").strip()
            if not name:
                continue
            if name not in merged:
                merged[name] = {
                    "name": name,
                    "aliases": list(set(c.get("aliases") or [])),
                    "description": c.get("description") or "",
                    "traits": list(set(c.get("traits") or [])),
                    "role": c.get("role") or "",
                }
            else:
                existing = merged[name]
                # Union aliases
                existing["aliases"] = list(set(existing["aliases"]) | set(c.get("aliases") or []))
                # Union traits
                existing["traits"] = list(set(existing["traits"]) | set(c.get("traits") or []))
                # Keep longest description
                new_desc = c.get("description") or ""
                if len(new_desc) > len(existing["description"]):
                    existing["description"] = new_desc
                # Keep first non-empty role
                if not existing["role"] and c.get("role"):
                    existing["role"] = c.get("role", "")

        return list(merged.values())

    # ── Provider Implementations ───────────────────────────────

    async def _call_anthropic(self, system_prompt: str, user_message: str) -> str:
        """Call Anthropic Claude API."""
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = await client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        return response.content[0].text

    async def _call_openai(self, system_prompt: str, user_message: str) -> str:
        """Call OpenAI GPT API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        return response.choices[0].message.content or ""

    async def _call_qwen(self, system_prompt: str, user_message: str) -> str:
        """Call Qwen (Tongyi Qianwen) API."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.QWEN_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen-plus",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "temperature": settings.LLM_TEMPERATURE,
                },
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _call_deepseek(self, system_prompt: str, user_message: str) -> str:
        """Call DeepSeek API (OpenAI-compatible)."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
        )

        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            extra_body={"thinking": {"type": "disabled"}},
        )

        return response.choices[0].message.content or ""

    # ── Sync methods (for background threads) ────────────────────

    def adapt_chapter_sync(
        self,
        chapter_text: str,
        style: str = "film",
        character_context: str | None = None,
        previous_scene_context: str | None = None,
    ) -> str:
        """Synchronous version of adapt_chapter for use in thread pools."""
        from openai import OpenAI

        system_prompt = STYLE_PROMPTS.get(style, SYSTEM_PROMPT_FILM)

        user_lines = [
            "## 提示：请按原文顺序自然穿插 stage_direction 和 dialogue，避免全部描写堆在一起、全部对白堆在一起。\n",
        ]
        if character_context:
            user_lines.append(f"## 已知人物信息\n{character_context}\n")
        if previous_scene_context:
            user_lines.append(f"## 上一场结尾\n{previous_scene_context}\n")
        user_lines.append(f"## 需要改编的小说片段\n\n{chapter_text}")
        user_message = "\n".join(user_lines)

        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
            timeout=300.0,
        )

        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            timeout=300.0,
            extra_body={"thinking": {"type": "disabled"}},
        )

        return response.choices[0].message.content or ""

    def adapt_chapter_sync_with_alignment(
        self,
        chapter_text: str,
        style: str = "film",
        character_context: str | None = None,
        previous_scene_context: str | None = None,
    ) -> tuple[str, list[dict], list[dict]]:
        """
        Synchronous adaptation: novel text → structured JSON → prose text.

        The AI prompt now instructs the LLM to output JSON with `scenes` and
        `alignment` fields directly. The structured scenes are then rendered
        to prose-format text for frontend display.

        Args:
            chapter_text: Raw novel chapter text with [¶N] paragraph markers.
            style: One of "film", "comic", "stage".
            character_context: Pre-extracted character info for consistency.
            previous_scene_context: Previous chapter's last scene for continuity.

        Returns:
            (prose_text, structured_scenes, alignment_list)
            - prose_text: Prose-format script for frontend display
            - structured_scenes: List of structured scene dicts
            - alignment_list: [{"scene": 1, "para_start": 0, "para_end": 3}, ...]
        """
        from openai import OpenAI

        system_prompt = STYLE_PROMPTS.get(style, SYSTEM_PROMPT_FILM)

        user_lines = [
            "## 提示：请按原文顺序自然穿插 stage_direction 和 dialogue，避免全部描写堆在一起、全部对白堆在一起。\n",
        ]
        if character_context:
            user_lines.append(f"## 已知人物信息\n{character_context}\n")
        if previous_scene_context:
            user_lines.append(f"## 上一场结尾\n{previous_scene_context}\n")
        user_lines.append(f"## 需要改编的小说片段\n\n{chapter_text}")
        user_message = "\n".join(user_lines)

        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
            timeout=300.0,
        )

        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            timeout=300.0,
            extra_body={"thinking": {"type": "disabled"}},
        )

        raw = response.choices[0].message.content or ""

        # Parse the JSON response
        parsed = self._parse_adaptation_json(raw)
        structured_scenes: list[dict] = parsed.get("scenes", [])
        alignment: list[dict] = parsed.get("alignment", [])

        # Normalize to elements format (v4 schema)
        for scene in structured_scenes:
            if "elements" in scene and isinstance(scene["elements"], list):
                continue  # Already in new format
            # Convert old format: stage_directions + dialogues → elements
            elements: list[dict] = []
            raw_dirs = scene.pop("stage_directions", []) or []
            raw_dialogues = scene.pop("dialogues", []) or []

            # Build position→directions map for old {text, position} format
            from collections import defaultdict
            dirs_by_pos: dict[int, list[str]] = defaultdict(list)
            for item in raw_dirs:
                if isinstance(item, str):
                    dirs_by_pos[0].append(item)
                elif isinstance(item, dict):
                    pos = item.get("position", 0)
                    dirs_by_pos[pos].append(item.get("text", ""))

            # Interleave: position 0 → dialogue 0 → position 1 → dialogue 1 → ...
            for text in dirs_by_pos.get(0, []):
                elements.append({"type": "stage_direction", "text": text})
            for i, d in enumerate(raw_dialogues):
                elements.append({
                    "type": "dialogue",
                    "character": d.get("character", ""),
                    "line": d.get("line", ""),
                    "parenthetical": d.get("parenthetical"),
                })
                for text in dirs_by_pos.get(i + 1, []):
                    elements.append({"type": "stage_direction", "text": text})

            scene["elements"] = elements

        # Render prose text from structured scenes
        prose_text = structured_scenes_to_prose(structured_scenes, style)

        return prose_text, structured_scenes, alignment

    # ── JSON Parsing ──────────────────────────────────────────

    @staticmethod
    def _parse_adaptation_json(text: str) -> dict:
        """
        Parse the LLM's JSON response containing `scenes` and `alignment`.

        Handles common LLM output quirks: markdown code fences,
        leading/trailing text, etc.
        """
        text = text.strip()

        # Try direct parse
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "scenes" in data:
                return data
        except json.JSONDecodeError:
            pass

        # Extract from code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
                if isinstance(data, dict) and "scenes" in data:
                    return data
            except json.JSONDecodeError:
                pass

        # Find outermost JSON object
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(text[start:end + 1])
                if isinstance(data, dict) and "scenes" in data:
                    return data
        except json.JSONDecodeError:
            pass

        logger.warning("Failed to parse adaptation JSON, raw preview: %s",
                        text[:200])
        return {"scenes": [], "alignment": []}

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _parse_character_json(text: str) -> list[dict]:
        """Parse JSON from LLM response, handling code-block wrapping."""
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            text = json_match.group(1).strip()
        try:
            data = json.loads(text)
            return data.get("characters", [])
        except json.JSONDecodeError:
            try:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1:
                    data = json.loads(text[start:end + 1])
                    return data.get("characters", [])
            except json.JSONDecodeError:
                pass
            return []


# Singleton
ai_adapter = AIAdapter()
