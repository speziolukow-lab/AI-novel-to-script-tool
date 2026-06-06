# AI小说转剧本 Demo 实施计划

> **状态**: Phase 0-3 已全部完成 ✅ | Phase 4 (EPUB) 未实施 | **更新**: 2026-06-06

## Context

项目 `AI-novel-to-script-tool` 已有完整的前后端脚手架：FastAPI 后端（上传/解析/AI改编/导出）+ React 前端（项目列表/上传/剧本阅读器）+ 4 个 LLM 适配器（Anthropic/OpenAI/Qwen/DeepSeek）。目标是快速打造一个能**端到端演示**的 Demo。

**已完成超出原计划的新增功能**：
- ✅ Adaptation 表 — 多风格独立改编存储
- ✅ 质量检查问题高亮 — 剧本 + 原文双视图独立高亮，点击定位
- ✅ 风格切换防覆盖 — useRef 守卫 + 独立存储

---

## Phase 0：环境搭建 & 跑通全流程（⏱ ~45min）

### 0.1 添加 DeepSeek Provider
- `ai_adapter.py` 中新增 `_call_deepseek()` 方法（DeepSeek API 兼容 OpenAI 格式）
- `config.py` 中新增 `DEEPSEEK_API_KEY` 和 `DEEPSEEK_MODEL` 配置
- `.env.example` 同步更新

### 0.2 创建 `.env`
- 复制 `backend\.env.example` → `backend\.env`
- `LLM_PROVIDER=deepseek`
- 填入 DeepSeek API Key（从 platform.deepseek.com 获取）

### 0.3 安装后端依赖 & 启动
```bash
cd backend
pip install -r requirements.txt
python run.py    # → localhost:8000
```

### 0.4 安装前端依赖 & 启动
```bash
cd frontend
npm install
npm run dev      # → localhost:5173，/api 代理到 localhost:8000
```

### 0.5 准备测试小说
- 找一个 3-5 章的中文小说 TXT，有清晰的章节标记（`第X章`）
- 建议用公有领域作品（如《红楼梦》前3章）或自创短篇

### 0.6 验证全流程
→ 上传小说 → 自动分章 → 点击"改编本章" → 查看剧本输出 → 导出 MD/DOCX

---

## Phase 1：角色提取接入改编流水线（⏱ ~1h，**影响最大**）

### 问题
`ai_adapter.py` 的 `extract_characters()` 已实现，但**从未被调用**。`_run_adaptation` 中的角色上下文构建依赖 DB 中已有 Character 记录，而没有任何代码往 Character 表写入数据。

### 改动

**① `backend/app/api/upload.py`** — 上传完成后自动提取角色
- 小说解析完成后，后台调用 `ai_adapter.extract_characters()` 分析前 2-3 章
- 将提取的角色（name, aliases, description, traits）写入 `Character` 表

**② `backend/app/api/chapters.py`** — `_run_adaptation` 中角色上下文已验证可自动生效
- 确认角色上下文格式对 LLM 有用（当前格式：`- 角色名（性格特征）：角色描述`）
- 增加别名信息，让 LLM 能识别同一角色的不同称呼

---

## Phase 1.5：跨章长期记忆 — 摘要链（⏱ ~30min）

### 问题
当前改编第 N 章时，只能看到第 N-1 章剧本的**最后 500 字符尾巴**，没有结构化前情提要。第 10 章不知道第 1 章发生了什么。角色状态变化（黑化/死亡/离开）无法跨章追踪。

### 方案：摘要链 (Summary Chain)
每章改编完成后，用 LLM 生成结构化摘要 → 存 DB → 改编下一章时把**累积摘要**作为"前情提要"传入 System Prompt。

### 改动

**① `backend/app/models/models.py`** — Chapter 表新增 2 个字段
- `chapter_summary: Text | None` — 本章摘要（单章独立）
- `cumulative_summary: Text | None` — 累积摘要（第1章～本章）

**② `backend/app/services/ai_adapter.py`** — 新增摘要生成方法
- `CHAPTER_SUMMARY_PROMPT`：要求 LLM 以结构化格式输出：新出场角色、角色状态变化、关键事件、未解决悬念、场景概述
- `summarize_chapter(script_text, previous_summary) -> dict`：调用 LLM 生成本章摘要，合并到累积摘要

**③ `backend/app/api/chapters.py` `_run_adaptation()`** — 改编前后接入摘要
- 改编前：读取上一章的 `cumulative_summary`，作为 `story_context` 传入 `adapt_chapter()`
- 改编后：调用 `ai_adapter.summarize_chapter()` 生成并保存本章摘要

**④ `backend/app/services/ai_adapter.py` `adapt_chapter()`** — 新增 story_context 参数
- 在 User Message 中增加 `## 前情提要` 段落

### 成本
| 操作 | 额外 token |
|------|-----------|
| 每章摘要生成 | ~300 input + ~200 output |
| 改编时附加上下文 | ~200-500 token (累积摘要) |
| **每章额外** | ~800 token ≈ ¥0.002（DeepSeek） |

### 效果
```
改前：第10章只能看到第9章的 500 字尾巴
改后：第10章能看到：
  ├─ 角色状态快照（XX已黑化、YY已离开京城）
  ├─ 前9章关键事件列表
  ├─ 未解决的悬念
  └─ 当前场景位置
```

---

## Phase 2：Prompt 增强（⏱ ~1.5h）

### 2.1 增强电影剧本 System Prompt
当前 Prompt 较通用，需要针对 Demo 效果增强：

