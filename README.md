# AI 小说转剧本工具

基于大语言模型（LLM）的智能小说改编剧本平台。

## 核心功能

- 📖 **小说上传**：支持 `.txt` / `.epub` 格式，自动识别章节
- 🤖 **AI 改编**：调用 DeepSeek/Claude/GPT/Qwen 将小说转换为结构化剧本
- 🎬 **多风格独立存储**：影视剧本 / 漫画分镜 / 舞台剧，三种风格各自独立改编、互不覆盖
- 🎭 **示例小说一键加载**：无需准备文件，点击即可体验全流程
- 📖 **原文/剧本对比**：一键切换查看改编前后效果
- ⚠️ **质量自检**：自动检测格式问题，高亮定位问题行
- 📋 **批量改编**：勾选 1-5 章，按需批量改编
- 📤 **多格式导出**：Markdown / TXT / Word（.docx）/ YAML（结构化剧本数据）
  - 全本导出：`标题_全本_风格剧本.ext`
  - 单章导出：`标题_第N章_风格剧本.ext`

## 项目结构

```
├── backend/                  # Python FastAPI 后端
│   ├── app/
│   │   ├── api/              # API 路由
│   │   │   ├── upload.py     # 文件上传
│   │   │   ├── projects.py   # 项目管理
│   │   │   ├── chapters.py   # 章节改编 & 批量改编
│   │   │   ├── demo.py       # 示例小说
│   │   │   └── export.py     # 剧本导出 (md/txt/docx/yaml，全本 & 单章)
│   │   ├── core/             # 配置 & 数据库
│   │   ├── models/           # ORM 模型 (Project/Chapter/Character/Adaptation)
│   │   └── services/         # 核心服务
│   │       ├── ai_adapter.py     # AI 改编引擎（AI→JSON→Prose 单次流水线）
│   │       ├── text_parser.py    # 小说文本解析
│   │       └── text_utils.py     # 段落编号 & 切分
│   ├── run.py                # 开发启动
│   └── requirements.txt
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── api/client.ts     # API 客户端
│   │   ├── components/
│   │   │   ├── ProjectList.tsx
│   │   │   ├── UploadNovel.tsx
│   │   │   ├── ProjectDetail.tsx
│   │   │   ├── ScriptViewer.tsx
│   │   │   └── shared/        # Toast / DeleteModal 通用组件
│   │   └── App.tsx
│   └── vite.config.ts
├── docs/                     # 设计文档
│   ├── product-requirements.md
│   ├── solution-design.md
│   ├── technical-architecture.md
│   ├── information-architecture.md
│   ├── implementation-plan.md
│   ├── yaml-schema.md         # YAML Schema 设计文档
│   └── competitive-analysis.md
├── USAGE.md
└── README.md
```

## 快速开始

### 后端

```bash
cd backend
cp .env.example .env          # 编辑 .env，填入 API Key
pip install -r requirements.txt
python run.py                 # 启动 http://localhost:8000
```

### 前端

```bash
cd frontend
npm install
npm run dev                   # 启动 http://localhost:5173
```

### API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload` | POST | 上传小说文件 |
| `/api/demo` | POST | 加载示例小说 |
| `/api/projects` | GET | 项目列表 |
| `/api/projects/{id}` | GET | 项目详情 |
| `/api/projects/{id}/style` | PUT | 切换改编风格 |
| `/api/projects/{id}/adapt-batch` | POST | 批量改编（选 1-5 章） |
| `/api/chapters/{id}/adapt` | POST | 改编单章 |
| `/api/projects/{id}/export/markdown` | GET | 导出全本 Markdown |
| `/api/projects/{id}/export/txt` | GET | 导出全本 TXT |
| `/api/projects/{id}/export/docx` | GET | 导出全本 Word |
| `/api/projects/{id}/export/yaml` | GET | 导出全本 YAML |
| `/api/chapters/{id}/export/markdown` | GET | 导出单章 Markdown |
| `/api/chapters/{id}/export/txt` | GET | 导出单章 TXT |
| `/api/chapters/{id}/export/docx` | GET | 导出单章 Word |
| `/api/chapters/{id}/export/yaml` | GET | 导出单章 YAML |

## 技术栈

- **后端**：Python FastAPI + SQLAlchemy + SQLite
- **前端**：React 19 + TypeScript + TailwindCSS v4 + Vite
- **AI**：DeepSeek（默认）/ Anthropic Claude / OpenAI GPT / 阿里通义千问（可切换）
- **YAML**：PyYAML（结构化剧本序列化）

## 依赖

### 后端 (requirements.txt)

| 包 | 版本 | 用途 |
|----|------|------|
| fastapi | 0.115 | Web 框架 |
| uvicorn | 0.30 | ASGI 服务器 |
| sqlalchemy | 2.0 | ORM 数据库操作 |
| aiosqlite | 0.20 | 异步 SQLite 驱动 |
| pydantic | 2.9 | 数据校验 & 配置 |
| anthropic | 0.39 | Anthropic Claude API |
| openai | ≥1.30 | OpenAI / DeepSeek / Qwen API |
| pyyaml | 6.0 | YAML 序列化 |
| python-docx | 1.1 | Word 文档生成 |
| httpx | 0.27 | HTTP 客户端 |
| python-multipart | 0.0 | 文件上传解析 |

### 前端 (package.json)

| 包 | 版本 | 用途 |
|----|------|------|
| react | ^19.2 | UI 框架 |
| react-dom | ^19.2 | React DOM 渲染 |
| typescript | ~6.0 | 类型系统 |
| vite | ^8.0 | 构建工具 |
| tailwindcss | ^4.3 | CSS 框架 |
| @vitejs/plugin-react | ^6.0 | Vite React 插件 |
