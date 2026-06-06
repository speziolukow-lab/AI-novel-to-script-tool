import { useEffect, useState } from "react";
import { listProjects, deleteProject, type ProjectSummary } from "../api/client";
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
          <button onClick={onLoadDemo} className="btn btn-outline">
            🎭 加载示例小说
          </button>
          <button onClick={onNavigateUpload} className="btn btn-primary">
            📤 上传小说
          </button>
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
                onClick={() => onProjectClick(p.id)}
              >
                {/* Delete button */}
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
    </div>
  );
}
