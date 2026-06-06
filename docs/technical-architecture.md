# AI 小说转剧本工具 — 技术架构文档

> **版本**: 0.1.0 (MVP) | **日期**: 2026-06-06 | **更新**: 2026-06-06 (同步对齐映射)

---

## 1. 项目概述

**AI 小说转剧本工具** 是一个基于 LLM 的中文小说→结构化剧本智能改编平台。用户上传 .txt/.epub 小说文件，系统自动分章、提取角色，并通过大语言模型将每章叙事文本转换为三种风格的剧本：**影视剧本**、**漫画分镜**、**舞台剧本**。支持 Markdown / TXT / DOCX 三种格式导出。

---

## 2. 技术栈

### 2.1 后端

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 语言 | Python | 3.12+ | 主语言 |
| Web 框架 | FastAPI | 0.115.0 | REST API |
| ASGI 服务器 | uvicorn | 0.30.6 | 开发/生产运行 |
| ORM | SQLAlchemy | 2.0.35 | 异步 + 同步双引擎 |
| 数据库 | SQLite (aiosqlite) | 0.20.0 | 本地持久化 |
| 数据校验 | Pydantic + pydantic-settings | 2.9+ | 配置管理 + 类型校验 |
| LLM SDK | anthropic (Claude) | 0.39.0 | Anthropic API 调用 |
| LLM SDK | openai | 1.30+ | OpenAI / DeepSeek API 调用 |
| HTTP 客户端 | httpx | 0.27.2 | Qwen API 调用 |
| 文档生成 | python-docx | 1.1.2 | .docx 导出 |
| 文件上传 | python-multipart | 0.0.12 | multipart 解析 |

### 2.2 前端

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 语言 | TypeScript | 6.0 | 类型安全 |
| UI 框架 | React | 19.2 | 组件化 UI |
| 构建工具 | Vite | 8.0 | 开发服务器 + 打包 |
| CSS 框架 | Tailwind CSS | 4.3 | 原子化样式 |
| CSS 插件 | @tailwindcss/vite | 4.3 | Vite 集成 |
| React 插件 | @vitejs/plugin-react | 6.0 | JSX 转换 (Oxc) |
| 代码检查 | ESLint | 10.3 | 静态分析 |
| HTTP | 原生 fetch API | — | 无第三方 HTTP 库 |

---

## 3. 系统架构

### 3.1 整体架构图

