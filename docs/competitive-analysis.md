# AI小说转剧本工具 —— 竞品技术实现深度分析

> 调研日期：2026-06-06 | 覆盖产品：10+ 款商业/开源工具

---

## 一、竞品全景图

### 1.1 商业产品矩阵

| 产品 | 开发商 | 核心能力 | 技术路线 |
|------|--------|----------|----------|
| **纳逗Pro** | 爱奇艺 | 小说一键转剧本 + 剧本评估 + 光线/运镜控制 + ~70个专业Agent | 自研奇智大模型 + 多模态模型矩阵(Vidu/海螺/即梦/可灵/Wan) |
| **ADB-PG AI编剧助手** | 阿里云 | GraphRAG + 4Agent协同 + 长记忆 + 10维质量自动评分 | AnalyticDB图引擎 + 向量引擎混合检索 |
| **墨客大模型** | 博采传媒 | 影视剧本/网文/剧本杀全链路生成 | 自研大模型, 浙江省首批"AI+文化"重点模型 |
| **量子探险** | 海豚元沣 | 200万字长篇生成 + 漫剧一键成片(40分钟) + AI消痕 | 未公开 |
| **StoryAI** | 字节跳动(脸萌) | 交互式叙事 + 原创插画 + 分支剧情 | 未公开 |
| **Movie42** | capAI×R42 | 文字→电影分镜/剧本/视觉资产 | 未公开(MVP阶段, 目标2026.03) |

### 1.2 开源项目矩阵

| 项目 | Stars | 技术栈 | Agent架构 | 关键创新 |
|------|-------|--------|-----------|----------|
| **Toonflow** | 4000+ | Node.js+TypeScript+Electron+SQLite, Vercel AI SDK, ONNX | 三层5Agent协作 | Chapter Event Graph + 资产库约束 + 宫格图生成 + 持久化记忆 |
| **AI shotlive** | 新项目 | React 19+Express.js+MySQL/SQLite, 多模型适配器 | 主控Agent + CutOS Agent | 角色定妆照 + 衣橱系统 + AI对话式剪辑 |
| **Openframe** | 活跃 | Web+Desktop, S3/COS/OSS存储 | AI辅助编辑Agent | FCPXML/EDL专业导出 + 人物关系图谱 + 本地/云端存储 |
| **Seedance2-Storyboard** | - | Claude Code + Seedance 2.0 | 单Agent Skill | 四幕结构剧本 + 分镜提示词批量生成 |
| **InfinityCN** | - | 离线优先, 7种AI提供商 | - | 电影化阅读体验 + SFX标注 + BEAT/PAUSE标记 |

### 1.3 工具/Skill类产品

| 产品 | 平台 | 特点 |
|------|------|------|
| **Novel to Script Converter** | Openclaw Skill | 小说→专业剧本(含镜头指导/音效), 四段式节奏结构 |
| **AI Drama Prompt Factory** | Openclaw Skill | 小说→结构化JSON提示词包, 对接Sora/可灵等视频生成 |
| **neoscript** | PyPI v0.1.0 | 多模式创作, Fountain/JSON输出, 连续性检查, 合规扫描 |
| **Novel Master AI** | npm v0.33.9 | IDE内AI写作工作室, MCP/CLI工具, 策划→草稿→修订 |

---

## 二、核心技术实现原理 —— 通用实现模式

所有主流 AI 小说转剧本工具，虽然在产品形态和具体技术选型上各有差异，但底层共享一套高度一致的实现范式。

### 2.1 通用 Pipeline 流程

```
小说输入 → 文本解析 → 故事线提取 → 大纲拆解 → 剧本生成 → 分镜制作 → 视觉/视频生成 → 剪辑导出
```

每一步都是独立的 Pipeline 阶段，有独立的 Agent 或模块负责，中间结果被结构化存储（数据库/JSON），下游步骤读取上游输出作为输入约束。

### 2.2 Multi-Agent 协作架构（核心范式）

