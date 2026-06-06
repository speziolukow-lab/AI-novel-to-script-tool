interface DeleteModalProps {
  open: boolean;
  projectTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteModal({ open, projectTitle, onConfirm, onCancel }: DeleteModalProps) {
  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "8px", color: "#1e293b" }}>
          🗑️ 确认删除
        </h3>
        <p style={{ fontSize: "13px", color: "#64748b", marginBottom: "16px", lineHeight: 1.6 }}>
          删除后将无法恢复，包括所有改编剧本和角色数据。
        </p>
        <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            className="btn btn-secondary"
            style={{ padding: "8px 16px", fontSize: "13px" }}
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            className="btn btn-danger"
            style={{ padding: "8px 16px", fontSize: "13px" }}
          >
            确认删除
          </button>
        </div>
      </div>
    </div>
  );
}
