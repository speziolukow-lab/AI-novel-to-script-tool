# 剧本 YAML Schema 设计文档

## 一、概述

本文档定义 AI 小说转剧本工具输出的结构化剧本 YAML Schema。该 Schema 是 AI 的主要输出格式——AI 直接生成结构化 JSON，后端再将其渲染为散文格式文本供前端展示。结构化数据便于程序化处理、版本管理、专业工具导入和二次编辑。

## 二、Schema 定义

### 2.1 顶层结构

```yaml
# 剧本 YAML Schema v3.0
project:
  title: string         # 项目/小说标题
  author: string        # 原著作者
  style: enum           # 改编风格：film | comic | stage
  total_chapters: int   # 总章节数
  generated_at: string  # 生成时间（ISO 8601 格式）

chapters:
  - chapter_num: int    # 章节序号（从 1 开始）
    title: string       # 章节标题
    scenes: Scene[]     # 场景列表
```

### 2.2 场景（Scene）

```yaml
scene_num: int                      # 场景序号（从 1 开始，跨章节递增）
time: string | null                 # 时间描述（如 "黄昏"、"深夜"）
location: string | null             # 地点描述（如 "城主府大厅"）
characters: string[]                # 出场人物列表
stage_directions: StageDirection[]  # 舞台指示列表（含文本 + 穿插位置）
dialogues: Dialogue[]               # 对白列表
```

### 2.2.1 舞台指示（StageDirection）

```yaml
text: string       # 舞台指示文本（环境、动作、心理描写）
position: int      # 插入位置：0=第一条对话前，1=第一条后/第二条前，以此类推
```

> **v3.0 变更**: `stage_directions` 从 `string[]` 改为 `StageDirection[]` 对象数组，支持按原著顺序将舞台指示穿插到对话之间，而非全部堆积在场景开头。

### 2.3 对白（Dialogue）

```yaml
character: string             # 说话角色名
line: string                  # 对白内容
parenthetical: string | null  # 演员指示（括号内的表演指导），如 "冷冷地"、"笑"
```

### 2.4 完整类型定义

| 字段路径 | 类型 | 必填 | 说明 |
|----------|------|------|------|
| `project.title` | `string` | ✓ | 小说标题 |
| `project.author` | `string` | ✓ | 原著作者 |
| `project.style` | `enum("film"\|"comic"\|"stage")` | ✓ | 改编风格 |
| `project.total_chapters` | `int` | ✓ | 总章节数 |
| `project.generated_at` | `string` | ✓ | 生成时间（ISO 8601） |
| `chapters[].chapter_num` | `int` | ✓ | 章节序号 |
| `chapters[].title` | `string` | ✓ | 章节标题 |
| `chapters[].scenes` | `Scene[]` | ✓ | 场景列表 |
| `scenes[].scene_num` | `int` | ✓ | 场景序号 |
| `scenes[].time` | `string \| null` | ✓ | 时间 |
| `scenes[].location` | `string \| null` | ✓ | 地点 |
| `scenes[].characters` | `string[]` | ✓ | 出场人物 |
| `scenes[].stage_directions` | `StageDirection[]` | ✓ | 舞台指示（v3.0: 对象数组，含 text + position） |
| `scenes[].stage_directions[].text` | `string` | ✓ | 舞台指示文本 |
| `scenes[].stage_directions[].position` | `int` | ✓ | 插入位置（0=第一条对话前） |
| `scenes[].dialogues` | `Dialogue[]` | ✓ | 对白列表 |
| `dialogues[].character` | `string` | ✓ | 说话角色名 |
| `dialogues[].line` | `string` | ✓ | 对白内容 |
| `dialogues[].parenthetical` | `string \| null` | ✓ | 演员指示 |

## 三、完整示例

以下是一章两场剧本的完整 YAML 输出：

