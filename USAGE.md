# AI 小说转剧本工具 — 使用文档

## 一、项目简介

将中文小说智能改编为结构化剧本格式，支持**影视剧本**、**漫画分镜**、**舞台剧本**三种风格。基于大语言模型（LLM）驱动，自动完成场景拆分、对白提取、舞台指示生成。

---

## 二、系统要求

| 依赖 | 版本要求 |
|------|----------|
| Python | ≥ 3.11 |
| Node.js | ≥ 18 |
| 包管理器 | pip + npm |

---

## 三、项目结构

```
AI-novel-to-script-tool/
├── backend/                  # Python FastAPI 后端
│   ├── app/
│   │   ├── api/              # API 路由（upload, projects, chapters, export, demo）
│   │   ├── core/             # 配置 & 数据库
│   │   ├── models/           # SQLAlchemy 数据模型
│   │   └── services/         # AI 改编引擎 & 文本解析
│   ├── .env                  # 环境变量配置（API Key 等）
│   ├── .env.example          # 配置模板
│   ├── requirements.txt      # Python 依赖
│   ├── data/samples/         # 示例小说（.txt 文件）
│   └── run.py                # 后端启动入口
├── frontend/                 # React + TypeScript 前端
│   ├── src/
│   │   ├── api/client.ts     # API 调用封装
│   │   └── components/       # UI 组件
│   ├── package.json
│   └── vite.config.ts        # Vite 配置（含 API 代理）
└── data/                     # 运行时数据（自动生成）
    ├── app.db                # SQLite 数据库
    ├── uploads/              # 上传的小说文件
    └── outputs/              # 导出的剧本文件
```

---

## 四、LLM 配置

### 4.1 支持的 LLM 提供商

编辑 `backend/.env` 文件，设置 `LLM_PROVIDER` 为以下值之一：

| 提供商 | `LLM_PROVIDER` 值 | 所需配置项 |
|--------|-------------------|-----------|
| **DeepSeek**（默认） | `deepseek` | `DEEPSEEK_API_KEY` + `DEEPSEEK_MODEL` |
| **OpenAI** | `openai` | `OPENAI_API_KEY` + `OPENAI_MODEL` |
| **Anthropic** | `anthropic` | `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL` |
| **通义千问** | `qwen` | `QWEN_API_KEY` |

### 4.2 配置示例

#### 使用 DeepSeek（默认）

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_MODEL=deepseek-v4-pro
```

#### 使用 OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o
```

#### 使用 Anthropic Claude

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-sonnet-4-6
```

#### 使用通义千问

```env
LLM_PROVIDER=qwen
QWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **注意**：通义千问使用阿里云 DashScope 兼容接口，模型固定为 `qwen-plus`。

### 4.3 LLM 参数调整

```env
# 最大输出 Token 数（默认 8192）
LLM_MAX_TOKENS=8192

# 生成随机性（0-1，越高越有创意）
LLM_TEMPERATURE=0.7

# 单章最大处理长度（字符数）
MAX_CHAPTER_LENGTH=8000
```

---

## 五、启动方式

### 5.1 第一步：安装后端依赖

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 5.2 第二步：配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env，填入你的 API Key（必填）
# 用任意文本编辑器打开 backend/.env，修改对应字段
```

### 5.3 第三步：启动后端

```bash
cd backend
python run.py
```

后端启动后：
- **API 地址**：`http://localhost:8000`
- **健康检查**：`http://localhost:8000/api/health`
- **API 文档**：`http://localhost:8000/docs`（Swagger UI）

### 5.4 第四步：安装并启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动后：
- **访问地址**：`http://localhost:5173`

> 前端的 Vite 开发服务器已配置代理，`/api` 请求会自动转发到后端 `http://localhost:8000`。

---

## 六、使用流程

### 6.1 方式一：加载示例小说（快速体验）

1. 准备示例文件：将一个 `.txt` 格式的中文小说文件放入 `backend/data/samples/` 目录
2. 打开浏览器访问 `http://localhost:5173`
3. 在项目列表页点击 **"🎭 加载示例小说"** 按钮
4. 系统自动解析章节并跳转到项目详情页

### 6.2 方式二：上传自己的小说

