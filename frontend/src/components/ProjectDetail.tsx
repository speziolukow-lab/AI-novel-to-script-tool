import { useEffect, useState, useCallback, useRef } from "react";
import {
  getProject,
  adaptChapter,
  adaptBatchChapters,
  updateStyle,
  exportMarkdownUrl,
  exportDocxUrl,
  exportTxtUrl,
  exportYamlUrl,
  exportChapterMarkdownUrl,
  exportChapterDocxUrl,
  exportChapterTxtUrl,
  exportChapterYamlUrl,
} from "../api/client";
import type { ProjectDetail as ProjectDetailType, ChapterInfo, AdaptationInfo } from "../api/client";
import { ScriptViewer } from "./ScriptViewer";
import { useToast } from "./shared/Toast";

interface Props {
  projectId: string;
  onBack: () => void;
}

const STYLE_OPTIONS = [
  { key: "film", label: "🎬 影视剧本" },
  { key: "comic", label: "📖 漫画分镜" },
  { key: "stage", label: "🎭 舞台剧本" },
] as const;

const ADAPT_STAGES = [
  "正在分析章节结构…",
  "正在提取出场人物…",
  "正在生成剧本…",
  "AI 正在处理中…",
];

// ── F11: Quality check ──
interface QualityWarning {
  message: string;
  lines: number[];  // 0-based line indices; empty = global warning
}

function checkQuality(adapt: AdaptationInfo): QualityWarning[] {
  const warnings: QualityWarning[] = [];
  if (!adapt.script_text) return warnings;

  const allLines = adapt.script_text.split("\n");

  // ── Scene count ──
  const sceneMatches = adapt.script_text.match(/第\s*\d+\s*场/g);
  const sceneCount = sceneMatches ? sceneMatches.length : 0;
  if (sceneCount > 0 && sceneCount < 3) {
    warnings.push({
      message: `场景数偏少（仅 ${sceneCount} 场），可能遗漏场景切换`,
      lines: [],
    });
  }

  // ── Dialogue format ──
  const badLineIndices: number[] = [];
  allLines.forEach((line, idx) => {
    const t = line.trim();
    if (!/^\S+?[：:]/.test(t)) return;
    // Exclude structural markers
    if (/^(第\s*\d+\s*[场格幕帧镜页]|[时地人]点[：:]|【|[-─-╿]{2,})/.test(t)) return;
    // Check proper dialogue format
    if (!/^[^\s：:]{1,10}[：:]\s*\S/.test(t)) {
      badLineIndices.push(idx);
    }
  });
  if (badLineIndices.length > 0) {
    warnings.push({
      message: `对话格式不规范：${badLineIndices.length} 处缺少「角色名：」前缀，疑似 LLM 将叙述与对白混淆`,
      lines: badLineIndices,
    });
  }

  // ── Output length ──
  if (adapt.script_text.length < 500) {
    warnings.push({
      message: "产出长度不足原文的 30%，可能 LLM 未完整改编",
      lines: [],
    });
  }

  return warnings;
}

