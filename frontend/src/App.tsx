import { useState } from "react";
import { ProjectList } from "./components/ProjectList";
import { UploadNovel } from "./components/UploadNovel";
import { ProjectDetail } from "./components/ProjectDetail";
import { ToastProvider, useToast } from "./components/shared/Toast";
import { loadDemo } from "./api/client";

type Page = "projects" | "upload";

function AppInner() {
  const [page, setPage] = useState<Page>("projects");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const { toast } = useToast();

  const handleProjectClick = (projectId: string) => {
    setSelectedProjectId(projectId);
  };

  const handleBack = () => {
    setSelectedProjectId(null);
  };

  const handleUploadSuccess = (projectId: string) => {
    setSelectedProjectId(projectId);
    setPage("projects");
  };

  const handleLoadDemo = async () => {
    toast("🎭 正在从 backend/data/samples/ 加载示例小说…");
    try {
      const result = await loadDemo();
      toast("✅ 示例小说加载完成！正在跳转…");
      setTimeout(() => setSelectedProjectId(result.project_id), 800);
    } catch {
      toast("ℹ️ Demo 端点尚未部署，请先上传小说");
    }
  };

  // Show project detail if one is selected
  if (selectedProjectId) {
    return (
      <ProjectDetail
        projectId={selectedProjectId}
        onBack={handleBack}
      />
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "#f1f5f9" }}>
      {/* Proto banner — dark gradient nav */}
      <header className="proto-banner">
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span className="label">原型</span>
          AI 小说转剧本工具 — 交互原型
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
