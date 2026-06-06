import { useState } from "react";
import { ProjectList } from "./components/ProjectList";
import { UploadNovel } from "./components/UploadNovel";
import { ProjectDetail } from "./components/ProjectDetail";
import { ToastProvider, useToast } from "./components/shared/Toast";
import { loadDemo } from "./api/client";

type Page = "projects" | "upload" | "detail";

function AppInner() {
  const [page, setPage] = useState<Page>("projects");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const { toast } = useToast();

  const handleProjectClick = (projectId: string) => {
    setSelectedProjectId(projectId);
    setPage("detail");
  };

  const handleBack = () => {
    setSelectedProjectId(null);
    setPage("projects");
  };

  const handleUploadSuccess = (projectId: string) => {
    setSelectedProjectId(projectId);
    setPage("detail");
  };

  const handleLoadDemo = async () => {
    toast("🎭 正在从 backend/data/samples/ 加载示例小说…");
    try {
      const result = await loadDemo();
      toast("✅ 示例小说加载完成！正在跳转…");
      setTimeout(() => {
        setSelectedProjectId(result.project_id);
        setPage("detail");
      }, 800);
    } catch {
      toast("ℹ️ Demo 端点尚未部署，请先上传小说");
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "#f1f5f9" }}>
      {/* Proto banner — dark gradient nav */}
      <header className="proto-banner">
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          🎬 AI 小说转剧本工具
        </div>
        <nav style={{ display: "flex", gap: "4px" }}>
          <button
            onClick={() => setPage("projects")}
            style={{
              padding: "6px 16px",
              border: page === "projects"
                ? "1px solid #6366f1"
                : "1px solid rgba(255,255,255,.2)",
              background: page === "projects" ? "#6366f1" : "transparent",
              color: page === "projects" ? "#fff" : "#94a3b8",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "13px",
              transition: "150ms ease",
            }}
            onMouseEnter={(e) => {
              if (page !== "projects") {
                e.currentTarget.style.color = "#fff";
                e.currentTarget.style.borderColor = "rgba(255,255,255,.5)";
              }
            }}
            onMouseLeave={(e) => {
              if (page !== "projects") {
                e.currentTarget.style.color = "#94a3b8";
                e.currentTarget.style.borderColor = "rgba(255,255,255,.2)";
              }
            }}
          >
            🏠 项目列表
          </button>
          <button
            onClick={() => setPage("upload")}
            style={{
              padding: "6px 16px",
              border: page === "upload"
                ? "1px solid #6366f1"
                : "1px solid rgba(255,255,255,.2)",
              background: page === "upload" ? "#6366f1" : "transparent",
              color: page === "upload" ? "#fff" : "#94a3b8",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "13px",
              transition: "150ms ease",
            }}
            onMouseEnter={(e) => {
              if (page !== "upload") {
                e.currentTarget.style.color = "#fff";
                e.currentTarget.style.borderColor = "rgba(255,255,255,.5)";
              }
            }}
            onMouseLeave={(e) => {
              if (page !== "upload") {
                e.currentTarget.style.color = "#94a3b8";
                e.currentTarget.style.borderColor = "rgba(255,255,255,.2)";
              }
            }}
          >
            📤 上传小说
          </button>
          <button
            onClick={() => {
              if (selectedProjectId) {
                setPage("detail");
              } else {
                toast("请先从项目列表中选择一个项目");
              }
            }}
            style={{
              padding: "6px 16px",
              border: page === "detail" && selectedProjectId
                ? "1px solid #6366f1"
                : "1px solid rgba(255,255,255,.2)",
              background: page === "detail" && selectedProjectId ? "#6366f1" : "transparent",
              color: page === "detail" && selectedProjectId ? "#fff" : "#94a3b8",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "13px",
              transition: "150ms ease",
            }}
            onMouseEnter={(e) => {
              if (!(page === "detail" && selectedProjectId)) {
                e.currentTarget.style.color = "#fff";
                e.currentTarget.style.borderColor = "rgba(255,255,255,.5)";
              }
            }}
            onMouseLeave={(e) => {
              if (!(page === "detail" && selectedProjectId)) {
                e.currentTarget.style.color = "#94a3b8";
                e.currentTarget.style.borderColor = "rgba(255,255,255,.2)";
              }
            }}
          >
            📖 项目详情
          </button>
        </nav>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: "1280px", margin: "0 auto", padding: "16px 24px" }}>
        {page === "projects" && (
          <ProjectList
            onProjectClick={handleProjectClick}
            onLoadDemo={handleLoadDemo}
            onNavigateUpload={() => setPage("upload")}
          />
        )}
        {page === "upload" && (
          <UploadNovel onSuccess={handleUploadSuccess} />
        )}
        {page === "detail" && selectedProjectId && (
          <ProjectDetail
            projectId={selectedProjectId}
            onBack={handleBack}
          />
        )}
        {page === "detail" && !selectedProjectId && (
          <div className="empty-state">
            <p style={{ fontSize: "48px", marginBottom: "12px" }}>📖</p>
            <p style={{ color: "#94a3b8", marginBottom: "12px" }}>请先从项目列表中选择一个项目</p>
            <button className="btn btn-primary" onClick={() => setPage("projects")}>
              去项目列表
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppInner />
    </ToastProvider>
  );
}