export function ProjectDetail({ projectId, onBack }: Props) {
  const [project, setProject] = useState<ProjectDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeChapterId, setActiveChapterId] = useState<string | null>(null);
  const [adapting, setAdapting] = useState<string | null>(null);
  const [adaptStage, setAdaptStage] = useState(0);
  const [adaptElapsed, setAdaptElapsed] = useState(0);
  const [style, setStyle] = useState("film");
  const [viewMode, setViewMode] = useState<"original" | "script">("script");
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const adaptTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stageTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { toast } = useToast();
  const initialLoadRef = useRef(true);
  const styleLoadedRef = useRef(false);

  // ── Resizable panel widths ──
  const [containerWidth, setContainerWidth] = useState(1800);
  const [leftWidth, setLeftWidth] = useState(260);
  const [rightWidth, setRightWidth] = useState(220);
  const resizing = useRef<"leftEdge" | "left" | "right" | "rightEdge" | null>(null);
  const resizeStartX = useRef(0);
  const resizeStartW = useRef(0);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const side = resizing.current;
      if (!side) return;
      const delta = e.pageX - resizeStartX.current;
      if (side === "leftEdge") {
        // Drag left edge of layout → controls overall container width
        // delta>0 (→) shrinks container, delta<0 (←) widens
        setContainerWidth(Math.min(2200, Math.max(640, resizeStartW.current - delta)));
      } else if (side === "left") {
        setLeftWidth(Math.min(420, Math.max(180, resizeStartW.current + delta)));
      } else if (side === "right") {
        setRightWidth(Math.min(420, Math.max(140, resizeStartW.current - delta)));
      } else {
        // Drag right edge of layout → controls overall container width
        // delta>0 (→) widens container, delta<0 (←) shrinks
        setContainerWidth(Math.min(2200, Math.max(640, resizeStartW.current + delta)));
      }
    };
    const onUp = () => {
      if (resizing.current) {
        resizing.current = null;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  const beginResize = (side: "leftEdge" | "left" | "right" | "rightEdge") => (e: React.MouseEvent) => {
    e.preventDefault();
    resizing.current = side;
    resizeStartX.current = e.pageX;
    if (side === "leftEdge" || side === "rightEdge") {
      resizeStartW.current = containerWidth;
    } else if (side === "left") {
      resizeStartW.current = leftWidth;
    } else {
      resizeStartW.current = rightWidth;
    }
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const fetchProject = useCallback(async () => {
    try {
      const data = await getProject(projectId);
      setProject(data);
      // Only sync style from backend on initial load — avoid
      // overwriting user choice during polling races.
      if (!styleLoadedRef.current && data.style) {
        setStyle(data.style);
        styleLoadedRef.current = true;
      }
      // Only auto-select the first chapter on initial load
      if (initialLoadRef.current && data.chapters.length > 0) {
        setActiveChapterId(data.chapters[0].id);
        initialLoadRef.current = false;
      }
      setError("");
    } catch {
      setError("加载项目失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchProject(); }, [fetchProject]);

  useEffect(() => {
    if (!project || project.status !== "adapting") return;
    const interval = setInterval(fetchProject, 3000);
    return () => clearInterval(interval);
  }, [project?.status, fetchProject]);

  const clearTimers = () => {
    if (adaptTimerRef.current) { clearInterval(adaptTimerRef.current); adaptTimerRef.current = null; }
    if (stageTimerRef.current) { clearInterval(stageTimerRef.current); stageTimerRef.current = null; }
  };

  const startProgress = () => {
    clearTimers();
    setAdaptStage(0); setAdaptElapsed(0);
    adaptTimerRef.current = setInterval(() => setAdaptElapsed((p) => p + 1), 1000);
    stageTimerRef.current = setInterval(() => {
      setAdaptStage((p) => (p >= ADAPT_STAGES.length - 1 ? p : p + 1));
    }, 600);
  };

  const stopProgress = () => { clearTimers(); };
  useEffect(() => () => clearTimers(), []);

  const handleAdaptChapter = async (chapterId: string) => {
    try {
      setAdapting(chapterId);
      startProgress();
      await adaptChapter(chapterId);
      const poll = setInterval(async () => {
        const p = await getProject(projectId);
        setProject(p);
        const ch = p.chapters.find((c) => c.id === chapterId);
        const adaptStatus = ch?.adaptations?.[style]?.status ?? "pending";
        if (adaptStatus === "completed" || adaptStatus === "failed") {
          clearInterval(poll);
          setAdapting(null);
          stopProgress();
          toast(adaptStatus === "completed" ? "✅ 改编完成！" : "❌ 改编失败");
        }
      }, 2000);
    } catch {
      setError("改编失败");
      setAdapting(null);
      stopProgress();
    }
  };

  const handleAdaptBatch = async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    try {
      setAdapting("__batch__");
      setBatchMode(false);
      setSelectedIds(new Set());
      startProgress();
      await adaptBatchChapters(projectId, ids);
      const poll = setInterval(async () => {
        const p = await getProject(projectId);
        setProject(p);
        if (p.status === "completed" || p.status === "failed" || p.status === "parsed") {
          clearInterval(poll);
          setAdapting(null);
          stopProgress();
          fetchProject();
          if (p.status === "completed") toast(`✅ ${ids.length} 个章节改编完成！`);
        }
      }, 2000);
    } catch {
      setError("批量改编失败");
      setAdapting(null);
      stopProgress();
    }
  };

  const toggleChapterSelect = (chapterId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(chapterId)) {
        next.delete(chapterId);
      } else if (next.size < 5) {
        next.add(chapterId);
      }
      return next;
    });
  };

  const handleStyleChange = async (s: string) => {
    setStyle(s);
    try {
      await updateStyle(projectId, s);
      toast(`🎨 风格已切换为「${STYLE_OPTIONS.find((o) => o.key === s)?.label}」`);
    } catch {
      toast("❌ 风格切换失败，请重试");
    }
  };

  const activeChapter = project?.chapters.find((c) => c.id === activeChapterId);
  const activeAdaptation = activeChapter?.adaptations?.[style] ?? {
    status: "pending",
    script_text: null,
    error_message: null,
    scenes: null,
    characters: null,
  } as AdaptationInfo;
  const activeWarnings = activeAdaptation.script_text ? checkQuality(activeAdaptation) : [];
  const scriptHighlightSet = new Set(activeWarnings.flatMap((w) => w.lines));

  // ── Original‑text highlight set (alignment‑based) ──
  // Uses AI-generated alignment data to map script quality warnings
  // back to the original text paragraphs that produced them.
  const originalHighlightSet = (() => {
    const set = new Set<number>();
    if (!activeChapter?.original_text) return set;

    const alignment = activeAdaptation.scenes?.alignment;
    if (!alignment || alignment.length === 0) return set;

    const scriptLines = activeAdaptation.script_text?.split("\n") ?? [];
    const origLines = activeChapter.original_text.split("\n");

    // Build line→scene map: for each script line, determine which scene it belongs to
    const lineToScene = new Map<number, number>();
    let currentScene = -1;
    for (let i = 0; i < scriptLines.length; i++) {
      const m = scriptLines[i].match(/^第\s*(\d+)\s*[场格幕帧镜页]/);
      if (m) {
        currentScene = parseInt(m[1], 10);
      }
      if (currentScene >= 0) {
        lineToScene.set(i, currentScene);
      }
    }

    // For each quality warning line, find its scene → corresponding original paragraphs
    for (const warning of activeWarnings) {
      for (const warnLine of warning.lines) {
        const scene = lineToScene.get(warnLine);
        if (scene === undefined) continue;
        const align = alignment.find((a) => a.scene === scene);
        if (!align) continue;
        for (let p = align.para_start; p <= align.para_end && p < origLines.length; p++) {
          set.add(p);
        }
      }
    }

    return set;
  })();

  // Helper: get adaptation for a chapter + current style
  const getAdaptation = (ch: ChapterInfo): AdaptationInfo =>
    ch.adaptations?.[style] ?? { status: "pending", script_text: null, error_message: null, scenes: null, characters: null };

  // Loading
  if (loading) {
    return (
      <div className="empty-state">
        <div className="spinner" style={{ margin: "0 auto 16px" }} />
        <p style={{ color: "#94a3b8" }}>加载项目...</p>
      </div>
    );
  }

  // Error
  if (error || !project) {
    return (
      <div className="empty-state">
        <p style={{ color: "#ef4444", marginBottom: "12px" }}>{error || "项目不存在"}</p>
        <button onClick={onBack} className="btn btn-outline">返回列表</button>
      </div>
    );
  }

  const statusText = project.status === "completed" ? "✅ 改编完成"
    : project.status === "adapting" ? "⏳ 改编中…"
    : project.status === "parsed" ? "📖 已解析，待改编"
    : `状态：${project.status}`;
  const statusColor = project.status === "completed" ? "#166534"
    : project.status === "adapting" ? "#92400e"
    : "#64748b";

  // Computed layout values for 3-column resizable layout
  const showCharacters = !!(activeChapter && activeAdaptation.characters && activeAdaptation.characters.length > 0);
  const HANDLE_W = 6; // each resize handle width in px
  const handlesW = showCharacters ? HANDLE_W * 4 : HANDLE_W * 2; // edge + inner per side
  const centerWidth = containerWidth - leftWidth - (showCharacters ? rightWidth : 0) - handlesW;

  return (
    <div>
      {/* ── Top bar ── */}
      <div className="detail-topbar">
        <button className="back-btn" onClick={onBack}>←</button>
        <div className="detail-meta">
          <h2>{project.title}</h2>
          <div className="sub">
            {project.author} · {project.total_chapters} 章 ·{" "}
            <span style={{ color: statusColor, fontWeight: 600 }}>{statusText}</span>
          </div>
        </div>

        {/* F8: Style switcher */}
        <div className="style-switcher">
          {STYLE_OPTIONS.map((s) => (
            <button
              key={s.key}
              className={style === s.key ? "active" : ""}
              onClick={() => handleStyleChange(s.key)}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* F6: Export buttons */}
        <div style={{ display: "flex", gap: "4px" }}>
          {(() => {
            const safeTitle = project.title.replace(/ /g, "_").replace(/\//g, "_").slice(0, 50);
            const styleLabel = { film: "影视", comic: "漫画", stage: "舞台" }[project.style] || "剧本";
            return [
              { label: ".md", url: exportMarkdownUrl(project.id), file: `${safeTitle}_全本_${styleLabel}剧本.md` },
              { label: ".txt", url: exportTxtUrl(project.id), file: `${safeTitle}_全本_${styleLabel}剧本.txt` },
              { label: ".docx", url: exportDocxUrl(project.id), file: `${safeTitle}_全本_${styleLabel}剧本.docx` },
              { label: ".yaml", url: exportYamlUrl(project.id), file: `${safeTitle}_全本_${styleLabel}剧本.yaml` },
            ];
          })().map((fmt) => (
            <a
              key={fmt.label}
              href={fmt.url}
              download={fmt.file}
              style={{
                padding: "7px 12px", borderRadius: "6px",
                fontSize: "12px", fontWeight: 600, textDecoration: "none",
                background: "#f8fafc", color: "#64748b",
                border: "1px solid #e2e8f0", transition: "150ms ease",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "#f1f5f9"; e.currentTarget.style.color = "#1e293b"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "#f8fafc"; e.currentTarget.style.color = "#64748b"; }}
            >
              {fmt.label}
            </a>
          ))}
        </div>

        {/* F5: Batch adapt */}
        <button
          className="btn-adapt-all"
          onClick={() => { setBatchMode(true); setSelectedIds(new Set()); }}
          disabled={adapting === "__batch__"}
        >
          {adapting === "__batch__" ? "⏳ 改编中..." : "📋 批量改编"}
        </button>
      </div>

      {/* ── Batch selection modal ── */}
      {batchMode && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 1000,
          background: "rgba(0,0,0,0.35)", display: "flex",
          alignItems: "center", justifyContent: "center",
        }} onClick={() => setBatchMode(false)}>
          <div style={{
            background: "#fff", borderRadius: "12px", padding: "24px",
            width: "420px", maxHeight: "70vh", overflow: "auto",
            boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
          }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "16px" }}>
              📋 批量改编（已选 {selectedIds.size}/5 章）
            </h3>
            <p style={{ margin: "0 0 16px 0", fontSize: "12px", color: "#94a3b8" }}>
              选择需要改编的章节，一次最多 5 章
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginBottom: "20px" }}>
              {project.chapters.map((ch) => {
                const adapt = getAdaptation(ch);
                const isSelected = selectedIds.has(ch.id);
                const isCompleted = adapt.status === "completed";
                const isFull = !isSelected && selectedIds.size >= 5;
                return (
                  <label
                    key={ch.id}
                    style={{
                      display: "flex", alignItems: "center", gap: "10px",
                      padding: "10px 12px", borderRadius: "8px",
                      cursor: isCompleted || isFull ? "not-allowed" : "pointer",
                      opacity: isCompleted ? 0.45 : 1,
                      background: isSelected ? "#f0f9ff" : "#f8fafc",
                      border: isSelected ? "2px solid #0ea5e9" : "1px solid #e2e8f0",
                      transition: "120ms ease",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={isCompleted || isFull}
                      onChange={() => toggleChapterSelect(ch.id)}
                      style={{ accentColor: "#0ea5e9", width: "16px", height: "16px" }}
                    />
                    <span style={{ flex: 1, fontSize: "13px", fontWeight: 500 }}>
                      第{ch.chapter_num}章 {ch.title}
                    </span>
                    {isCompleted && (
                      <span style={{ fontSize: "11px", color: "#16a34a" }}>✅ 已完成</span>
                    )}
                    {adapt.status === "failed" && (
                      <span style={{ fontSize: "11px", color: "#ef4444" }}>❌ 失败</span>
                    )}
                  </label>
                );
              })}
            </div>
            <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
              <button
                onClick={() => { setBatchMode(false); setSelectedIds(new Set()); }}
                style={{
                  padding: "8px 20px", borderRadius: "8px", border: "1px solid #e2e8f0",
                  background: "#fff", color: "#64748b", cursor: "pointer", fontSize: "13px",
                }}
              >
                取消
              </button>
              <button
                onClick={handleAdaptBatch}
                disabled={selectedIds.size === 0}
                style={{
                  padding: "8px 20px", borderRadius: "8px", border: "none",
                  background: selectedIds.size === 0 ? "#cbd5e1" : "#0ea5e9",
                  color: "#fff", cursor: selectedIds.size === 0 ? "not-allowed" : "pointer",
                  fontSize: "13px", fontWeight: 600,
                }}
              >
                确认改编 {selectedIds.size > 0 ? `(${selectedIds.size})` : ""}
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div style={{
          marginBottom: "14px", padding: "12px 16px",
          background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: "8px", color: "#991b1b", fontSize: "13px",
        }}>
          {error}
        </div>
      )}

      {/* ── Three-column resizable layout ── */}
      <div style={{ display: "flex", alignItems: "flex-start", width: containerWidth, margin: "0 auto" }}>
        {/* Resize handle: left edge → controls overall container width */}
        <div
          className="resize-handle resize-handle--edge"
          onMouseDown={beginResize("leftEdge")}
        />

        {/* LEFT: Chapters */}
        <div style={{ width: leftWidth, flexShrink: 0 }}>
          {/* Chapter panel */}
          <div className="chapter-panel" style={{ maxHeight: "calc(100vh - 180px)" }}>
            <div className="chapter-panel-header">
              章节列表
              <span className="count">{project.chapters.length} 章</span>
            </div>
            <div className="chapter-list">
              {project.chapters.map((ch) => {
                const adapt = getAdaptation(ch);
                const w = adapt.script_text ? checkQuality(adapt) : [];
                return (
                  <button
                    key={ch.id}
                    className={`chapter-item ${activeChapterId === ch.id ? "active" : ""}`}
                    onClick={() => setActiveChapterId(ch.id)}
                  >
                    <span className={`status-dot ${
                      adapt.status === "completed" ? "completed" :
                      adapt.status === "adapting" ? "adapting" :
                      adapt.status === "failed" ? "failed" : "pending"
                    }`} />
                    <span className="ch-num">第{ch.chapter_num}章</span>
                    <span className="ch-title">{ch.title}</span>
                    {w.length > 0 && (
                      <span style={{ fontSize: "13px", flexShrink: 0 }} title={`${w.length} 项质量警告`}>⚠️</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Resize handle: chapters ↔ script */}
        <div
          className="resize-handle"
          onMouseDown={beginResize("left")}
        />

        {/* CENTER: Script viewer */}
        <div className="script-panel" style={{ width: centerWidth, flexShrink: 0, maxHeight: "calc(100vh - 180px)", display: "flex", flexDirection: "column" }}>
          {activeChapter ? (
            <>
              {/* Script header */}
              <div className="script-panel-header">
                <h3>第{activeChapter.chapter_num}章 · {activeChapter.title}</h3>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  {/* Original vs Script view toggle */}
                  {activeAdaptation.script_text && activeChapter.original_text && (
                    <div className="style-switcher">
                      <button
                        className={viewMode === "original" ? "active" : ""}
                        onClick={() => setViewMode("original")}
                      >
                        原文
                      </button>
                      <button
                        className={viewMode === "script" ? "active" : ""}
                        onClick={() => setViewMode("script")}
                      >
                        剧本
                      </button>
                    </div>
                  )}
                  {activeAdaptation.status === "completed" ? (
                    <span className="adapt-status done">✅ 已改编</span>
                  ) : activeAdaptation.status === "adapting" ? (
                    <span className="adapt-status active">⏳ 改编中…</span>
                  ) : activeAdaptation.status === "failed" ? (
                    <span className="adapt-status failed">❌ 改编失败</span>
                  ) : null}
                  {/* Always show adapt button unless adapting this specific chapter */}
                  {adapting !== activeChapter.id && (
                    <button
                      className="btn-adapt-one"
                      onClick={() => handleAdaptChapter(activeChapter.id)}
                      disabled={adapting !== null}
                    >
                      改编本章
                    </button>
                  )}
                  {/* Per-chapter export */}
                  {activeAdaptation.status === "completed" && (
                    <div style={{ display: "flex", gap: "3px", marginLeft: "4px" }}>
                      {(() => {
                        const safeTitle = project.title.replace(/ /g, "_").replace(/\//g, "_").slice(0, 50);
                        const styleLabel = { film: "影视", comic: "漫画", stage: "舞台" }[project.style] || "剧本";
                        const chNum = activeChapter.chapter_num;
                        return [
                          { label: ".md", url: exportChapterMarkdownUrl(activeChapter.id), file: `${safeTitle}_第${chNum}章_${styleLabel}剧本.md` },
                          { label: ".txt", url: exportChapterTxtUrl(activeChapter.id), file: `${safeTitle}_第${chNum}章_${styleLabel}剧本.txt` },
                          { label: ".docx", url: exportChapterDocxUrl(activeChapter.id), file: `${safeTitle}_第${chNum}章_${styleLabel}剧本.docx` },
                          { label: ".yaml", url: exportChapterYamlUrl(activeChapter.id), file: `${safeTitle}_第${chNum}章_${styleLabel}剧本.yaml` },
                        ];
                      })().map((fmt) => (
                        <a
                          key={fmt.label}
                          href={fmt.url}
                          download={fmt.file}
                          title={`导出第${activeChapter.chapter_num}章`}
                          style={{
                            padding: "4px 7px", borderRadius: "4px",
                            fontSize: "11px", fontWeight: 600, textDecoration: "none",
                            background: "#f8fafc", color: "#475569",
                            border: "1px solid #e2e8f0",
                          }}
                        >
                          {fmt.label}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* F11: Warning banner */}
              {activeWarnings.length > 0 && activeAdaptation.status === "completed" && (
                <div className="warning-banner">
                  <div className="warn-title">⚠️ 质量检查未通过（{activeWarnings.length} 项）</div>
                  {activeWarnings.map((w, i) => (
                    <div
                      key={i}
                      className={`warn-item${w.lines.length > 0 ? " clickable" : ""}`}
                      onClick={() => {
                        if (w.lines.length > 0) {
                          const el = document.getElementById(`script-line-${w.lines[0]}`);
                          el?.scrollIntoView({ behavior: "smooth", block: "center" });
                        }
                      }}
                      title={w.lines.length > 0 ? "点击定位到第一个问题行" : undefined}
                    >
                      {w.message}
                      {w.lines.length > 0 && (
                        <span style={{ fontSize: "11px", color: "#d97706", marginLeft: "6px" }}>
                          🔍 定位
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Content or progress overlay */}
              {adapting === activeChapter.id ? (
                <div className="adapt-progress-overlay">
                  <div className="spinner" />
                  <div className="adapt-stage-text">{ADAPT_STAGES[adaptStage] || "处理中..."}</div>
                  <div className="adapt-elapsed">
                    已用时间：0:{String(adaptElapsed).padStart(2, "0")}
                  </div>
                </div>
              ) : (
                <div className="script-content">
                  {viewMode === "original" && activeChapter.original_text ? (
                    <ScriptViewer text={activeChapter.original_text} highlightLines={originalHighlightSet} />
                  ) : viewMode === "script" && activeAdaptation.script_text ? (
                    <ScriptViewer text={activeAdaptation.script_text} highlightLines={scriptHighlightSet} />
                  ) : activeAdaptation.status === "adapting" ? (
                    <div style={{ textAlign: "center", padding: "48px 0" }}>
                      <div className="spinner" style={{ margin: "0 auto 12px" }} />
                      <p style={{ color: "#94a3b8", fontSize: "14px" }}>AI 正在改编中...</p>
                    </div>
                  ) : activeAdaptation.status === "failed" ? (
                    <div style={{ textAlign: "center", padding: "48px 0", fontSize: "14px" }}>
                      <div style={{ color: "#ef4444", fontWeight: 600, marginBottom: "12px" }}>
                        ❌ 改编失败，请重试
                      </div>
                      {activeAdaptation.error_message && (
                        <div style={{
                          maxWidth: "500px", margin: "0 auto", padding: "12px 16px",
                          background: "#1e293b", color: "#f1f5f9", borderRadius: "8px",
                          fontSize: "12px", fontFamily: "monospace", textAlign: "left",
                          whiteSpace: "pre-wrap", wordBreak: "break-all",
                        }}>
                          {activeAdaptation.error_message}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{
                      display: "flex", flexDirection: "column",
                      alignItems: "center", justifyContent: "center",
                      height: "200px", color: "#94a3b8",
                      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                      fontSize: "14px",
                    }}>
                      点击「改编本章」开始 AI 改编
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div style={{ padding: "64px 0", textAlign: "center", color: "#94a3b8" }}>
              <p style={{ fontSize: "48px", marginBottom: "12px" }}>📖</p>
              <p style={{ fontSize: "14px" }}>选择一个章节查看剧本</p>
            </div>
          )}
        </div>

        {/* Resize handle: script ↔ characters (only when character panel visible) */}
        {showCharacters && (
          <div
            className="resize-handle"
            onMouseDown={beginResize("right")}
          />
        )}

        {/* RIGHT: Per-chapter character profiles (5-chapter sliding window) */}
        {showCharacters && (
          <div style={{ width: rightWidth, flexShrink: 0 }}>
            <div className="character-panel character-panel--right">
              <div className="character-panel-header">
                🎭 角色档案
                <span style={{ fontSize: "10px", color: "#94a3b8" }}>
                  第{Math.max(1, activeChapter.chapter_num - 2)}-{activeChapter.chapter_num + 2}章
                </span>
              </div>
              <div className="character-list">
                {activeAdaptation.characters.map((ch, i) => (
                  <div key={i} className="character-row">
                    <div className="ch-avatar">{ch.name[0]}</div>
                    <div className="ch-info">
                      <div className="ch-name">
                        {ch.name}
                        {ch.role && (
                          <span style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 400, marginLeft: "4px" }}>
                            {ch.role}
                          </span>
                        )}
                      </div>
                      {ch.description && (
                        <div className="ch-role">{ch.description}</div>
                      )}
                      {ch.traits && ch.traits.length > 0 && (
                        <div className="ch-traits">{ch.traits.join(" · ")}</div>
                      )}
                      {ch.aliases && ch.aliases.length > 0 && (
                        <div className="ch-traits" style={{ color: "#6366f1" }}>
                          aka {ch.aliases.join("、")}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Resize handle: right edge → controls overall container width */}
        {showCharacters && (
          <div
            className="resize-handle resize-handle--edge"
            onMouseDown={beginResize("rightEdge")}
          />
        )}
      </div>
    </div>
  );
}