```
┌──────────────────────────────────────────────────────────────┐
│                      Frontend (React 19)                      │
│                     localhost:5173 (Vite)                     │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ App.tsx  │  │ProjectList│  │UploadNovel│  │ProjectDetail│ │
│  │ (Router) │  │          │  │          │  │             │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘ │
│       │              │              │               │        │
│       └──────────────┴──────────────┴───────────────┘        │
│                           │  fetch(/api/*)                    │
└───────────────────────────┼──────────────────────────────────┘
                            │  Vite Proxy: /api → :8000
┌───────────────────────────┼──────────────────────────────────┐
│                      Backend (FastAPI)                        │
│                     localhost:8000                            │
│                           │                                   │
│  ┌────────────────────────┼──────────────────────────────┐   │
│  │                   main.py                              │   │
│  │  - CORS Middleware                                     │   │
│  │  - Lifespan: init_db() + mkdir                         │   │
│  │  - Router mounting (/api prefix)                       │   │
│  └────────────────────────┼──────────────────────────────┘   │
│                           │                                   │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ upload  │  │ projects  │  │ chapters │  │  export  │     │
│  │ .py     │  │ .py       │  │ .py      │  │ .py      │     │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │              │            │
│  ┌────┴─────────────┴─────────────┴──────────────┴────┐      │
│  │                  Service Layer                       │      │
│  │  ┌──────────────┐  ┌──────────────────┐             │      │
│  │  │ text_parser  │  │   ai_adapter     │             │      │
│  │  │ - 章节识别    │  │ - 多模型适配      │             │      │
│  │  │ - 标题/作者   │  │ - 3 风格 Prompt   │             │      │
│  │  │ - 长文本切分  │  │ - 角色提取        │             │      │
│  │  └──────────────┘  └──────────────────┘             │      │
│  └─────────────────────────────────────────────────────┘      │
│                           │                                   │
│  ┌────────────────────────┴──────────────────────────────┐   │
│  │                   Data Layer                           │   │
│  │  ┌──────────────┐  ┌──────────────────┐               │   │
│  │  │   SQLite     │  │   File System    │               │   │
│  │  │ (aiosqlite)  │  │ ./data/uploads/  │               │   │
│  │  │              │  │ ./data/outputs/  │               │   │
│  │  └──────────────┘  └──────────────────┘               │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 目录结构

```
AI-novel-to-script-tool/
├── backend/
│   ├── run.py                     # 入口: uvicorn app.main:app
│   ├── requirements.txt           # Python 依赖
│   ├── .env.example               # 环境变量模板
│   └── app/
│       ├── main.py                # FastAPI 工厂: CORS, lifespan, 路由注册
│       ├── core/
│       │   ├── config.py          # Pydantic Settings (env → 配置对象)
│       │   └── database.py        # 异步引擎 + Session + init_db()
│       ├── models/
│       │   └── __init__.py         # ORM: Project, Chapter, Character, Adaptation
│       ├── api/
│       │   ├── upload.py          # POST /api/upload
│       │   ├── projects.py        # GET/DELETE /api/projects[/{id}]
│       │   ├── chapters.py        # POST 单章/批量改编 + 后台任务
│       │   ├── export.py          # GET /api/projects/{id}/export/{fmt}
│       │   └── demo.py            # POST /api/demo (示例小说)
│       └── services/
│           ├── ai_adapter.py      # 核心引擎: 4 LLM Provider + 4 Prompt
│           └── text_parser.py     # 中文小说解析: 分章 + 切块
│
├── frontend/
│   ├── index.html                 # SPA 入口 (lang=zh-CN)
│   ├── vite.config.ts             # Vite + React + Tailwind + Proxy
│   ├── package.json               # react 19, tailwind 4, vite 8, ts 6
│   └── src/
│       ├── main.tsx               # ReactDOM.createRoot
│       ├── App.tsx                # 根组件: 页面状态机
│       ├── index.css              # Tailwind 导入 + @theme + 剧本样式
│       ├── api/
│       │   └── client.ts          # fetch 封装 + TypeScript 类型
│       └── components/
│           ├── ProjectList.tsx    # 项目卡片网格 (含删除)
│           ├── UploadNovel.tsx    # 拖拽上传 (.txt/.epub)
│           ├── ProjectDetail.tsx  # 双栏布局 + 改编控制 + 导出 + 原文/剧本切换
│           ├── ScriptViewer.tsx   # 剧本语法高亮渲染器
│           └── shared/
│               ├── Toast.tsx      # Toast 通知系统
│               └── DeleteModal.tsx # 删除确认模态框
│
├── docs/
│   ├── competitive-analysis.md    # 竞品技术分析报告
│   └── technical-architecture.md  # 本文档
├── README.md                      # 英文项目说明
└── PROJECT_PLAN.md                # 中文项目计划
```

---

## 4. 数据模型

### 4.1 ER 图

```
┌──────────────────────┐
│       Project        │
│──────────────────────│
│ id: UUID (PK)        │
│ user_id: str         │
│ title: str           │
│ author: str?         │
│ original_filename: str│
│ file_path: str?      │
│ status: enum         │  ← UPLOADED → PARSING → PARSED → ADAPTING → COMPLETED/FAILED
│ style: str           │  ← "film" | "comic" | "stage"（当前选择）
│ total_chapters: int  │
│ metadata_: JSON      │
│ created_at: datetime │
│ updated_at: datetime │
└──────┬───────────────┘
       │ 1
       │
       │ *                    ┌──────────────────────┐
       ├──────────────────────│     Character        │
       │  (cascade delete)    │──────────────────────│
       │                      │ id: UUID (PK)        │
       │                      │ project_id: FK       │
       │                      │ name: str            │
       │                      │ aliases: JSON[list]  │
       │                      │ description: text    │
       │                      │ traits: JSON[list]   │
       │                      │ relationships: JSON  │
       │                      │ created_at: datetime │
       │                      └──────────────────────┘
       │ *
       ├──────────────────────┐
       │  (cascade delete)    │  Chapter
       │                      │──────────────────────│
       │                      │ id: UUID (PK)        │
       │                      │ project_id: FK       │
       │                      │ chapter_num: int     │
       │                      │ title: str?          │
       │                      │ original_text: text  │
       │                      │ script_text: text?   │  ← 遗留字段（向后兼容）
       │                      │ chapter_summary: text?│  ← 本章摘要 (计划中)
       │                      │ cumulative_summary:  │  ← 累积摘要 (计划中)
       │                      │   text?              │
       │                      │ scenes: JSON?        │  ← 遗留字段
       │                      │ characters: JSON?    │  ← 遗留字段
       │                      │ status: enum         │  ← 遗留字段（以 Adaptation.status 为准）
       │                      │ error_message: text? │  ← 遗留字段
       │                      │ created_at/updated_at│
       └──────┬───────────────┘
              │ 1
              │
              │ *                    ┌──────────────────────────┐
              ├──────────────────────│     Adaptation           │
              │  (cascade delete)    │──────────────────────────│
              │                      │ id: UUID (PK)            │
              │                      │ chapter_id: FK           │
              │                      │ style: str               │  ← "film" | "comic" | "stage"
              │                      │ script_text: text?       │  ← 该风格的剧本
              │                      │ status: enum             │  ← PENDING → ADAPTING → COMPLETED/FAILED
              │                      │ error_message: text?     │
              │                      │ scenes: JSON?            │
              │                      │ characters: JSON?        │  ← 本章出场角色
              │                      │ created_at / updated_at  │
              │                      │ UNIQUE(chapter_id, style)│  ← 每章每种风格独立记录
              └──────────────────────────┘
