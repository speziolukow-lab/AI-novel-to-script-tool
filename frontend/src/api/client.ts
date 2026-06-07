/**
 * API client for the novel-to-script backend.
 */

const BASE = "/api";

export interface ProjectSummary {
  id: string;
  title: string;
  author: string;
  status: string;
  style: string;
  total_chapters: number;
  completed_chapters: number;
  created_at: string;
}

export interface AlignmentEntry {
  scene: number;
  para_start: number;
  para_end: number;
}

export interface AlignmentData {
  alignment: AlignmentEntry[];
  total_paras: number;
  version: number;
}

export interface CharacterData {
  name: string;
  aliases: string[];
  description: string;
  traits: string[];
  role?: string;
}

export interface AdaptationInfo {
  status: string;
  script_text: string | null;
  error_message: string | null;
  scenes: AlignmentData | null;
  characters: CharacterData[] | null;
}

export interface ChapterInfo {
  id: string;
  chapter_num: number;
  title: string;
  status: string;
  original_text: string | null;
  script_text: string | null;  // legacy backward compat
  scenes: any | null;
  characters: any | null;
  error_message: string | null;
  adaptations: Record<string, AdaptationInfo>;
}

export interface ProjectDetail extends ProjectSummary {
  chapters: ChapterInfo[];
  characters: CharacterInfo[];
}

export interface CharacterInfo {
  id: string;
  name: string;
  aliases: string[];
  description: string;
  traits: string[];
}

export interface UploadResult {
  project_id: string;
  title: string;
  author: string;
  total_chapters: number;
  chapters: Array<{ id: string | null; chapter_num: number; title: string }>;
}

// ── API functions ──────────────────────────────────────────────

export async function uploadNovel(file: File): Promise<UploadResult> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || "Upload failed");
  }

  return res.json();
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const res = await fetch(`${BASE}/projects`);
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  const res = await fetch(`${BASE}/projects/${projectId}`);
  if (!res.ok) throw new Error("Project not found");
  return res.json();
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await fetch(`${BASE}/projects/${projectId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete project");
}

export async function adaptChapter(chapterId: string): Promise<{ chapter_id: string; status: string }> {
  const res = await fetch(`${BASE}/chapters/${chapterId}/adapt`, { method: "POST" });
  if (!res.ok) throw new Error("Adaptation failed");
  return res.json();
}

export async function adaptBatchChapters(
  projectId: string,
  chapterIds: string[],
  style: string = "",
): Promise<{ project_id: string; chapters_queued: number }> {
  const res = await fetch(`${BASE}/projects/${projectId}/adapt-batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chapter_ids: chapterIds, style }),
  });
  if (!res.ok) throw new Error("Batch adaptation failed");
  return res.json();
}

export function exportMarkdownUrl(projectId: string): string {
  return `${BASE}/projects/${projectId}/export/markdown`;
}

export function exportDocxUrl(projectId: string): string {
  return `${BASE}/projects/${projectId}/export/docx`;
}

export function exportTxtUrl(projectId: string): string {
  return `${BASE}/projects/${projectId}/export/txt`;
}

export function exportYamlUrl(projectId: string): string {
  return `${BASE}/projects/${projectId}/export/yaml`;
}

// ── Per-chapter export ────────────────────────────────────────────

export function exportChapterMarkdownUrl(chapterId: string): string {
  return `${BASE}/chapters/${chapterId}/export/markdown`;
}

export function exportChapterDocxUrl(chapterId: string): string {
  return `${BASE}/chapters/${chapterId}/export/docx`;
}

export function exportChapterTxtUrl(chapterId: string): string {
  return `${BASE}/chapters/${chapterId}/export/txt`;
}

export function exportChapterYamlUrl(chapterId: string): string {
  return `${BASE}/chapters/${chapterId}/export/yaml`;
}

export async function loadDemo(): Promise<UploadResult> {
  const res = await fetch(`${BASE}/demo`, { method: "POST" });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || "Demo load failed");
  }
  return res.json();
}

export async function updateStyle(projectId: string, style: string): Promise<void> {
  const res = await fetch(`${BASE}/projects/${projectId}/style`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ style }),
  });
  if (!res.ok) throw new Error("Failed to update style");
}