这是当前所有产品最核心的架构模式。不同产品对 Agent 的命名和粒度不同，但本质上是同一套角色分工模型：

| Agent 角色 | 职责 | 代表产品 |
|------------|------|----------|
| **故事师/编剧 Agent** | 读取小说原文, 提炼故事线, 识别核心冲突、人物关系、情感走向 | 所有产品必备 |
| **大纲师/策划 Agent** | 将故事线拆解为剧集大纲, 含起承转合、情绪曲线、视觉高光 | Toonflow, 阿里云 |
| **导演/审核 Agent** | 质检剧本质量, 多维度评分, 触发迭代修改 | Toonflow, 阿里云, Co-DIRECT |
| **分镜师/视觉导演 Agent** | 将剧本转为镜头描述, 生成适配多模态模型的 Prompt | Toonflow, 阿里云 |
| **美术/资产 Agent** | 提取角色/场景/道具, 建立视觉资产库, 管理一致性约束 | 纳逗Pro, Toonflow, AI shotlive |

### 2.3 Agent 间的协作机制

核心实现模式是 **Tool Calling（工具调用）驱动**：

1. **主控 Agent（Orchestrator）** 持有全局工具集，不直接生成内容，只做调度
2. **子 Agent** 各持有领域专属工具（如"读取章节"、"保存故事线"、"生成图片提示词"）
3. 子 Agent 通过 Tool Calling 读写数据库，实现结构化数据流转
4. 主控通过 EventEmitter/Socket.IO 向前端推送实时进度

典型代码结构（TypeScript 示例，以 Toonflow 为参考）：

```typescript
// 主控Agent的工具集
private getAllTools() {
  return {
    AI1: "故事师 - 读小说生成故事线",
    AI2: "大纲师 - 据故事线生成大纲",
    director: "导演 - 审核修改",
    getChapter: "获取小说章节",
    getStoryline: "获取/保存故事线",
    saveOutline: "保存大纲",
    generateAssets: "从大纲提取角色/场景/道具"
  };
}
```

### 2.4 数据流设计

所有产品均采用**单向数据流**：

```
小说章节(t_novel) → 故事线(t_storyline) → 大纲(t_outline) → 剧本(t_script) → 资产库(t_assets) → 分镜 → 视频
```

每一步均有独立存储和版本追踪。以 Toonflow 的 6 张核心表为例：

| 表名 | 存储内容 |
|------|----------|
| t_project | 项目信息(名称、类型、风格、画幅) |
| t_novel | 小说章节(原文数据) |
| t_storyline | 故事线(每项目一条) |
| t_outline | 分集大纲(JSON结构化数据) |
| t_script | 剧本(关联大纲) |
| t_assets | 资产库(角色/场景/道具, 带图片提示词) |

### 2.5 Prompt 外置与管理

Toonflow 等成熟项目将所有 Agent 的 System Prompt 存在数据库 `t_prompts` 表中，支持用户自定义，无需改代码即可调整 Agent 行为。这是工业级产品的关键特征。

---

## 三、角色/场景一致性 —— 最大技术挑战的解决方案

长篇小说改编剧本时，角色外貌、场景风格、剧情逻辑的**跨集/跨场景一致性**是所有产品的核心技术难点。目前业界形成了四条主流技术路线：

### 3.1 资产库约束法（Asset Bank Constraint）

**代表产品**：Toonflow, Openframe

**原理**：从大纲/剧本中自动提取角色、场景、道具 → 建立受控资产库 → 下游 Agent **强制使用**资产库中的名称，禁止自由发挥、禁止近义词替换。

**实现要点**：
- LLM 自动提取实体（角色名、地名、关键道具）
- 为每个资产建立唯一 ID 和标准化名称
- 下游 Agent 的 System Prompt 中明确约束"必须使用资产列表中的名称"
- 宫格图技术：同分镜多镜头合成一张图 → 裁剪，天然保证风格统一

### 3.2 视觉参考约束法（Visual Reference Lock）