```yaml
project:
  title: "斗破苍穹"
  author: "天蚕土豆"
  style: "film"
  total_chapters: 3
  generated_at: "2026-06-06T12:00:00"

chapters:
  - chapter_num: 1
    title: "陨落的天才"
    scenes:
      - scene_num: 1
        time: "黄昏"
        location: "萧家演武场"
        characters:
          - "萧炎"
          - "萧宁"
          - "萧战"
        stage_directions:
          - text: "演武场上尘土飞扬，数十名少年正在修炼"
            position: 0
          - text: "萧炎站在角落，手中的木剑无力地挥舞着"
            position: 0
        dialogues:
          - character: "萧宁"
            line: "这不是我们萧家的'天才'吗？怎么连最基本的剑法都使不出来了？"
            parenthetical: "讥讽地"
          - character: "萧炎"
            line: "你……！"
            parenthetical: "握紧拳头"
      - scene_num: 2
        time: "深夜"
        location: "萧炎房间"
        characters:
          - "萧炎"
          - "药老"
        stage_directions:
          - text: "月光透过窗棂洒进房间，萧炎盘膝坐在床上"
            position: 0
          - text: "手指上的戒指突然发出一道微光"
            position: 1
        dialogues:
          - character: "萧炎"
            line: "三年了……难道我真的就这样变成一个废人了吗？"
            parenthetical: "喃喃自语"
          - character: "药老"
            line: "小家伙，别这么急着放弃。"
            parenthetical: "苍老的声音从戒指中传出"
```

## 四、设计原因说明

### 4.1 层级化结构（Project → Chapters → Scenes → Dialogues）

**设计决策**：采用四层嵌套结构而非扁平化列表。

**原因**：
- **自然映射**：小说本身具有"章"的概念，剧本输出保留这一层级有助于作者对照原文进行逐章修订
- **导航友好**：在 YAML 编辑器和脚本处理工具中，层级化结构更容易进行代码折叠和章节跳转
- **增量处理**：按章组织使得大长篇（数百章）的 YAML 输出可以按章拆分、独立管理，避免单文件过大
- **上下文关联**：章节标题作为结构锚点，便于理解每个场景在原作中的位置

### 4.2 Scene 独立为顶层对象

**设计决策**：将"场"（Scene）作为剧本的基本单元，而非用行内分隔符。

**原因**：
- **专业工具兼容**：专业剧本软件（如 Final Draft、Celtx）以"场"为单位管理。结构化 Scene 可被二次开发导入这些工具
- **精确检索**：可按 `scene_num`、`location`、`characters` 等字段精确查询特定场景
- **AI 精度提升**：让 LLM 以结构化 JSON 输出每个场景，比要求它输出整个剧本的 YAML 更可靠（单场景上下文更短，格式错误更少）

### 4.3 parenthetical 独立字段

**设计决策**：将对白中的"演员指示"（括号内容）单独提取为 `parenthetical` 字段，而非嵌入 `line` 中。

**原因**：
- **结构化编辑**：演员指示承载着导演和演员关心的表演信息。将其与对白分离，方便表演指导的独立审阅和修改
- **格式转换**：当需要输出为其他格式（如 Final Draft 的 `.fdx`）时，`parenthetical` 对应 `<Parenthetical>` 标签，`line` 对应 `<Dialogue>` 标签
- **人机可读**：人类阅读时不会被括号打断；机器处理时可直接判断 `if dialogue.parenthetical` 来添加格式
- **国际化**：不同语言的剧本格式对演员指示的括号要求不同（中文用（），英文用 ( )），分离后可根据输出目标调整

### 4.4 stage_directions 使用 {text, position} 对象数组

**设计决策**：`stage_directions` 从 `string[]` 改为 `{text: string, position: int}[]` 对象数组。`position` 字段指定舞台指示在对话序列中的插入位置（0=第一条对话前，1=第一条对话后/第二条对话前，以此类推）。

**原因**：
- **精确穿插**：原著中舞台指示（动作描写、环境描写）通常发生在特定对话之间。例如原文在角色 A 说完后描写 B 的脸色变化，这个描写就应该出现在 A 的对话后、B 的对话前。简单的交替渲染（方向→对话→方向→对话）无法精准匹配这种复杂的穿插
- **向后兼容**：旧格式的字符串数组被自动转换为 `{text, position: 0}`，已有数据不会报错
- **批量操作保留**：依然可以一次性提取所有舞台指示（忽略 position），方便批量分析
- **可组合性**：渲染器按 position 排序后穿插到对话之间：

