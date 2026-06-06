# AI 小说转剧本工具

基于大语言模型（LLM）的智能小说改编剧本平台。

## 核心功能

- 📖 **小说上传**：支持 `.txt` / `.epub` 格式，自动识别章节
- 🤖 **AI 改编**：调用 Claude/GPT/Qwen 将小说转换为剧本格式
- 🎬 **多风格支持**：影视剧本 / 漫画分镜 / 舞台剧
- 📤 **多格式导出**：Markdown / TXT / Word（.docx）

## 项目结构

```
├── backend/                  # Python FastAPI 后端
│   ├── app/
│   │   ├── api/              # API 路由
│   │   │   ├── upload.py     # 文件上传
│   │   │   ├── projects.py   # 项目管理
│   │   │   ├── chapters.py   # 章节改编
│   │   │   └── export.py     # 剧本导出
│   │   ├── core/             # 配置 & 数据库
│   │   ├── models/           # ORM 模型
│   │   └── services/         # 核心服务
│   │       ├── ai_adapter.py     # AI 改编引擎
│   │       └── text_parser.py    # 小说文本解析
│   ├── run.py                # 开发启动
│   └── requirements.txt
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── api/client.ts     # API 客户端
│   │   ├── components/
│   │   │   ├── ProjectList.tsx
│   │   │   ├── UploadNovel.tsx
│   │   │   ├── ProjectDetail.tsx
│   │   │   └── ScriptViewer.tsx
│   │   └── App.tsx
│   └── vite.config.ts
├── PROJECT_PLAN.md           # 项目计划文档
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
| `/api/projects` | GET | 项目列表 |
| `/api/projects/{id}` | GET | 项目详情 |
| `/api/chapters/{id}/adapt` | POST | 改编单章 |
| `/api/projects/{id}/adapt-all` | POST | 改编全部章节 |
| `/api/projects/{id}/export/markdown` | GET | 导出 Markdown |
| `/api/projects/{id}/export/docx` | GET | 导出 Word |
| `/api/projects/{id}/export/txt` | GET | 导出 TXT |

## 技术栈

- **后端**：Python FastAPI + SQLAlchemy + SQLite
- **前端**：React 19 + TypeScript + TailwindCSS v4 + Vite
- **AI**：Anthropic Claude / OpenAI GPT / 阿里通义千问（可切换）