- **强制格式约束**：明确要求所有舞台指示用 `【】`、所有对白用 `角色名：（内容）`
- **反幻觉指令**：禁止创造原文不存在的新角色或情节、不增删对白
- **角色外貌提取**：首次出现角色时，从原文提取外貌描述写入 `【角色外貌：...】`
- **场景切换显式标注**：每次场景变化用 `---` 分隔

### 2.2 增加章节结构预分析
- 新增 `analyze_chapter_structure()` 方法：快速列出本章场景 + 出场人物 + 关键事件
- 将结构化 outline 传给主改编调用作为上下文
- 成本：每章多 ~200 token，但输出结构显著改善

### 2.3 增加轻量质量自检
- 改编完成后检查：是否有场号 `第X场`、对话格式是否规范、长度是否合理
- 不合格则标记 warning 显示在 UI 中

---

## Phase 3：Demo 体验打磨（⏱ ~2h）

### 3.1 一键加载示例小说
- 后端新增 `POST /api/demo` 端点，从 `backend/data/samples/` 读取预置小说
- 前端在项目列表页增加「🎭 加载示例小说」按钮
- Demo 无需用户自己准备文件，一键体验全流程

### 3.2 改进改编中的进度展示
- 前端改编状态从简单的 spinner → 显示当前阶段（"正在分析场景…" → "正在生成剧本…"）
- 添加已用时间计数

### 3.3 前端风格切换
- 项目详情页增加风格切换按钮（电影/漫画/舞台剧）
- 切换后重新改编时使用新风格

### 3.4 导出验证 & 修复
- 确认 Markdown / TXT / DOCX 三种导出正常
- DOCX 短章节不要强制分页

---

## Phase 4（可选）：EPUB 支持（⏱ ~1h）

- `upload.py` 中实现 EPUB 的 ZIP 解压 + XHTML 文本提取
- 按 spine 顺序拼接章节

---

## 关键文件清单

| 文件 | 改动类型 | 状态 |
|------|----------|------|
| `backend/.env` | 新建（从 .env.example 复制） | ✅ |
| `backend/app/core/config.py` | 修改：新增 DeepSeek 配置 | ✅ |
| `backend/.env.example` | 修改：新增 DeepSeek 配置项 | ✅ |
| `backend/app/core/database.py` | 修改：新增 SyncSessionLocal (sync engine) | ✅ |
| `backend/app/models/__init__.py` | 修改：Project + Chapter + Character + Adaptation (新增) | ✅ |
| `backend/app/services/ai_adapter.py` | 修改：新增 DeepSeek provider + adapt_chapter_sync + thinking disabled | ✅ |
| `backend/app/api/upload.py` | 待修改：角色提取后台任务 | 🔧 |
| `backend/app/api/chapters.py` | 修改：asyncio.create_task + asyncio.to_thread + Adaptation 读写 | ✅ |
| `backend/app/api/projects.py` | 修改：projects API 返回 adaptations + original_text | ✅ |
| `backend/app/api/demo.py` | 新建：示例小说端点 | ✅ |
| `frontend/src/components/ProjectDetail.tsx` | 修改：风格切换 + 进度动画 + 原文/剧本对比 + 质量 Warning + 错误展示 | ✅ |
| `frontend/src/components/ProjectList.tsx` | 修改：示例小说按钮 + 空状态 + 删除模态框 | ✅ |
| `frontend/src/components/ScriptViewer.tsx` | 修改：highlightLines prop + scrollIntoView + 原文/剧本双模式 | ✅ |
| `frontend/src/components/shared/` | 新建：Toast.tsx + DeleteModal.tsx | ✅ |
| `frontend/src/api/client.ts` | 修改：新增 demo/style API 调用 + original_text 字段 | ✅ |
| `USAGE.md` | 新建：使用文档 | ✅ |

---

## 不做的事（Demo 边界）

- ❌ Multi-Agent 架构（多次 LLM 调用，成本高，Demo 看不出差异）
- ❌ 向量数据库 / RAG 记忆系统（需要额外基础设施）
- ❌ 知识图谱 / GraphRAG（实现复杂度高）
- ❌ 图片/视频生成（非文本转剧本范围）
- ❌ FCPXML/EDL 导出（专业后期流程，Demo 用不上）

---

## 验证方式

1. **启动验证**：后端 `curl localhost:8000/api/health` → `{"status":"ok"}`
2. **上传验证**：上传测试 TXT → 自动分章 → 章节列表正确
3. **示例验证**：点击"加载示例" → 无需上传文件即可体验全流程
4. **改编验证**：逐章改编 → 剧本输出格式正确（`第X场` / `【】` / `角色：对白`）
5. **风格切换验证**：改编影视 → 切换漫画 → 显示未改编 → 切回影视 → 之前内容仍在
6. **质量检查验证**：改编含格式问题的章节 → Warning 横幅显示 → 点击跳转定位
7. **原文对比验证**：已改编章节 → 点击「原文」→ 显示原始小说文本
8. **导出验证**：下载 MD / TXT / DOCX → 内容完整
9. **记忆验证**（🔧 待实现）：改编第3章后检查 Chapter 表 `cumulative_summary` 字段

---

## 关联文档

| 文档 | 用途 |
|------|------|
| [product-requirements.md](product-requirements.md) | 产品需求文档 |
| [technical-architecture.md](technical-architecture.md) | 技术架构详情 |
| [../USAGE.md](../USAGE.md) | 使用文档 |