**代表产品**：AI shotlive, 纳逗Pro

**原理**：先为每个角色生成"定妆照"作为视觉锚点 → 后续生成时注入定妆照作为参考图 → 配合"衣橱系统"提供多套造型。

**实现要点**：
- 角色定妆照（正面/侧面/全身）+ 多套服装造型
- 场景概念图作为环境参考
- 生成时通过 img2img / reference-image 参数注入视觉约束
- VLM（视觉语言模型）校验输出是否与定妆照一致

### 3.3 RAG 检索增强法（Retrieval-Augmented Consistency）

**代表产品**：ViMax, neoscript

**原理**：建立视觉资产向量索引 → 生成第 N 个镜头时，通过语义检索召回第 1~N-1 个镜头的角色视觉特征 → 注入 LLM/VLM 作为上下文约束。

**实现要点**：
- 每次生成后 embed 关键帧 → 存入向量数据库
- 下游生成时 query 相关历史帧作为视觉上下文
- VLM 多模态打分：并行生成多张备选帧 → VLM 评分 → 剔除不一致的

### 3.4 知识图谱法（Character Bible via KG）

**代表产品**：阿里云 ADB-PG AI 编剧助手, E²RAG, Co-DIRECT

**原理**：构建角色/场景/事件知识图谱 → GraphRAG 检索 → 长记忆注入。

**实现要点**：
- 实体子图（角色每个阶段的独立表示）+ 事件子图（时序因果链）+ 二部图映射
- 避免"早期 Hermione"和"晚期 Hermione"被合并为同一节点（E²RAG 的关键创新）
- ADB-PG 的 GraphRAG 支持 5 种检索模式（naive/local/global/hybrid/mix）

### 3.5 四方案对比总结

| 技术路线 | 一致性强度 | 实现复杂度 | 计算成本 | 代表产品 |
|----------|-----------|-----------|---------|---------|
| 资产库约束 | ★★★☆ | 低 | 低 | Toonflow, Openframe |
| 视觉参考约束 | ★★★★ | 中 | 中 | AI shotlive, 纳逗Pro |
| RAG 检索增强 | ★★★★ | 高 | 高 | ViMax, neoscript |
| 知识图谱法 | ★★★★★ | 最高 | 最高 | 阿里云, E²RAG |

---

## 四、GraphRAG 与知识图谱 —— 前沿技术方案

### 4.1 为什么需要 GraphRAG？

传统 RAG（向量检索增强生成）在小说转剧本场景中存在三个核心问题：
1. **上下文理解不足**：向量相似 ≠ 逻辑相关，角色 A 和 B 的对话可能被误匹配
2. **复杂关系难以建模**：人物关系网、事件因果链无法用扁平向量表达
3. **多跳推理困难**："A 是 B 的师父，B 是 C 的父亲"→ 需要多步推理才能得出 A 和 C 的关系

### 4.2 阿里云 ADB-PG GraphRAG 架构

**三阶段处理**：

```
阶段一：索引（Indexing）
  文档 → 知识抽取模型(大模型) → 知识图谱 → 存入ADB-PG图分析引擎

阶段二：检索（Retrieval）
  用户查询 → 提取关键词 → 遍历知识图谱 → 找到相关子图

阶段三：生成（Generation）
  查询 + 子图上下文 → 提交LLM → 生成回复
```

**五大检索模式**：

| 模式 | 策略 | 适用场景 |
|------|------|----------|
| `naive` | 纯向量搜索 | 简单事实查询 |
| `local` | 实体节点检索 | 特定实体相关查询 |
| `global` | 关系边检索 | 跨数据集模式分析 |
| `hybrid` | 实体+关系边联合 | 需要实体细节和关系上下文 |
| `mix`(默认) | 向量匹配+知识图谱融合 | 通用综合查询 |

**性能数据**：相比开源 GraphRAG 方案实现 **20倍性能提升**，采用向量引擎存语义 + 图引擎存逻辑关系的混合存储方案。

