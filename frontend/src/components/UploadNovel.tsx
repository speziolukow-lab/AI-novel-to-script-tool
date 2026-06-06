import { useState, useRef } from "react";
import { uploadNovel } from "../api/client";

interface Props {
  onSuccess: (projectId: string) => void;
}

export function UploadNovel({ onSuccess }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File | null) => {
    if (!f) return;
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (ext !== "txt" && ext !== "epub") {
      setError("仅支持 .txt 或 .epub 格式的小说文件");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setError("文件大小不能超过 50MB");
      return;
    }
    setFile(f);
    setError("");
  };

  const handleSubmit = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const result = await uploadNovel(file);
      onSuccess(result.project_id);
    } catch (e: any) {
      setError(e.message || "上传失败，请重试");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto">
      <h2 className="text-2xl font-bold text-slate-800 mb-2">上传小说</h2>
      <p className="text-slate-500 mb-6">
        支持 .txt 和 .epub 格式，最大 50MB。AI 将自动识别章节并改编为剧本。
      </p>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFile(e.dataTransfer.files[0]);
        }}
        onClick={() => fileRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
          ${dragOver ? "border-indigo-400 bg-indigo-50" : "border-slate-300 hover:border-indigo-300"}
          ${file ? "bg-green-50 border-green-300" : ""}`}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.epub"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] || null)}
        />
        {file ? (
          <div>
            <p className="text-4xl mb-3">📄</p>
            <p className="text-lg font-medium text-slate-700">{file.name}</p>
            <p className="text-sm text-slate-400 mt-1">
              {(file.size / 1024).toFixed(1)} KB
            </p>
          </div>
        ) : (
          <div>
            <p className="text-4xl mb-3">📁</p>
            <p className="text-slate-600 font-medium">
              拖拽小说文件到此处，或点击选择
            </p>
            <p className="text-sm text-slate-400 mt-2">.txt / .epub</p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Submit */}
      <button
        disabled={!file || uploading}
        onClick={handleSubmit}
        className="mt-6 w-full py-3 rounded-lg font-medium text-white transition-colors
          bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
      >
        {uploading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12" cy="12" r="10"
                stroke="currentColor" strokeWidth="4" fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            解析中...
          </span>
        ) : (
          "开始解析"
        )}
      </button>
    </div>
  );
}