```python
# 按 position 分组 → 穿插渲染
dirs_by_pos = defaultdict(list)
for d in stage_directions:
    dirs_by_pos[d["position"]].append(d["text"])

# position 0: 在第一条对话前
for text in dirs_by_pos[0]:
    print(text)
# 交替输出第 i 条对话 → position i+1 的方向
for i, dialogue in enumerate(dialogues):
    print(f"{dialogue['character']}：{dialogue['line']}")
    for text in dirs_by_pos[i + 1]:
        print(text)
```

### 4.5 Flat characters 列表

**设计决策**：`characters` 为每场的出场人物平面列表，不含角色档案信息。

**原因**：
- **数据分离**：角色详情（性格、别名、关系）已在系统的角色提取模块中独立管理，YAML 中的 `characters` 只需标明"谁在这场出现"
- **快速检查**：剧组人员可根据 `characters` 快速确认某场戏需要的演员
- **避免冗余**：同一角色在多场出现，如果每场都内嵌完整的角色档案会导致 YAML 体积膨胀

### 4.6 缺失值用 null 表示

**设计决策**：`time`、`location`、`parenthetical` 等可选字段缺失时使用 `null`。

**原因**：
- **Schema 一致性**：所有场景具有相同的字段集合，不会因省略字段导致下游解析器报 KeyError
- **语义明确**：`null` 明确表示"无此信息"，区别于空字符串 `""`（可能有但未提取到）
- **工具链兼容**：JSON/YAML 序列化/反序列化直接支持 null，无需额外的默认值处理

## 五、与散文格式的关系

| 维度 | 散文格式（渲染输出） | YAML 格式（AI 主输出） |
|------|-------------------|-------------------|
| 用途 | 前端展示、人工阅读 | 程序处理、专业工具导入 |
| 结构 | 自由文本 + 约定格式标记 | 严格 Schema 定义 |
| 可解析性 | 需要正则匹配 | 标准 YAML 解析器 |
| 编辑性 | 直接文本编辑 | 结构化编辑 |
| 体积 | 较小（无元数据） | 较大（含完整元数据） |

两种格式在系统中**共存**：
- AI 直接输出结构化 JSON，存储在 `scenes.structured_scenes` 字段，作为数据源
- 后端通过 `structured_scenes_to_prose()` 将 JSON 渲染为散文格式，存入 `script_text`，前端 ScriptViewer 用于展示

## 六、扩展性设计

### 6.1 版本号管理

`Adaptation.scenes.version` 字段当前为 `2`（v2: 引入 structured_scenes；v3.0: stage_directions 改为对象数组），未来 Schema 变更时递增版本号，确保向后兼容。

### 6.2 预留字段

以下字段已在设计中预留空间，可在后续版本中添加：

- `Scene.duration` — 预估时长（分钟），用于影视拍摄排期
- `Scene.mood` — 场景情绪标签（如 "紧张"、"温馨"）
- `Dialogue.tone` — 语气标注（如 "愤怒"、"调侃"）
- `Scene.camera_notes` — 镜头建议（电影/漫画风格专属）
- `Scene.transition` — 转场方式（如 "淡入"、"切"）

### 6.3 风格适配

当前 Schema 为三种风格（film / comic / stage）共用。如果某个风格需要专属字段，可采用以下方式：

```yaml
scenes:
  - scene_num: 1
    time: "黄昏"
    ...
    style_specific:
      film:
        camera_suggestion: "中景，45度角"
      comic:
        panel_layout: "2x3 六格"
        page: 1
```

## 七、参考

- YAML 1.2 规范：https://yaml.org/spec/1.2/spec.html
- Final Draft XML Schema：行业标准剧本格式参考
- 本项目整体架构：`docs/technical-architecture.md`