```

> **设计决策**: Adaptation 表实现多风格独立存储。每章可以有 film / comic / stage 三条 Adaptation 记录，各自独立改编、独立状态。Chapter 表上的 `script_text` / `status` / `error_message` 保留为遗留字段（向后兼容），新代码读写 Adaptation 表。

### 4.2 状态机

**Project 状态流转**:
```
UPLOADED → PARSING → PARSED → ADAPTING → COMPLETED
                                      ↘ FAILED
```

**Chapter 状态流转**:
```
PENDING → ADAPTING → COMPLETED
                  ↘ FAILED
```

---

## 5. API 接口

| 方法 | 路径 | 功能 | 请求/响应 |
|------|------|------|-----------|
| `POST` | `/api/upload` | 上传小说文件 | multipart file → `UploadResult` |
| `GET` | `/api/projects` | 项目列表 | → `ProjectSummary[]` |
| `GET` | `/api/projects/{id}` | 项目详情 (含章节+角色) | → `ProjectDetail` |
| `DELETE` | `/api/projects/{id}` | 删除项目 | → 204 |
| `POST` | `/api/chapters/{id}/adapt` | 改编单章 | → `{chapter_id, status}` |
| `POST` | `/api/projects/{id}/adapt-all` | 改编全部章节 | → `{project_id, chapters_queued}` |
| `GET` | `/api/projects/{id}/export/markdown` | 导出 Markdown | → file download |
| `GET` | `/api/projects/{id}/export/txt` | 导出纯文本 | → file download |
| `GET` | `/api/projects/{id}/export/docx` | 导出 Word 文档 | → file download |
| `POST` | `/api/demo` | 加载示例小说 | → `UploadResult` |
| `PUT` | `/api/projects/{id}/style` | 更新项目风格 | → `{project_id, style, message}` |
| `GET` | `/api/health` | 健康检查 | → `{status, version}` |

---

## 6. 核心业务流程

### 6.1 小说上传 & 解析

```
用户拖拽/选择文件 (.txt / .epub)
         │
         ▼
前端: UploadNovel.tsx
  ├─ 校验: 扩展名 (.txt/.epub) + 大小 (< 50MB)
  ├─ POST /api/upload (FormData)
         │
         ▼
