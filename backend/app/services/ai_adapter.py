"""
AI Adapter — core engine for novel-to-script adaptation.

Uses Claude API (or other LLMs) to transform novel prose into formatted scripts.
"""

from __future__ import annotations

import json
import re
from typing import TypedDict

from app.core.config import settings


class SceneInfo(TypedDict):
    scene_num: int
    time: str
    location: str
    characters: list[str]
    stage_direction: str
    dialogues: list[dict]  # [{"character": "XX", "line": "..."}]


# ── Prompt Templates ──────────────────────────────────────────

SYSTEM_PROMPT_FILM = """你是一位资深的影视编剧，擅长将小说改编为剧本格式。

## 改编规则：
1. **保留原著核心情节**：不要删减重要情节和人物对话
2. **叙述转舞台指示**：将环境描写、动作描写、心理描写转换为【舞台指示】（用【】标注）
3. **对白精炼**：保留人物原话，可适当精炼但不改变原意，语气、个性要保留
4. **场景拆分**：每次场景切换（时间/地点变化）都拆分为新的一场
5. **格式要求**：严格按照以下格式输出

## 输出格式：

第 [场景序号] 场
时间：[时间]
地点：[地点]
人物：[用顿号分隔的人物列表]
【舞台指示：环境、动作、心理描写等】
角色A：（对白内容）
角色B：（对白内容）

---

请将以下小说片段改编为剧本。"""


SYSTEM_PROMPT_COMIC = """你是一位专业的漫画分镜师和编剧，擅长将小说改编为漫画分镜剧本。

## 改编规则：
1. **视觉化呈现**：将所有叙述转换为可视化的画面描述
2. **分格设计**：为每个重要画面标注分格
3. **对话气泡**：对白改为适合漫画的简短对话
4. **画面说明**：用[画面]标注场景视觉描述
5. **节奏感**：控制每页的信息量，保持阅读节奏

## 输出格式：

第 [场景序号] 场 - [地点]
[画面：全景/中景/特写，描述画面内容]
角色A：对话内容
[画面：动作/表情描述]
角色B：对话内容
---

请将以下小说片段改编为漫画分镜剧本。"""


SYSTEM_PROMPT_STAGE = """你是一位舞台剧编剧，擅长将小说改编为舞台剧剧本。

## 改编规则：
1. **舞台空间**：考虑舞台空间限制，合理设计场景
2. **戏剧冲突**：强化戏剧张力和人物冲突
3. **台词节奏**：台词要有舞台感和韵律感
4. **动作指示**：用[左]和[右]标注演员走位

## 输出格式：

第一幕 第[场景序号]场
场景：[地点描述]
出场人物：[人物列表]

角色A：（台词）
[动作指示]
角色B：（台词）

---

请将以下小说片段改编为舞台剧剧本。"""


STYLE_PROMPTS = {
    "film": SYSTEM_PROMPT_FILM,
    "comic": SYSTEM_PROMPT_COMIC,
    "stage": SYSTEM_PROMPT_STAGE,
}

# ── Alignment Instruction ──────────────────────────────────────

ALIGNMENT_INSTRUCTION = """
## 原著段落对应

原著的每个自然段前面都标注了 `[¶数字]` 格式的编号（如 `[¶0]`、`[¶1]`），表示段落编号。

剧本输出完成后，**另起一行**，按以下格式输出改编对应关系：

¶ALIGN¶
S1:0-3
S2:4-7
S3:8-15
¶ENDALIGN¶

格式说明：
- `S{场次}` 是你输出的剧本场次编号（第1场对应S1、第2场对应S2...）
- `:{起始段落}-{结束段落}` 表示该场改编自原著哪些段落
- 段落编号与原文中的 `[¶数字]` 完全对应
- 每个场次单独一行，必须按照 `S{场次}:{起始}-{结束}` 格式
- 确保覆盖所有已改编的原著段落，段落范围不要遗漏
"""


def _make_system_prompt_with_alignment(style: str) -> str:
    """Return the system prompt for a style with alignment instruction appended."""
    base = STYLE_PROMPTS.get(style, SYSTEM_PROMPT_FILM)
    return base + ALIGNMENT_INSTRUCTION


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


# ── Structured Script (Prose → YAML) Prompt ───────────────────

