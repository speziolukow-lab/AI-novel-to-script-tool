import { useEffect, useState, useCallback } from "react";
import {
  getProject,
  adaptChapter,
  adaptAllChapters,
  exportMarkdownUrl,
  exportDocxUrl,
  exportTxtUrl,
} from "../api/client";
import type { ProjectDetail as ProjectDetailType } from "../api/client";
import { ScriptViewer } from "./ScriptViewer";

interface Props {
  projectId: string;
  onBack: () => void;
}

export function ProjectDetail({ projectId, onBack }: Props) {
  const [project, setProject] = useState<ProjectDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeChapterId, setActiveChapterId] = useState<string | null>(null);
  const [adapting, setAdapting] = useState<string | null>(null); // chapter id currently adapting

  const fetchProject = useCallback(async () => {
    try {
      const data = await getProject(projectId);
      setProject(data);
      // Auto-select first chapter
      if (!activeChapterId && data.chapters.length > 0) {
        setActiveChapterId(data.chapters[0].id);
      }
      setError("");
    } catch {
      setError("加载项目失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  // Poll while adapting
  useEffect(() => {
    if (!project || project.status !== "adapting") return;
    const interval = setInterval(fetchProject, 3000);
    return () => clearInterval(interval);
  }, [project?.status, fetchProject]);

  const handleAdaptChapter = async (chapterId: string) => {
    try {
      setAdapting(chapterId);
      await adaptChapter(chapterId);
      // Poll until done
      const poll = setInterval(async () => {
        const p = await getProject(projectId);
        setProject(p);
        const ch = p.chapters.find((c) => c.id === chapterId);
        if (ch?.status === "completed" || ch?.status === "failed") {
          clearInterval(poll);
          setAdapting(null);
        }
      }, 3000);
    } catch {
      setError("改编失败");
      setAdapting(null);
    }
  };

  const handleAdaptAll = async () => {
    try {
      setAdapting("__all__");
      await adaptAllChapters(projectId);
      // Poll
      const poll = setInterval(async () => {
        const p = await getProject(projectId);
        setProject(p);
        if (p.status === "completed" || p.status === "failed" || p.status === "parsed") {
          clearInterval(poll);
          setAdapting(null);
          fetchProject();
        }
      }, 3000);
    } catch {
      setError("批量改编失败");
      setAdapting(null);
    }
  };

  const activeChapter = project?.chapters.find((c) => c.id === activeChapterId);

  if (loading) {
    return (
      <div className="text-center py-16 text-slate-400">
        <div className="animate-spin h-8 w-8 border-2 border-indigo-400 border-t-transparent rounded-full mx-auto mb-3" />
        加载项目...
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="text-center py-16">
        <p className="text-red-500 mb-4">{error || "项目不存在"}</p>
        <button onClick={onBack} className="text-indigo-600 hover:underline">
          返回列表
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Top bar */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={onBack}
          className="p-2 -ml-2 rounded-lg hover:bg-slate-200 text-slate-500 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <h2 className="text-xl font-bold text-slate-800 truncate">{project.title}</h2>
          <p className="text-sm text-slate-400">
            {project.author} · {project.total_chapters} 章
            {" · "}
            {project.status === "completed" ? "✅ 改编完成" :
             project.status === "adapting" ? "⏳ 改编中..." :
             project.status === "parsed" ? "📖 已解析，待改编" :
             `状态：${project.status}`}
          </p>
        </div>
        {/* Export buttons */}
        <div className="flex gap-1">
          <a
            href={exportMarkdownUrl(project.id)}
            className="px-3 py-1.5 text-xs font-medium rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
            download
          >
            .md
          </a>
          <a
            href={exportTxtUrl(project.id)}
            className="px-3 py-1.5 text-xs font-medium rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
            download
          >
            .txt
          </a>
          <a
            href={exportDocxUrl(project.id)}
            className="px-3 py-1.5 text-xs font-medium rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
            download
          >
            .docx
          </a>
        </div>
        {/* Adapt All */}
        <button
          onClick={handleAdaptAll}
          disabled={adapting !== null || project.status === "adapting"}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-indigo-600 text-white
            hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
        >
          {adapting === "__all__" ? "改编中..." : "一键改编全部"}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Two-column layout */}
      <div className="flex gap-6">
        {/* Left: Chapter list */}
        <div className="w-64 shrink-0">
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-600">章节列表</h3>
            </div>
            <div className="max-h-[calc(100vh-240px)] overflow-y-auto">
              {project.chapters.map((ch) => (
                <button
                  key={ch.id}
                  onClick={() => setActiveChapterId(ch.id)}
                  className={`w-full text-left px-4 py-2.5 text-sm border-b border-slate-50
                    transition-colors hover:bg-slate-50
                    ${activeChapterId === ch.id ? "bg-indigo-50 border-l-2 border-l-indigo-500" : ""}`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0
                      ${ch.status === "completed" ? "bg-green-400" :
                        ch.status === "adapting" ? "bg-amber-400 animate-pulse" :
                        ch.status === "failed" ? "bg-red-400" : "bg-slate-300"}`}
                    />
                    <span className="text-slate-700 truncate">
                      第{ch.chapter_num}章 {ch.title}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Script Viewer */}
        <div className="flex-1 min-w-0">
          {activeChapter ? (
            <div className="bg-white rounded-lg border border-slate-200">
              <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50">
                <h3 className="font-semibold text-slate-700 text-sm">
                  第{activeChapter.chapter_num}章 {activeChapter.title}
                </h3>
                <div className="flex items-center gap-2">
                  {activeChapter.status === "completed" ? (
                    <span className="text-xs text-green-600">✅ 已改编</span>
                  ) : activeChapter.status === "adapting" ? (
                    <span className="text-xs text-amber-600">⏳ 改编中...</span>
                  ) : activeChapter.status === "failed" ? (
                    <span className="text-xs text-red-500">❌ 改编失败</span>
                  ) : (
                    <button
                      onClick={() => handleAdaptChapter(activeChapter.id)}
                      disabled={adapting !== null}
                      className="px-3 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-600
                        hover:bg-indigo-100 disabled:opacity-50 transition-colors"
                    >
                      改编本章
                    </button>
                  )}
                </div>
              </div>
              <div className="p-5 max-h-[calc(100vh-300px)] overflow-y-auto">
                {activeChapter.script_text ? (
                  <ScriptViewer text={activeChapter.script_text} />
                ) : activeChapter.status === "adapting" ? (
                  <div className="text-center py-12">
                    <div className="animate-spin h-6 w-6 border-2 border-indigo-400 border-t-transparent rounded-full mx-auto mb-3" />
                    <p className="text-sm text-slate-400">AI 正在改编中...</p>
                  </div>
                ) : activeChapter.status === "failed" ? (
                  <div className="text-center py-12 text-red-400 text-sm">
                    改编失败，请重试
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <p className="text-4xl mb-3">📝</p>
                    <p className="text-slate-400 text-sm mb-3">
                      点击「改编本章」开始 AI 改编
                    </p>
                    <button
                      onClick={() => handleAdaptChapter(activeChapter.id)}
                      disabled={adapting !== null}
                      className="px-4 py-2 rounded-lg text-sm font-medium bg-indigo-600 text-white
                        hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                    >
                      开始改编
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-slate-200 p-12 text-center text-slate-400">
              <p className="text-4xl mb-3">📖</p>
              <p>选择一个章节查看剧本</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