后端: upload.py
  ├─ 保存到 ./data/uploads/{uuid}.txt
  ├─ 解码: UTF-8 → GBK (fallback)
  │
  ├─ text_parser.parse_novel_text()
  │   ├─ 提取标题 (首行)
  │   ├─ 提取作者 (作者：/Author：匹配)
  │   ├─ 正则匹配章节边界:
  │   │   ├─ "第X章" / "第X节" (带/不带标题)
  │   │   ├─ "Chapter X" / "CH X"
  │   │   ├─ "序章/楔子/引子/尾声/番外"
  │   │   └─ "=== X ==="
  │   └─ 按边界分割, 返回 [(title, content), ...]
  │
  ├─ 创建 Project (status=PARSED)
  └─ 批量创建 Chapter (status=PENDING)
         │
         ▼
前端: 跳转到项目详情页
```

### 6.2 AI 改编 (剧本生成)

```
用户点击「改编本章」或「一键改编全部」
         │
         ▼
前端: POST /api/chapters/{id}/adapt (触发, 立即返回)
      或 POST /api/projects/{id}/adapt-all
         │
         ▼
后端: chapters.py → asyncio.create_task → _run_adaptation()
         │
         ├─ asyncio.to_thread(_sync_work)  ← 关键：避免 greenlet 冲突
         │     └─ 使用 SyncSessionLocal (同步 SQLAlchemy engine)
         │
         ├─ 1. 构建角色上下文 (如果 Project.characters 非空)
         │     "已知人物信息: 角色名（性格）: 描述"
         │
         ├─ 2. 获取上一章末尾 (最后 500 字符)
         │     用于跨章连贯性
         │
         ├─ 3. 长章节切分 (text_parser.split_long_chapter)
         │     max_length=8000, overlap=200
         │     在段落边界切分, 前后 chunk 共享 overlap 区域
         │
         ├─ 4. 逐 chunk 调用 AI:
         │     for chunk in chunks:
         │       ai_adapter.adapt_chapter_sync(  ← 同步方法，线程安全
         │         chapter_text=chunk,
         │         style="film|comic|stage",
         │         character_context=...,
         │         previous_scene_context=prev_chunk[-300:]
         │       )
         │         │
         │         ▼
         │     AIAdapter.adapt_chapter_sync()
         │       ├─ 使用 openai.OpenAI (同步客户端, base_url="https://api.deepseek.com/v1")
         │       ├─ extra_body={"thinking": {"type": "disabled"}}  ← 禁用 V4-Pro 思维链
         │       └─ 返回 LLM 生成的剧本文本
         │
         ├─ 5. 拼接所有 chunk 的剧本 (用 \n\n 连接)
         │
         ├─ 6. 更新 DB: chapter.script_text, status=COMPLETED
         │
         ├─ 7. 失败处理: logger.exception() 记录完整 traceback
         │     └─ chapter.status=FAILED, chapter.error_message=str(e)
         │
         └─ 8. 检查是否所有章节完成 → 更新 project.status
         │
         ▼
前端: 2-3 秒轮询 → 状态变化后刷新 → ScriptViewer 渲染 → Toast 通知
```

### 6.3 导出

```
用户点击 .md / .txt / .docx 下载链接
         │
         ▼
前端: <a href="/api/projects/{id}/export/{format}" download>
         │
         ▼
后端: export.py
  ├─ markdown:  # 标题 + ## 章节 + 剧本正文
  ├─ txt:       ===== 章节 ===== + 正文
  └─ docx:      python-docx 构建, 章节间加分页
         │
         ▼