### 4.3 E²RAG：实体-事件双图框架（2025 学术前沿）

**核心创新**：避免传统 KG-RAG 将同一角色不同阶段的实体合并为一个节点
- **实体子图**：每个实体提及保持独立（"第1章的天真的爱丽丝"≠"第20章的老练的爱丽丝"）
- **事件子图**：保留时序和因果关系
- **二部图映射**：实体提及 ↔ 参与事件的双向链接
- **ChronoQA 基准**：497 QA pairs 覆盖 9 部小说/剧本

### 4.4 知识图谱在各产品中的应用形态

| 产品 | 图谱类型 | 存储引擎 | 应用场景 |
|------|----------|----------|----------|
| 阿里云 ADB-PG | 属性图 | PostgreSQL图引擎 | 角色关系+场景层级+剧情因果 |
| Toonflow | Chapter Event Graph | SQLite JSON | 章节事件提取+剧本适配 |
| Openframe | 人物关系图谱 | 未公开 | 角色互动可视化 |
| E²RAG(学术) | 实体-事件双图 | Neo4j | 角色演化追踪 |
| Fabula(开源) | 故事世界知识图谱 | Neo4j | Cypher自然语言查询 |

---

## 五、质量控制系统 —— "生成→检测→修复"闭环

### 5.1 质量控制是产品分水岭

爱奇艺官方明确指出："一键生成在专业影视生产领域目前不可行"。质量控制是将 AI 剧本工具从"玩具"升级为"生产工具"的核心分水岭。

### 5.2 阿里云 10 维自动评分体系

阿里云 ADB-PG AI 编剧助手的审核专家 Agent 从 10 个维度自动评分：

| 维度 | 检查内容 |
|------|----------|
| 1. 结构与节奏 | 三幕/四幕是否完整, 节奏是否有拖沓或跳跃 |
| 2. 角色塑造 | 人物弧光是否完整, 性格是否前后一致 |
| 3. 冲突与戏剧性 | 冲突设置是否合理, 张力是否足够 |
| 4. 对话质量 | 台词是否自然, 是否符合角色性格 |
| 5. 视觉叙事 | 是否具备可拍摄性, 视觉化程度如何 |
| 6. 情感共鸣 | 情感线是否动人, 观众代入感如何 |
| 7. 逻辑一致性 | 前后是否矛盾, 时间线是否合理 |
| 8. 主题表达 | 主题是否清晰, 是否贯穿始终 |
| 9. 格式规范 | 是否符合影视工业剧本格式标准 |
| 10. 市场契合度 | 目标受众匹配度, 商业潜力评估 |

评分后自动触发**智能迭代引擎**：低分维度 → 定向重写 → 再次评分 → 直到达标。

### 5.3 Toonflow 的导演审核 Agent

- **导演 Agent** 作为独立的质量守门员
- 可调用 `updateOutline` / `saveStoryline` 工具直接修改输出
- 审核不通过 → 退回上游 Agent 重新生成
- 形成 "故事师生成 → 导演审核 → 大纲师修改 → 导演再审核" 的迭代闭环

### 5.4 纳逗Pro 的剧本评估面板

- 生成后自动给出**多维度量化评分**
- 三幕结构完整性、对话密度、视觉化程度
- **人物互动关系图**：可视化角色关系变化轨迹
- **大场景数量 / 场景复用统计**：帮助制片人预估拍摄周期与成本
- 核心设计理念：**AI 建议但不替代人类决策**

### 5.5 Co-DIRECT 的 Director-in-the-Loop 范式（学术前沿）

- Writer Agent（叙事弧线）+ Actor Agent（上下文对话）+ Critic Agent（一致性评估）
- **人类导演坐在"导演椅"上**，在关键节点做决策
- 本体论知识图谱注入叙事学知识，解决内容同质化

---

## 六、记忆系统 —— 长文本不"失忆"的关键

### 6.1 为什么需要记忆系统？

