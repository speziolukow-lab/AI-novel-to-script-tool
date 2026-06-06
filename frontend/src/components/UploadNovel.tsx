import { useState, useRef } from "react";
import { uploadNovel } from "../api/client";
import { useToast } from "./shared/Toast";

interface Props {
  onSuccess: (projectId: string) => void;
  onBack: () => void;
}

const UPLOAD_STAGES = [
  "正在保存文件…",
  "正在解析编码 (UTF-8/GBK)…",
  "正在识别章节边界…",
  "正在提取标题与作者信息…",
  "✅ 解析完成！正在跳转…",
];

export function UploadNovel({ onSuccess, onBack }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState(-1);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

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

    let stageIdx = 0;
    setUploadStage(stageIdx);
    const stageInterval = setInterval(() => {
      stageIdx++;
      if (stageIdx < UPLOAD_STAGES.length - 1) {
        setUploadStage(stageIdx);
      }
    }, 800);

    try {
      const result = await uploadNovel(file);
      clearInterval(stageInterval);
      setUploadStage(UPLOAD_STAGES.length - 1);
      toast("✅ 解析完成！共识别 " + result.total_chapters + " 章");
      setTimeout(() => {
        setUploading(false);
        setUploadStage(-1);
        onSuccess(result.project_id);
      }, 600);
    } catch (e: any) {
      clearInterval(stageInterval);
      setUploadStage(-1);
      setError(e.message || "上传失败，请重试");
      setUploading(false);
    }
  };

  return (
    <div>
      {/* Back link */}
      <button
        onClick={() => onBack()}
        style={{
          display: "inline-flex", alignItems: "center", gap: "6px",
          color: "#64748b", fontSize: "14px", cursor: "pointer",
          border: "none", background: "none", marginBottom: "20px", padding: "4px 0",
        }}
        onMouseEnter={(e) => { e.currentTarget.style.color = "#6366f1"; }}
        onMouseLeave={(e) => { e.currentTarget.style.color = "#64748b"; }}
      >
        ← 返回项目列表
      </button>

      <div style={{ maxWidth: "720px", margin: "0 auto", position: "relative" }}>
        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
          onClick={() => fileRef.current?.click()}
          className={`drop-zone ${dragOver ? "drag-over" : ""}`}
          style={file ? { background: "#f0fdf4", borderColor: "#86efac" } : undefined}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.epub"
            style={{ display: "none" }}
            onChange={(e) => handleFile(e.target.files?.[0] || null)}
          />
          {file ? (
            <div>
              <p style={{ fontSize: "48px", marginBottom: "12px" }}>📄</p>
              <p style={{ fontSize: "16px", fontWeight: 700, color: "#1e293b", marginBottom: "4px" }}>
                {file.name}
              </p>
              <p style={{ fontSize: "13px", color: "#64748b" }}>
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div>
              <div className="icon">📁</div>
              <h3>拖拽小说文件到此处，或点击选择</h3>
              <p>支持 .txt / .epub 格式，最大 50MB</p>
            </div>
          )}
        </div>

        {/* Upload progress */}
        {uploading && (
          <div className="upload-progress">
            <div className="filename">{file?.name}</div>
            <div className="stage">{UPLOAD_STAGES[uploadStage] || "处理中..."}</div>
            <div className="progress-track">
              <div className="progress-indeterminate" />
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{
            marginTop: "16px", padding: "12px 16px",
            background: "#fef2f2", border: "1px solid #fecaca",
            borderRadius: "8px", color: "#991b1b", fontSize: "13px",
          }}>
            {error}
          </div>
        )}

        {/* Submit button */}
        <button
          disabled={!file || uploading}
          onClick={handleSubmit}
          className="btn btn-primary"
          style={{ marginTop: "24px", width: "100%", justifyContent: "center", padding: "12px" }}
        >
          {uploading ? (
            <>
              <div className="spinner" style={{ width: "16px", height: "16px", borderWidth: "2px", margin: "0" }} />
              解析中...
            </>
          ) : (
            "开始解析"
          )}
        </button>

        {/* Info cards row */}
        <div className="upload-info-row">
          {[
            { icon: "📄", title: "支持格式", desc: ".txt / .epub\n最大 50MB" },
            { icon: "🔤", title: "编码兼容", desc: "UTF-8 / GBK\n自动检测编码" },
            { icon: "📑", title: "章节识别", desc: "「第X章」「Chapter X」\n序章 / 楔子 / 尾声" },
          ].map((card) => (
            <div key={card.title} className="upload-info-card">
              <div className="info-icon">{card.icon}</div>
              <div className="info-title">{card.title}</div>
              <div className="info-desc" style={{ whiteSpace: "pre-line" }}>{card.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