StreamingResponse (Content-Disposition: attachment)
```

---

## 7. 上下文管理与记忆设计

### 7.1 现状：滑动窗口（仅短期记忆）

当前改编流水线中，LLM 能获取的上下文来源（[chapters.py:113-213](backend/app/api/chapters.py#L113-L213)）：

| 来源 | 机制 | 范围 | 局限 |
|------|------|------|------|
| 角色上下文 | 从 `Project.characters` 读取 | 全项目 | **永远为空** — `extract_characters()` 从未被调用（代码已实现但未接线） |
| 上一章末尾 | 上一章剧本最后 500 字符 | 仅前 1 章 | 非结构化文本，无法传递情节/状态信息 |
| Chunk 重叠 | 长章切块时前 chunk 尾 300 字符 | 同一章内 | 仅解决切分断裂，不跨章 |

**已实现改进**：
- DeepSeek-V4-Pro thinking mode 已通过 `extra_body={"thinking": {"type": "disabled"}}` 禁用，避免推理 token 消耗输出空间
- `original_text` 已通过 API 暴露给前端，用于原文/剧本对比
- 同步引擎 (`SyncSessionLocal`) 解决后台任务 greenlet 冲突
- 错误信息通过 `chapter.error_message` 传递到前端展示

**核心问题**：改编第 10 章时，LLM 不知道第 1-8 章发生了什么。角色状态变化（黑化、死亡、离开）无法跨章追踪。

### 7.2 设计：摘要链 (Summary Chain)

在改编流水线中增加 **摘要生成** 步骤，形成跨章记忆链：

```
Chapter 1 改编完成
    │
    ├─→ summarize_chapter(script) → Chapter1.chapter_summary
    ├─→ Chapter1.cumulative_summary = chapter_summary
    │
    ▼
Chapter 2 改编
    ├─→ story_context = Chapter1.cumulative_summary  ← 作为"前情提要"传入
    ├─→ 改编完成
    ├─→ summarize_chapter(script, prev_summary) → 合并到累积摘要
    ├─→ Chapter2.cumulative_summary = 第1-2章累积
    │
    ▼
Chapter N 改编
    ├─→ story_context = Chapter[N-1].cumulative_summary  ← 前 N-1 章全部信息
    ├─→ 改编完成
    └─→ ChapterN.cumulative_summary = 第1-N章累积
```

### 7.3 数据模型

Chapter 表新增 2 个字段（[models.py](backend/app/models/models.py)）：

```python
class Chapter(Base):
    # ... 现有字段 ...
    chapter_summary: Mapped[Optional[str]]   # 本章摘要（单章独立）
    cumulative_summary: Mapped[Optional[str]] # 累积摘要（第1章～本章）
```

### 7.4 摘要 Prompt 设计

```json
{
  "new_characters": [
    {"name": "姓名", "role": "身份", "first_appearance": "首次出场场景"}
  ],
  "character_state_changes": [
    {"name": "姓名", "before": "之前状态", "after": "当前状态"}
  ],
  "key_events": ["事件1", "事件2"],
  "unresolved_threads": ["悬念1"],
  "scene_summary": "本章场景概述 (100字内)"
}
```

### 7.5 LLM 上下文窗口拼接

改编第 N 章时，传给 LLM 的完整 User Message 结构：

```
## 前情提要                          ← 新增：累积摘要
第1-3章概要：角色A从京城出发前往边关，
途中遇到角色B。当前未解决悬念：角色C的身份尚未揭晓。

## 已知人物信息                      ← Phase 1 接入后生效
- 角色A（坚毅果敢）：主角，青年剑客
- 角色B（神秘冷漠）：配角，身份不明

## 上一场结尾                        ← 原有：第 N-1 章末尾
角色A推开客栈房门，里面空无一人。

