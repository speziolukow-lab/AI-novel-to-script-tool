/**
 * Script viewer with syntax highlighting matching prototype design.
 */
export function ScriptViewer({ text }: { text: string }) {
  const lines = text.split("\n");

  return (
    <>
      {lines.map((line, i) => {
        const trimmed = line.trim();

        // Scene header: 第 X 场
        if (/^第\s*\d+\s*场/.test(trimmed)) {
          return (
            <span key={i} className="scene-title" style={{ display: "block" }}>
              {line}
            </span>
          );
        }

        // Metadata: 时间/地点/人物
        if (/^(时间|地点|人物)[：:]/.test(trimmed)) {
          return (
            <span key={i} className="scene-meta" style={{ display: "block" }}>
              {line}
            </span>
          );
        }

        // Stage direction: 【...】
        if (/^【.*】/.test(trimmed)) {
          return (
            <div key={i} className="stage-direction">
              {line}
            </div>
          );
        }

        // Scene break: --- or — — —
        if (/^[-—]{2,}$/.test(trimmed) || /^[—]\s*[—]\s*[—]$/.test(trimmed)) {
          return (
            <span key={i} className="scene-break" style={{ display: "block" }}>
              — — —
            </span>
          );
        }

        // Dialogue: 角色名：对白
        const dMatch = line.match(/^(\S+?)[：:]\s*(.+)/);
        if (dMatch && !/^(时间|地点|人物|第)/.test(trimmed)) {
          return (
            <div key={i} className="dialogue">
              <span className="speaker">{dMatch[1]}：</span>
              <span className="line">{dMatch[2]}</span>
            </div>
          );
        }

        // Scene description
        if (/^\[画面[：:]\s*.*\]/.test(trimmed)) {
          return (
            <div key={i} style={{ color: "#6366f1", fontStyle: "italic", margin: "4px 0 4px 16px", fontSize: "13px" }}>
              {line}
            </div>
          );
        }

        // Generic bracket action
        if (/^\[.*\]/.test(trimmed)) {
          return (
            <div key={i} style={{ color: "#94a3b8", fontSize: "12px", margin: "2px 0 2px 24px" }}>
              {line}
            </div>
          );
        }

        // Empty line
        if (trimmed === "") {
          return <div key={i} style={{ height: "8px" }} />;
        }

        // Default
        return (
          <div key={i} style={{ color: "#334155", margin: "2px 0 2px 8px" }}>
            {line}
          </div>
        );
      })}
    </>
  );
}
