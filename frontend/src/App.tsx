import { useState } from "react";
import { ProjectList } from "./components/ProjectList";
import { UploadNovel } from "./components/UploadNovel";
import { ProjectDetail } from "./components/ProjectDetail";

type Page = "projects" | "upload";

export default function App() {
  const [page, setPage] = useState<Page>("projects");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

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
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <span className="text-2xl">📖</span>
            AI 小说转剧本
          </h1>
          <nav className="flex gap-1">
            <button
              onClick={() => setPage("projects")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                page === "projects"
                  ? "bg-indigo-50 text-indigo-600"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              我的项目
            </button>
            <button
              onClick={() => setPage("upload")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                page === "upload"
                  ? "bg-indigo-50 text-indigo-600"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              + 上传小说
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        {page === "projects" && (
          <ProjectList onProjectClick={handleProjectClick} />
        )}
        {page === "upload" && (
          <UploadNovel onSuccess={handleUploadSuccess} />
        )}
      </main>
    </div>
  );
}