STRUCTURED_SCRIPT_PROMPT = """你是一位专业的剧本格式转换专家，负责将散文格式的剧本转换为结构化的 JSON 数据。

## 任务
将下面散文格式的剧本转换为结构化的 JSON 数组。每个场景是一个对象。

## 散文格式说明
散文剧本的格式为：
- `第 N 场` 标记场景开始
- `时间：...` / `地点：...` / `人物：...` 为场景元数据
- `【...】` 为舞台指示
- `角色名：（对白内容）` 为对白，角色名后括号内为演员指示

## 输出格式
请以 JSON 数组返回，每个元素代表一个场景：

```json
[
  {
    "scene_num": 1,
    "time": "黄昏",
    "location": "城主府大厅",
    "characters": ["张三", "李四"],
    "stage_directions": ["大厅内烛火摇曳，窗外雨声淅沥"],
    "dialogues": [
      {"character": "张三", "line": "你来了。", "parenthetical": "冷冷地"},
      {"character": "李四", "line": "我一直在等你。", "parenthetical": null}
    ]
  }
]
```

## 规则
1. 从 `第 N 场` 提取 scene_num（整数）
2. 从 `时间：` / `地点：` / `人物：` 行提取元数据（去掉标签前缀，只保留值）
3. 从 `【...】` 提取舞台指示（去掉【】符号）
4. 从 `角色名：（对白）` 提取对白；如果角色名后有（），提取为 parenthetical（去掉括号）
5. 只返回 JSON，不要其他内容
6. 确保每个场景的字段完整，缺失的字段用 null 或空数组填充
7. 人物列表中的名字用顿号分隔的，拆分为数组"""

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

        # Build user message
        user_lines = []
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

        # Parse JSON from result
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
        )

        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            extra_body={"thinking": {"type": "disabled"}},
        )

        return self._parse_character_json(response.choices[0].message.content or "")

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

        user_lines = []
        if character_context:
            user_lines.append(f"## 已知人物信息\n{character_context}\n")
        if previous_scene_context:
            user_lines.append(f"## 上一场结尾\n{previous_scene_context}\n")
        user_lines.append(f"## 需要改编的小说片段\n\n{chapter_text}")
        user_message = "\n".join(user_lines)

        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
        )

        response = client.chat.completions.create(
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

    def adapt_chapter_sync_with_alignment(
        self,
        chapter_text: str,
        style: str = "film",
        character_context: str | None = None,
        previous_scene_context: str | None = None,
    ) -> tuple[str, list[dict]]:
        """
        Synchronous adaptation with alignment data extraction.

        Uses the alignment-enhanced system prompt and parses the
        alignment footer from the LLM response.

        Returns:
            (cleaned_script_text, alignment_list)
            alignment_list: [{"scene": 1, "para_start": 0, "para_end": 3}, ...]
        """
        from openai import OpenAI

        from app.services.text_utils import parse_alignment_footer

        system_prompt = _make_system_prompt_with_alignment(style)

        user_lines = []
        if character_context:
            user_lines.append(f"## 已知人物信息\n{character_context}\n")
        if previous_scene_context:
            user_lines.append(f"## 上一场结尾\n{previous_scene_context}\n")
        user_lines.append(f"## 需要改编的小说片段\n\n{chapter_text}")
        user_message = "\n".join(user_lines)

        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
        )

        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            extra_body={"thinking": {"type": "disabled"}},
        )

        raw = response.choices[0].message.content or ""
        return parse_alignment_footer(raw)

    def adapt_prose_to_structured_sync(self, script_text: str) -> list[dict]:
        """
        Second-pass AI conversion: prose script text → structured scene dicts.

        Uses DeepSeek (via OpenAI-compatible API) to parse the prose-format
        script into a JSON array of structured scene objects.

        Args:
            script_text: The prose-format script from the first AI pass.

        Returns:
            List of structured scene dicts, each with:
            scene_num, time, location, characters, stage_directions, dialogues.
            Returns empty list on failure.
        """
        from openai import OpenAI

        user_message = (
            f"## 散文格式剧本\n\n{script_text}\n\n"
            "请将以上散文格式剧本转换为结构化 JSON 数组。只返回 JSON，不要其他内容。"
        )

        try:
            client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1",
            )

            response = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=0.1,  # Low temperature for consistent structured output
                messages=[
                    {"role": "system", "content": STRUCTURED_SCRIPT_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                extra_body={"thinking": {"type": "disabled"}},
            )

            result = response.choices[0].message.content or "[]"
            return self._parse_structured_json(result)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Structured script conversion failed"
            )
            return []

    @staticmethod
    def _parse_structured_json(text: str) -> list[dict]:
        """Parse structured scene JSON from LLM response."""
        # Try direct JSON parse first
        text = text.strip()
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Extract from code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        # Find outermost JSON array
        try:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                data = json.loads(text[start:end + 1])
                if isinstance(data, list):
                    return data
        except json.JSONDecodeError:
            pass

        return []

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _parse_character_json(text: str) -> list[dict]:
        """Parse JSON from LLM response, handling code-block wrapping."""
        # Find JSON block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            text = json_match.group(1).strip()
        try:
            data = json.loads(text)
            return data.get("characters", [])
        except json.JSONDecodeError:
            # Try to find a JSON-like structure
            try:
                # Find outermost JSON object
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