小说改编剧本是典型的长文本处理场景。一部中等长度的网络小说（100-300万字）远超任何 LLM 的上下文窗口。记忆系统是保证 Agent 在跨章节处理时不丢失角色设定、情节线索和世界观信息的关键。

### 6.2 主流记忆架构对比

| 产品 | 记忆架构 | 技术实现 |
|------|----------|----------|
| **Toonflow** | 本地ONNX向量检索 | 短期消息 + 长期摘要 + 语义召回, HuggingFace Transformers |
| **阿里云 ADB-PG** | 长记忆(LTM) | PostgreSQL 持久化 + GraphRAG 检索 + 角色个性化记忆 |
| **百度Agent引擎** | 双层记忆 | Redis 短期缓存 + Neo4j 长期关系图 |
| **novel-multi-agents** | 记忆宫殿 | 大纲→角色→章节→摘要 分层存储 |
| **纳逗Pro** | 资产主体库 | 美术Agent管理角色/场景的持久化视觉主体 |

### 6.3 记忆系统的核心能力

1. **短期记忆**：当前处理章节的上下文（对话历史、最近事件）
2. **长期记忆**：角色设定、世界观规则、已发生的重大事件
3. **语义召回**：基于向量相似度检索历史相关片段
4. **摘要压缩**：将长文本压缩为结构化摘要，降低上下文占用
5. **增量更新**：新章节处理完后自动更新记忆库

---

## 七、技术栈对比总结

### 7.1 各产品技术选型一览

| 维度 | Toonflow | AI shotlive | Openframe | 阿里云 | 纳逗Pro |
|------|----------|-------------|-----------|--------|---------|
| **后端** | Node.js/Express 5 | Express.js | 未公开 | AnalyticDB PG | 奇智大模型 |
| **前端** | Electron 40 | React 19 | Web+Desktop | Web控制台 | Web平台 |
| **数据库** | SQLite(better-sqlite3) | MySQL/SQLite | S3/COS/OSS | PostgreSQL | 爱奇艺内部 |
| **AI SDK** | Vercel AI SDK | 多模型适配器 | 独立配置 | DTS RAGFlow | 多模态矩阵 |
| **向量检索** | ONNX(本地) | - | - | ADB-PG向量引擎 | 未公开 |
| **图引擎** | SQLite JSON | - | - | ADB-PG图引擎 | 未公开 |
| **实时通信** | Socket.IO | - | - | - | - |
| **图片处理** | Sharp | - | - | - | - |
| **容器化** | Docker | - | - | 阿里云容器 | - |

### 7.2 技术选型趋势

1. **Vercel AI SDK 成为主流选择**：统一的多模型调用接口，TypeScript 原生支持
2. **SQLite 是开源项目的首选**：轻量、零配置、嵌入式，适合桌面端
3. **向量检索正在从云端走向本地**：ONNX/HuggingFace Transformers 支持本地推理
4. **PostgreSQL 是企业级方案的首选**：同时支持向量引擎和图引擎，一套数据库解决多种需求
5. **Prompt 外置化是工业级标志**：将 Agent Prompt 从代码中剥离存入数据库，支持非开发者自定义

---

## 八、差异化机会分析 —— 对本项目的启示

### 8.1 市场空白与切入点

| 空白方向 | 当前状态 | 机会描述 |
|----------|----------|----------|
| **中文短剧格式深度适配** | 多数产品偏通用 | 针对抖音/快手短剧格式（1-3分钟/集, 竖屏, 强钩子）做深度优化 |
| **特定品类深耕** | 缺乏垂类产品 | 如"赘婿逆袭""霸总甜宠"等高频题材的模板化剧本生成 |
| **与国内视频生成生态集成** | 多数对接国外模型 | 深度对接可灵/即梦/Seedance 等国内视频生成模型的 Prompt 优化 |
| **剧本评估/打分系统** | 仅阿里云/纳逗Pro有 | 独立的剧本质量评估工具，面向编剧/制片方的 SaaS 服务 |
| **FCPXML/EDL 专业格式输出** | 仅 Openframe 支持 | 提供标准化的专业后期软件对接能力 |
| **本地化+隐私保护** | 大厂产品依赖云端 | 面向独立创作者/IP 方的本地化部署方案 |

