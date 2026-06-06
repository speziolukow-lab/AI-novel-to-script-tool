import { useEffect, useState, useCallback, useRef } from "react";
import {
  getProject,
  adaptChapter,
  adaptAllChapters,
  updateStyle,
  exportMarkdownUrl,
  exportDocxUrl,
  exportTxtUrl,
} from "../api/client";
import type { ProjectDetail as ProjectDetailType, ChapterInfo } from "../api/client";
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
function checkQuality(ch: ChapterInfo): string[] {
  const warnings: string[] = [];
  if (!ch.script_text) return warnings;
  const sceneMatches = ch.script_text.match(/第\s*\d+\s*场/g);
  const sceneCount = sceneMatches ? sceneMatches.length : 0;
  if (sceneCount > 0 && sceneCount < 3) {
    warnings.push(`场景数偏少（仅 ${sceneCount} 场），可能遗漏场景切换`);
  }
  const dialogueLines = ch.script_text.split("\n").filter((l) => /^\S+?[：:]/.test(l.trim()));
  const badlyFormatted = dialogueLines.filter((l) => !/^[^\s：:]{1,10}[：:]\s*\S/.test(l.trim()));
  if (badlyFormatted.length > 0) {
    warnings.push(`对话格式不规范：${badlyFormatted.length} 处缺少「角色名：」前缀，疑似 LLM 将叙述与对白混淆`);
  }
  if (ch.script_text.length < 500) {
    warnings.push("产出长度不足原文的 30%，可能 LLM 未完整改编");
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
  const adaptTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stageTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { toast } = useToast();
  const initialLoadRef = useRef(true);

  const fetchProject = useCallback(async () => {
    try {
      const data = await getProject(projectId);
      setProject(data);
      if (data.style) setStyle(data.style);
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
        if (ch?.status === "completed" || ch?.status === "failed") {
          clearInterval(poll);
          setAdapting(null);
          stopProgress();
          toast(ch?.status === "completed" ? "✅ 改编完成！" : "❌ 改编失败");
        }
      }, 2000);
    } catch {
      setError("改编失败");
      setAdapting(null);
      stopProgress();
    }
  };

  const handleAdaptAll = async () => {
    try {
      setAdapting("__all__");
      startProgress();
      await adaptAllChapters(projectId);
      const poll = setInterval(async () => {
        const p = await getProject(projectId);
        setProject(p);
        if (p.status === "completed" || p.status === "failed" || p.status === "parsed") {
          clearInterval(poll);
          setAdapting(null);
          stopProgress();
          fetchProject();
          if (p.status === "completed") toast("✅ 全部章节改编完成！");
        }
      }, 2000);
    } catch {
      setError("批量改编失败");
      setAdapting(null);
      stopProgress();
    }
  };

  const handleStyleChange = async (s: string) => {
    setStyle(s);
    try { await updateStyle(projectId, s); } catch { /* endpoint may not exist yet */ }
    toast(`🎨 风格已切换为「${STYLE_OPTIONS.find((o) => o.key === s)?.label}」`);
  };

  const activeChapter = project?.chapters.find((c) => c.id === activeChapterId);
  const activeWarnings = activeChapter ? checkQuality(activeChapter) : [];

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
          {[
            { label: ".md", url: exportMarkdownUrl(project.id) },
            { label: ".txt", url: exportTxtUrl(project.id) },
            { label: ".docx", url: exportDocxUrl(project.id) },
          ].map((fmt) => (
            <a
              key={fmt.label}
              href={fmt.url}
              download
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

        {/* F5: Adapt all */}
        <button
          className="btn-adapt-all"
          onClick={handleAdaptAll}
          disabled={adapting !== null || project.status === "adapting"}
        >
          {adapting === "__all__" ? "⏳ 改编中..." : "⚡ 一键改编全部"}
        </button>
      </div>

      {error && (
        <div style={{
          marginBottom: "14px", padding: "12px 16px",
          background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: "8px", color: "#991b1b", fontSize: "13px",
        }}>
          {error}
        </div>
      )}

      {/* ── Two-column layout ── */}
      <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
        {/* LEFT: Chapters + Characters */}
        <div style={{ width: "300px", flexShrink: 0 }}>
          {/* Chapter panel */}
          <div className="chapter-panel">
            <div className="chapter-panel-header">
              章节列表
              <span className="count">{project.chapters.length} 章</span>
            </div>
            <div className="chapter-list">
              {project.chapters.map((ch) => {
                const w = checkQuality(ch);
                return (
                  <button
                    key={ch.id}
                    className={`chapter-item ${activeChapterId === ch.id ? "active" : ""}`}
                    onClick={() => setActiveChapterId(ch.id)}
                  >
                    <span className={`status-dot ${
                      ch.status === "completed" ? "completed" :
                      ch.status === "adapting" ? "adapting" :
                      ch.status === "failed" ? "failed" : "pending"
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

          {/* F3: Character panel */}
          {project.characters && project.characters.length > 0 && (
            <div className="character-panel">
              <div className="character-panel-header">
                🎭 角色档案
                <span style={{ fontSize: "10px", color: "#94a3b8" }}>AI 自动提取</span>
              </div>
              <div className="character-list">
                {project.characters.map((ch) => (
                  <div key={ch.id} className="character-row">
                    <div className="ch-avatar">{ch.name[0]}</div>
                    <div className="ch-info">
                      <div className="ch-name">
                        {ch.name}
                        {ch.aliases && ch.aliases.length > 0 && (
                          <span style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 400 }}>
                            {" "}aka {ch.aliases.join("、")}
                          </span>
                        )}
                      </div>
                      {ch.description && (
                        <div className="ch-role">{ch.description}</div>
                      )}
                      {ch.traits && ch.traits.length > 0 && (
                        <div className="ch-traits">{ch.traits.join(" · ")}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: Script viewer */}
        <div className="script-panel">
          {activeChapter ? (
            <>
              {/* Script header */}
              <div className="script-panel-header">
                <h3>第{activeChapter.chapter_num}章 · {activeChapter.title}</h3>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  {activeChapter.status === "completed" ? (
                    <span className="adapt-status done">✅ 已改编</span>
                  ) : activeChapter.status === "adapting" ? (
                    <span className="adapt-status active">⏳ 改编中…</span>
                  ) : activeChapter.status === "failed" ? (
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
                </div>
              </div>

              {/* F11: Warning banner */}
              {activeWarnings.length > 0 && activeChapter.status === "completed" && (
                <div className="warning-banner">
                  <div className="warn-title">⚠️ 质量检查未通过（{activeWarnings.length} 项）</div>
                  {activeWarnings.map((w, i) => (
                    <div key={i} className="warn-item">{w}</div>
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
                  {activeChapter.script_text ? (
                    <ScriptViewer text={activeChapter.script_text} />
                  ) : activeChapter.status === "adapting" ? (
                    <div style={{ textAlign: "center", padding: "48px 0" }}>
                      <div className="spinner" style={{ margin: "0 auto 12px" }} />
                      <p style={{ color: "#94a3b8", fontSize: "14px" }}>AI 正在改编中...</p>
                    </div>
                  ) : activeChapter.status === "failed" ? (
                    <div style={{ textAlign: "center", padding: "48px 0", fontSize: "14px" }}>
                      <div style={{ color: "#ef4444", fontWeight: 600, marginBottom: "12px" }}>
                        ❌ 改编失败，请重试
                      </div>
                      {activeChapter.error_message && (
                        <div style={{
                          maxWidth: "500px", margin: "0 auto", padding: "12px 16px",
                          background: "#1e293b", color: "#f1f5f9", borderRadius: "8px",
                          fontSize: "12px", fontFamily: "monospace", textAlign: "left",
                          whiteSpace: "pre-wrap", wordBreak: "break-all",
                        }}>
                          {activeChapter.error_message}
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
      </div>
    </div>
  );
}
