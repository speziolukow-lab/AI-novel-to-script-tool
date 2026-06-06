import { useEffect, useState } from "react";
import { listProjects, deleteProject, type ProjectSummary } from "../api/client";

interface Props {
  onProjectClick: (projectId: string) => void;
}

export function ProjectList({ onProjectClick }: Props) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchProjects = async () => {
    try {
      setError("");
      const data = await listProjects();
      setProjects(data);
    } catch (e: any) {
      setError("加载项目列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDelete = async (id: string, title: string) => {
    if (!confirm(`确定删除项目「${title}」吗？此操作不可撤销。`)) return;
    try {
      await deleteProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch {
      setError("删除失败");
    }
  };

  const statusBadge = (status: string) => {
    const map: Record<string, { text: string; cls: string }> = {
      uploaded: { text: "已上传", cls: "bg-slate-100 text-slate-600" },
      parsing: { text: "解析中", cls: "bg-blue-100 text-blue-600" },
      parsed: { text: "已解析", cls: "bg-blue-100 text-blue-600" },
      adapting: { text: "改编中", cls: "bg-amber-100 text-amber-600" },
      completed: { text: "已完成", cls: "bg-green-100 text-green-600" },
      failed: { text: "失败", cls: "bg-red-100 text-red-600" },
    };
    const info = map[status] || { text: status, cls: "bg-slate-100" };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${info.cls}`}>
        {info.text}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="text-center py-12 text-slate-400">
        <div className="animate-spin h-8 w-8 border-2 border-indigo-400 border-t-transparent rounded-full mx-auto mb-3" />
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-3">{error}</div>
        <button
          onClick={fetchProjects}
          className="text-indigo-600 text-sm hover:underline"
        >
          重试
        </button>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-5xl mb-4">📚</p>
        <p className="text-slate-500 text-lg mb-2">还没有项目</p>
        <p className="text-slate-400 text-sm">
          点击「+ 上传小说」开始你的第一个剧本改编
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-800 mb-6">我的项目</h2>
      <div className="grid gap-3">
        {projects.map((p) => (
          <div
            key={p.id}
            onClick={() => onProjectClick(p.id)}
            className="bg-white rounded-lg border border-slate-200 p-5 hover:border-indigo-300
              hover:shadow-sm transition-all cursor-pointer group"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-slate-800 truncate">
                    {p.title}
                  </h3>
                  {statusBadge(p.status)}
                </div>
                <p className="text-sm text-slate-400">
                  作者：{p.author} · {p.total_chapters} 章
                  {p.status === "completed" && (
                    <> · 已完成 {p.completed_chapters}/{p.total_chapters} 章改编</>
                  )}
                </p>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <span className="text-xs text-slate-400">
                  {new Date(p.created_at).toLocaleDateString("zh-CN")}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(p.id, p.title);
                  }}
                  className="text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 p-1"
                  title="删除"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