## 需要改编的小说片段                ← 原有：第 N 章文本
...
```

### 7.6 与行业方案对比

| 层级 | 行业方案 | 当前 Demo | 实现复杂度 |
|------|----------|-----------|-----------|
| 短期记忆 | 滑动窗口 | ✅ Chunk overlap | 已实现 |
| 长期记忆 | 结构化摘要 + DB 持久化 | 🔧 摘要链 (本次新增) | 低 (~30min) |
| 语义召回 | 向量数据库 (ChromaDB/Pinecone) | ❌ MVP 不做 | 中 (需额外基础设施) |
| 知识图谱 | GraphRAG / E²RAG 双图 | ❌ MVP 不做 | 高 |

---

## 8. AI Prompt 设计

### 8.1 电影剧本 (`SYSTEM_PROMPT_FILM`)

AI 角色: **资深影视编剧**

核心规则:
1. 保留原著核心情节，不删减
2. 叙述描述 → `【舞台指示】` (心理/动作/环境描写)
3. 对白精炼，保留原意和语气
4. 时间/地点变化时自动拆分场景
5. 严格输出格式:

```
第 [序号] 场
时间：[time]
地点：[location]
人物：[name1、name2]
【舞台指示内容】
角色A：（对白）
角色B：（对白）
---
```

### 8.2 漫画分镜 (`SYSTEM_PROMPT_COMIC`)

AI 角色: **漫画分镜师+编剧**

核心规则:
1. 全部叙述转换为可视化画面
2. 重要画面标注分格
3. 对白改为简短对话 (适合气泡)
4. `[画面：景别描述]` 替代舞台指示
5. 控制每页信息量，保持阅读节奏

### 8.3 舞台剧本 (`SYSTEM_PROMPT_STAGE`)

AI 角色: **舞台剧编剧**

核心规则:
1. 考虑舞台空间限制设计场景
2. 强化戏剧张力和冲突
3. 台词有舞台感和韵律感
4. `[左]/[右]` 标注演员走位

### 8.4 角色提取 (`CHARACTER_EXTRACTION_PROMPT`)

要求 LLM 以 JSON 格式返回:
```json
{
  "characters": [{
    "name": "姓名",
    "aliases": ["别名"],
    "description": "描述",
    "traits": ["性格特征"],
    "role": "主角/配角/反派/路人"
  }]
}
```

> **⚠ 注意**: 当前 `extract_characters()` 方法已实现但从未被调用——角色提取未接入上传/改编流水线。

---

## 9. 前端组件架构

### 9.1 组件概览

| 组件 | 功能 | 关键特性 |
|------|------|----------|
| `App.tsx` | 根组件 + 页面状态机 | `page` + `selectedProjectId` 状态管理 |
| `ProjectList.tsx` | 项目卡片网格 | 加载示例、空状态、删除确认 |
| `UploadNovel.tsx` | 拖拽上传 | .txt/.epub 验证、进度动画 |
| `ProjectDetail.tsx` | 项目详情（双栏） | 风格切换、原文/剧本对比、进度动画、质量 Warning、错误展示、防跳章 |
| `ScriptViewer.tsx` | 剧本语法高亮 | 6 类 CSS 规则，支持 highlightLines 质量高亮，原文/剧本双模式 |
| `Toast.tsx` | Toast 通知 | Context Provider 模式，自动消失 |
| `DeleteModal.tsx` | 删除确认 | 模态框覆盖层，显示项目名称 |

### 9.2 导航状态机

```
                    ┌──────────────┐
        ┌──────────→│  ProjectList │ (page="projects")
        │           └──────┬───────┘
        │                  │ 点击项目卡
        │                  ▼
        │           ┌──────────────┐
        │           │ProjectDetail │ (selectedProjectId != null)
        │           └──────┬───────┘
        │                  │ 返回按钮
        │                  │
        │  ┌───────────────┘
        │  ▼
   ┌──────────┐
   │UploadNovel│ (page="upload")
   └──────────┘
        │ 上传成功 → 自动跳转到 ProjectDetail
        └──────────────────────────────────────┘