1. 访问 `http://localhost:5173`，点击导航栏 **"📤 上传小说"**
2. 选择 `.txt` 格式的小说文件（支持 UTF-8 / GBK 编码）
3. 系统自动分章解析，完成后跳转到项目详情页

### 6.3 章节改编

在项目详情页：

1. **选择风格**：顶部下拉框选择「影视剧本 / 漫画分镜 / 舞台剧本」
2. **改编单章**：点击某章右侧的 ▶️ 按钮
3. **全部改编**：点击顶部 **"⚡ 一键改编全部"** 按钮，批量处理所有章节
4. 改编完成后自动显示剧本内容

> **注意**：三种风格各自独立存储，切换风格不会覆盖已改编的内容。例如：改编完影视剧本 → 切换到漫画分镜 → 显示未改编状态 → 切回影视剧本 → 之前的内容仍在。

### 6.4 查看剧本

- **剧本视图**：语法高亮显示（场景标题、角色对白、舞台指示等不同颜色）
- **原文视图**：点击切换按钮查看原始小说文本
- 两种视图之间可随时切换对比

### 6.5 质量检查

改编完成后系统自动进行质量检查：

| 检查项 | 说明 |
|--------|------|
| 场景数量 | 少于 2 场会提示 |
| 对话格式 | 检测缺少「角色名：」前缀的问题行 |
| 产出长度 | 剧本长度不足原文 40% 时提示 |

- 有问题的行会在剧本中用**黄色左边框高亮**
- 原文视图中可疑段落也会独立标记（>500 字长段落、角色对话句）
- 点击警告横幅中的项可自动滚动到对应位置

### 6.6 导出

点击 **"📥 导出"** 下拉菜单，支持三种格式：

| 格式 | 说明 |
|------|------|
| Markdown | 纯文本，适合进一步编辑 |
| TXT | 纯文本，通用格式 |
| Word | `.docx` 格式，适合打印和交付 |

> 导出内容为当前所选风格的已改编所有章节。

---

## 七、API 接口概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/upload` | 上传小说文件 |
| `POST` | `/api/demo` | 加载示例小说 |
| `GET` | `/api/projects` | 项目列表 |
| `GET` | `/api/projects/{id}` | 项目详情（含章节） |
| `DELETE` | `/api/projects/{id}` | 删除项目 |
| `PUT` | `/api/projects/{id}/style` | 切换改编风格 |
| `POST` | `/api/projects/{id}/adapt-all` | 一键改编全部章节 |
| `POST` | `/api/chapters/{id}/adapt` | 改编单个章节 |
| `GET` | `/api/projects/{id}/export/markdown` | 导出 Markdown |
| `GET` | `/api/projects/{id}/export/txt` | 导出 TXT |
| `GET` | `/api/projects/{id}/export/docx` | 导出 Word |

完整 API 文档：启动后端后访问 `http://localhost:8000/docs`

---

## 八、常见问题

### Q: 改编失败怎么办？

- 检查 `backend/.env` 中的 API Key 是否正确
- 检查 API 账户余额是否充足
- 查看后端终端输出的错误日志
- 章节页面会显示具体错误信息

### Q: 改编结果不理想？

- 调整 `LLM_TEMPERATURE` 参数（降低可提高稳定性）
- 尝试切换 LLM 提供商（不同模型适配效果不同）
- 检查原文章节是否过长（超出 `MAX_CHAPTER_LENGTH` 会被截断）

### Q: 如何清空数据重新开始？

删除 `backend/data/app.db` 文件即可重置数据库：

```bash
# Windows
del backend\data\app.db

# macOS / Linux
rm backend/data/app.db
```

### Q: 端口被占用？

- 后端端口：修改 `backend/run.py` 中的 `port=8000`，同时更新 `frontend/vite.config.ts` 中的代理目标
- 前端端口：修改 `frontend/vite.config.ts` 中的 `server.port`

---

## 九、技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + TailwindCSS 4 + Vite 8 |
| 后端 | Python FastAPI + SQLAlchemy + aiosqlite |
| AI 引擎 | DeepSeek / OpenAI / Anthropic / 通义千问 |
| 数据库 | SQLite（`backend/data/app.db`） |
