# AI 小说转剧本工具 — 项目计划

> **版本**: v0.1.0 (MVP) | **日期**: 2026-06-06 | **状态**: Demo 核心已完成，AI 引擎增强进行中

---

## 一、项目概述

### 1.1 项目背景
传统的小说改编为剧本（影视剧本/漫画剧本）需要编剧投入大量时间和精力进行手工改写。借助大语言模型（LLM）的能力，可以实现从小说文本到剧本格式的智能转换，大幅提升改编效率。

### 1.2 项目目标
构建一个基于 AI 的小说转剧本平台，支持用户上传小说文本，自动完成：
- 小说章节解析与结构化
- AI 驱动逐章改编为剧本格式
- 三种风格独立存储（影视/漫画/舞台）
- 多格式导出（Markdown/TXT/DOCX）

### 1.3 目标用户
- 短剧编剧（抖音/快手/小程序剧）
- 网文作者转型短剧/漫画
- 独立内容创作者
- Demo 体验者

---

## 二、当前状态

### 2.1 Demo 核心已完成 ✅

| 模块 | 功能 | 状态 |
|------|------|------|
| **文本输入** | 小说上传 (.txt/.epub) + 示例小说一键加载 | ✅ 已完成 |
| **章节解析** | 自动分章（6 种正则模式）+ 编码识别（UTF-8/GBK） | ✅ 已完成 |
| **AI 改编** | DeepSeek-V4-Pro（默认）+ Anthropic/OpenAI/Qwen 可切换 | ✅ 已完成 |
| **多风格** | 影视剧本/漫画分镜/舞台剧本，Adaptation 表独立存储 | ✅ 已完成 |
| **质量自检** | 前端 `checkQuality()` 纯函数，问题行高亮 + 点击定位 | ✅ 已完成 |
| **原文对比** | 原文/剧本一键切换对比 | ✅ 已完成 |
| **导出** | Markdown / TXT / DOCX 三格式导出 | ✅ 已完成 |
| **剧本阅读器** | 6 类语法高亮 + 质量高亮 + 原文/剧本双模式 | ✅ 已完成 |

### 2.2 AI 引擎增强（待实现）🔧

| 模块 | 功能 | 优先级 | 工作量 |
|------|------|--------|--------|
| **角色提取** | 上传后自动提取角色档案，改编时注入角色上下文 | P0 | ~1h |
| **摘要链记忆** | 跨章累积摘要，解决长篇连贯性问题 | P0 | ~30min |
| **Prompt 增强** | 反幻觉指令 + 格式约束 + 外貌标注 | P0 | ~1h |

---

## 三、技术架构（实际）

| 层级 | 技术选择 | 说明 |
|------|----------|------|
| **前端** | React 19 + TypeScript + TailwindCSS 4 + Vite 8 | 单页状态机（非路由），Vite Proxy 到后端 |
| **后端** | Python FastAPI + SQLAlchemy 2.0 | 异步 API + 同步后台线程（双引擎） |
| **AI 引擎** | DeepSeek-V4-Pro（默认）+ Anthropic/OpenAI/Qwen | 4 Provider 可切换，成本 ~¥0.002/章 |
| **数据库** | SQLite (aiosqlite + 同步引擎) | 零配置，单文件存储 |
| **异步方案** | `asyncio.create_task()` + `asyncio.to_thread()` | 无需 Celery/Redis |
| **部署** | 单进程 FastAPI + Vite Dev Server | Demo 本地部署 |

---

## 四、AI 处理流水线

```
小说输入 → 文本预处理(编码/分章) → 长章节切分(8000字/块)
                                           ↓
           剧本输出 ← 拼接 ← AI 逐 chunk 改编 (DeepSeek)
              ↓
         质量自检 → Warning 高亮
```

---

## 五、核心数据结构（实际 ORM 模型）

### 5.1 Project（项目）
- `id`, `title`, `author`, `style`(film/comic/stage)
- `status`: UPLOADED → PARSING → PARSED → ADAPTING → COMPLETED/FAILED

### 5.2 Chapter（章节）
- `id`, `project_id`, `chapter_num`, `original_text`
- 遗留字段: `script_text`, `status`, `error_message`（向后兼容）

### 5.3 Adaptation（多风格改编）🆕
- `id`, `chapter_id`, `style`, `script_text`, `status`
- UNIQUE(chapter_id, style) — 每章每种风格独立记录

### 5.4 Character（角色）
- `id`, `project_id`, `name`, `aliases`, `description`, `traits`

---

## 六、下一步行动

1. **P0 — 角色提取接入**：`extract_characters()` 已实现，需接线到上传流水线
2. **P0 — 摘要链记忆**：Chapter 表加 2 字段 + `summarize_chapter()` 方法
3. **P0 — Prompt 增强**：反幻觉指令 + 格式约束 + 外貌标注
4. **P2 — EPUB 解析**：ZIP 解压 + XHTML 文本提取

---

## 七、关联文档

| 文档 | 用途 |
|------|------|
| [product-requirements.md](product-requirements.md) | 产品需求文档 |
| [solution-design.md](solution-design.md) | 方案设计（16 方案卡） |
| [technical-architecture.md](technical-architecture.md) | 技术架构详情 |
| [information-architecture.md](information-architecture.md) | 信息架构设计 |
| [implementation-plan.md](implementation-plan.md) | 实施计划 |
| [competitive-analysis.md](competitive-analysis.md) | 竞品技术分析 |
| [../USAGE.md](../USAGE.md) | 使用文档 |

---

> 📅 创建日期：2026-06-05 | 📝 更新：2026-06-06（同步 Adaptation 表 + 质量高亮 + 实际技术栈）