```

### 9.3 ScriptViewer 语法高亮

| 规则 | 匹配 | 视觉 |
|------|------|------|
| 场景标题 | `第 X 场` | 靛蓝粗体 + 下划边框 |
| 元数据 | `时间/地点/人物:` | 小号灰色 |
| 舞台指示 | `【...】` | 靛蓝斜体 + 缩进 |
| 画面描述 | `[画面: ...]` | 浅靛蓝斜体 |
| 对白 | `角色名：内容` | 粗体名字 + 正文 |
| 动作指示 | `[动作]` | 小号灰色 |
| **质量高亮** | `highlightLines` prop | 黄色渐变背景 + 橙色左边框 (`.highlight-warn`) |

**highlightLines 机制**：
- `ScriptViewer` 接受可选 `highlightLines?: Set<number>`（0-based 行号集合）
- 高亮行叠加 `.highlight-warn` CSS class，与原有语法高亮样式共存
- 每行添加 `id="script-line-N"` 用于 `scrollIntoView` 定位
- 点击质量警告横幅的警告项可平滑滚动到第一个高亮行
- 剧本视图和原文视图各自有独立的 `highlightSet`，分析逻辑不同

---

## 10. 配置参数

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_PROVIDER` | `deepseek` | LLM 提供商 (anthropic/openai/qwen/deepseek) |
| `DEEPSEEK_MODEL` | `deepseek-v4-pro` | DeepSeek 模型名称 |
| `LLM_MAX_TOKENS` | `8192` | 每次 API 调用最大输出 token |
| `LLM_TEMPERATURE` | `0.7` | 生成温度 |
| `MAX_CHAPTER_LENGTH` | `8000` | 单次改编最大字符数 (超出则切分) |
| `CHAPTER_OVERLAP` | `200` | 长章切分时的重叠字符数 |
| `MAX_UPLOAD_SIZE_MB` | `50` | 上传文件大小上限 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db` | 数据库路径 |

---

## 11. 技术特点 & 限制

### 11.1 架构特点
- **单体应用**: 前后端分离但部署在一起 (Vite proxy → FastAPI)
- **无状态 API**: 无 Session，userId 固定为 "default"
- **双数据库引擎**: async SQLAlchemy (aiosqlite) 用于 API 请求 + sync SQLAlchemy (sqlite) 用于后台线程
- **后台任务**: `asyncio.create_task()` + `asyncio.to_thread()` 执行改编，避免 BackgroundTasks 的 greenlet 冲突
- **轮询而非推送**: 前端 2-3 秒 polling 检测改编完成，非 WebSocket/SSE
- **多 LLM Provider**: Anthropic / OpenAI / Qwen / DeepSeek 四 Provider 可切换（异步 `adapt_chapter`）；同步方法 `adapt_chapter_sync` 硬编码为 DeepSeek（后台线程专用）
- **DeepSeek-V4-Pro**: 默认 Provider，成本 ~¥0.002/章，通过 `extra_body={"thinking": {"type": "disabled"}}` 禁用思维链
- **错误诊断**: `logging.basicConfig()` + `logger.exception()` 完整 traceback + `error_message` 前端展示
- **单例 AIAdapter**: 全局共享同一个 provider 配置
- **中文优先**: 所有 API 错误消息、UI 标签、提示词均为中文

### 11.2 MVP 边界 (不做的事)
- ❌ 用户认证 & 多用户隔离
- ❌ Multi-Agent 协作架构
- ❌ RAG / 向量数据库 / 知识图谱
- ❌ 图片/视频生成
- ❌ FCPXML / EDL 专业导出
- ❌ Docker / K8s 部署配置
- ❌ 自动化测试
- ❌ YAML Schema 输出
- ❌ EPUB 正文提取 (已接受文件但解析为纯文本)
- ❌ 暗色模式 / 移动端适配

### 11.3 已实现超出原计划
- ✅ DeepSeek-V4-Pro 集成（原计划 Anthropic 默认）
- ✅ 原文/剧本对比切换（新增需求）
- ✅ Toast 通知系统
- ✅ 同步数据库引擎（解决 greenlet 冲突）
- ✅ 错误诊断完整链路（日志 → API → 前端展示）
- ✅ 防章节跳转（useRef 初始加载守卫）
- ✅ 假进度修复（仅循环处理中状态，完成由后端确认）
- ✅ **Adaptation 表多风格独立存储** — 每章 × 每风格独立记录，切换风格不覆盖
- ✅ **质量检查问题高亮** — 剧本视图中黄色左边框高亮问题行，点击警告项 scrollIntoView 定位
- ✅ **AI 原文-剧本对齐映射** — LLM 改编时输出段落→场次对应关系，原文高亮精准定位到问题段落（替换旧启发式）

---

## 12. 快速启动

详细使用说明请参阅 [USAGE.md](../USAGE.md)。

### 后端
```bash
cd backend
cp .env.example .env          # 填入 LLM API Key
pip install -r requirements.txt
python run.py                 # → http://localhost:8000
```

### 前端
```bash
cd frontend
npm install
npm run dev                   # → http://localhost:5173
```

### 健康检查
```bash
curl http://localhost:8000/api/health
# → {"status":"ok","version":"0.1.0"}
```

---

**文档生成日期**: 2026-06-06 | **更新**: 2026-06-06 | **基于代码版本**: `80a7456` (feature/demo-sample-novel-api)
