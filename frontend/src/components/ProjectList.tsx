import { useEffect, useState } from "react";
import { listProjects, deleteProject, deleteProjectsBatch, type ProjectSummary } from "../api/client";
import { DeleteModal } from "./shared/DeleteModal";
import { useToast } from "./shared/Toast";

interface Props {
  onProjectClick: (projectId: string) => void;
  onLoadDemo: () => void;
  onNavigateUpload: () => void;
}

const STATUS_MAP: Record<string, { text: string; cls: string }> = {
  completed: { text: "✅ 改编完成", cls: "completed" },
  adapting:  { text: "⏳ 改编中",  cls: "adapting" },
  parsed:    { text: "📖 已解析，待改编", cls: "parsed" },
  failed:    { text: "❌ 失败",    cls: "failed" },
};

export function ProjectList({ onProjectClick, onLoadDemo, onNavigateUpload }: Props) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<ProjectSummary | null>(null);
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchConfirmOpen, setBatchConfirmOpen] = useState(false);
  const { toast } = useToast();

  const fetchProjects = async () => {
    try {
      setError("");
      const data = await listProjects();
      setProjects(data);
    } catch {
      setError("加载项目列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteProject(deleteTarget.id);
      setProjects((prev) => prev.filter((p) => p.id !== deleteTarget.id));
      toast("🗑️ 项目已删除");
    } catch {
      setError("删除失败");
    } finally {
      setDeleteTarget(null);
    }
  };

  const toggleProjectSelect = (projectId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
      }
      return next;
    });
  };

  const enterBatchMode = () => {
    setSelectedIds(new Set());
    setBatchMode(true);
  };

  const exitBatchMode = () => {
    setBatchMode(false);
    setSelectedIds(new Set());
    setBatchConfirmOpen(false);
  };

  const handleBatchDelete = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    try {
      await deleteProjectsBatch(ids);
      setProjects((prev) => prev.filter((p) => !selectedIds.has(p.id)));
      toast(`🗑️ 已删除 ${ids.length} 个项目`);
    } catch {
      setError("批量删除失败");
    } finally {
      exitBatchMode();
    }
  };

  // Loading
  if (loading) {
    return (
      <div className="empty-state">
        <div className="spinner" style={{ margin: "0 auto 16px" }} />
        <p style={{ color: "#94a3b8" }}>加载中...</p>
      </div>
    );
  }

  // Error
  if (error) {
    return (
      <div className="empty-state">
        <p style={{ color: "#ef4444", marginBottom: "12px" }}>{error}</p>
        <button onClick={fetchProjects} className="btn btn-outline">
          重试
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Page header */}
      <div className="page-header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#1e293b", display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "28px" }}>🎬</span>
          AI 小说转剧本
        </h1>
        <div style={{ display: "flex", gap: "10px" }}>
          {!batchMode && (
            <>
              <button onClick={enterBatchMode} className="btn btn-outline" style={{ color: "#ef4444", borderColor: "#fecaca" }}>
                🗑️ 批量删除
              </button>
              <button onClick={onLoadDemo} className="btn btn-outline">
                🎭 加载示例小说
              </button>
              <button onClick={onNavigateUpload} className="btn btn-primary">
                📤 上传小说
              </button>
            </>
          )}
          {batchMode && (
            <>
              <span style={{ fontSize: "13px", color: "#ef4444", fontWeight: 600, alignSelf: "center" }}>
                已选 {selectedIds.size} 个项目
              </span>
              <button
                onClick={() => selectedIds.size > 0 && setBatchConfirmOpen(true)}
                disabled={selectedIds.size === 0}
                className="btn btn-primary"
                style={{ background: selectedIds.size === 0 ? "#cbd5e1" : "#ef4444", border: "none" }}
              >
                确认删除
              </button>
              <button onClick={exitBatchMode} className="btn btn-outline">
                取消
              </button>
            </>
          )}
        </div>
      </div>

      {/* Empty state */}
      {projects.length === 0 ? (
        <div className="empty-state">
          <div className="icon">📚</div>
          <h3>还没有项目</h3>
          <p>上传你的小说，或加载示例小说，开始 AI 改编之旅</p>
          <div style={{ display: "flex", gap: "10px", justifyContent: "center", flexWrap: "wrap" }}>
            <button onClick={onNavigateUpload} className="btn btn-primary">
              📤 上传小说
            </button>
            <button onClick={onLoadDemo} className="btn btn-outline">
              🎭 加载示例小说
            </button>
          </div>
        </div>
      ) : (
        /* Project grid */
        <div className="project-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "14px" }}>
          {projects.map((p) => {
            const progressPct =
              p.total_chapters > 0
                ? Math.round((p.completed_chapters / p.total_chapters) * 100)
                : 0;
            const st = STATUS_MAP[p.status] || { text: p.status, cls: "" };

            return (
              <div
                key={p.id}
                className="project-card"
                onClick={() => {
                  if (batchMode) {
                    toggleProjectSelect(p.id);
                  } else {
                    onProjectClick(p.id);
                  }
                }}
                style={batchMode ? { cursor: "pointer", position: "relative" } : {}}
              >
                {/* Batch mode checkbox */}
                {batchMode && (
                  <div
                    style={{
                      position: "absolute", top: "12px", left: "12px", zIndex: 2,
                      width: "20px", height: "20px", borderRadius: "4px",
                      border: selectedIds.has(p.id) ? "2px solid #ef4444" : "2px solid #cbd5e1",
                      background: selectedIds.has(p.id) ? "#ef4444" : "#fff",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      color: "#fff", fontSize: "12px", fontWeight: 700,
                      transition: "120ms ease",
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleProjectSelect(p.id);
                    }}
                  >
                    {selectedIds.has(p.id) ? "✓" : ""}
                  </div>
                )}

                {/* Delete button (hidden in batch mode) */}
                {!batchMode && (
                  <button
                    className="card-delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(p);
                    }}
                    title="删除项目"
                  >
                    ✕
                  </button>
                )}

                <div className="card-title">{p.title}</div>
                <div className="card-author">{p.author}</div>

                <div className="card-meta">
                  <span className={`card-status ${st.cls}`}>{st.text}</span>
                  <span>🎬 影视</span>
                </div>

                {/* Progress bar */}
                <div className="card-progress">
                  <span>{p.completed_chapters} / {p.total_chapters} 章</span>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${progressPct}%` }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Delete modal */}
      <DeleteModal
        open={deleteTarget !== null}
        projectTitle={deleteTarget?.title ?? ""}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Batch delete confirmation modal */}
      {batchConfirmOpen && (
        <div className="modal-overlay" onClick={() => setBatchConfirmOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "8px", color: "#1e293b" }}>
              🗑️ 确认批量删除
            </h3>
            <p style={{ fontSize: "13px", color: "#64748b", marginBottom: "16px", lineHeight: 1.6 }}>
              确定删除已选的 {selectedIds.size} 个项目？删除后将无法恢复，包括所有改编剧本和角色数据。
            </p>
            <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
              <button
                onClick={() => setBatchConfirmOpen(false)}
                className="btn btn-secondary"
                style={{ padding: "8px 16px", fontSize: "13px" }}
              >
                取消
              </button>
              <button
                onClick={handleBatchDelete}
                className="btn btn-danger"
                style={{ padding: "8px 16px", fontSize: "13px" }}
              >
                删除 ({selectedIds.size})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