### 8.2 推荐技术路线（MVP 阶段）

```
优先级 P0（核心差异化）：
  ├── 中文小说文本解析（章节识别、对话提取、场景分割）
  ├── 结构化剧本生成（标准剧本格式 + 短剧模板）
  └── 角色/场景资产提取与管理

优先级 P1（体验提升）：
  ├── Multi-Agent 协作架构（故事师 + 编剧 + 导演审核）
  ├── 基础质量评估（结构完整性 + 对话自然度）
  └── 多模型适配（至少支持 DeepSeek/通义千问/GPT-4）

优先级 P2（生态扩展）：
  ├── 分镜提示词生成（对接视频生成模型）
  ├── 向量记忆系统（长文本不"失忆"）
  └── FCPXML/EDL 导出
```

### 8.3 关键技术决策建议

1. **Agent 架构**：采用 Toonflow 已验证的"主控 Orchestrator + 专业化子 Agent + Tool Calling"模式，这是当前最成熟、可参考实现最多的方案
2. **一致性方案**：MVP 阶段优先采用"资产库约束法"（实现简单、成本低、效果可接受），后续迭代再引入 RAG/知识图谱
3. **Prompt 管理**：从 Day 1 就将 Prompt 外置化（存数据库/配置文件），这是工业化和可维护性的基础
4. **数据流设计**：严格单向数据流 + 每阶段独立存储，支持断点续传和版本回溯
5. **模型选型**：文本处理优先 DeepSeek（性价比最优），剧本生成可用 Claude/GPT-4（质量最优），支持灵活切换

---

## 参考来源

- [Toonflow GitHub](https://github.com/HBAI-Ltd/Toonflow-app)
- [AI shotlive GitHub](https://github.com/sorker/ai-shotlive)
- [Openframe GitHub](https://github.com/murongg/openframe)
- [Seedance2-Storyboard-Generator GitHub](https://github.com/liangdabiao/Seedance2-Storyboard-Generator)
- [阿里云 AI 编剧助手官方文档](https://developer.aliyun.com/article/1717944)
- [阿里云 GraphRAG 服务文档](https://www.alibabacloud.com/help/en/analyticdb/analyticdb-for-postgresql/user-guide/use-the-graphrag-service)
- [极客公园：实测纳逗Pro](https://w.geekpark.net/news/363720)
- [新京报：拆解纳逗Pro](https://www.bjnews.com.cn/detail/1777474232168810.html)
- [百度百科：纳逗Pro](https://baike.baidu.com/item/%E7%BA%B3%E9%80%97Pro/67513912)
- [E²RAG 论文 (arXiv 2506.05939)](https://arxiv.org/abs/2506.05939)
- [EventRAG 论文 (ACL 2025)](https://aclanthology.org/2025.acl-long.830.pdf)
- [MovieAgent 论文 (arXiv 2503.07314)](https://arxiv.org/abs/2503.07314)
- [FilmAgent 论文 (arXiv 2501.12909)](https://arxiv.org/abs/2501.12909)
- [Co-DIRECT 论文 (ESWA 2025)](https://www.sciencedirect.com/science/article/abs/pii/S0957417425041867)
- [novel-multi-agents GitHub](https://github.com/QSPBU-LONG/novel-multi-agents)
- [百度 AI Agent 小说创作引擎](https://developer.baidu.com/article/detail.html?id=5550234)
- [Toonflow 架构解析](https://www.e-com-net.com/article/2044970939757682688.htm)
- [Toolify: Novel to Script](https://www.toolify.ai/openclaw-skills/novel-to-script-6799)
- [neoscript PyPI](https://pypi.org/project/neoscript/0.1.0/)
- [InfinityCN GitHub](https://github.com/Pushyanth02/InfinityCN)
