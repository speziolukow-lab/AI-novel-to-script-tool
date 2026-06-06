/**
 * Script viewer with syntax highlighting for script format.
 *
 * Parses the output format:
 *   第 X 场
 *   时间：XX  地点：XX  人物：XX
 *   【舞台指示】
 *   角色A：（对白）
 */
export function ScriptViewer({ text }: { text: string }) {
  const lines = text.split("\n");

  return (
    <div className="script-content font-mono text-sm leading-relaxed">
      {lines.map((line, i) => {
        // Scene header
        if (/^第\s*\d+[\s]*场/.test(line.trim())) {
          return (
            <div key={i} className="text-indigo-700 font-bold text-base mt-6 mb-2 border-b border-indigo-100 pb-1">
              {line}
            </div>
          );
        }

        // Metadata line (时间/地点/人物)
        if (/^(时间|地点|人物)[：:]/.test(line.trim())) {
          return (
            <div key={i} className="text-slate-500 text-xs ml-2 mb-1">
              {line}
            </div>
          );
        }

        // Stage direction
        if (/^【.*】/.test(line.trim())) {
          return (
            <div key={i} className="text-indigo-500 italic ml-4 my-2 leading-relaxed">
              {line}
            </div>
          );
        }

        // Scene description (画面描述)
        if (/^\[画面[：:]\s*.*\]/.test(line.trim())) {
          return (
            <div key={i} className="text-indigo-400 italic ml-4 my-1">
              {line}
            </div>
          );
        }

        // Dialogue (角色A：...)
        const dialogueMatch = line.match(/^(\S+?)[：:]\s*(.+)/);
        if (dialogueMatch && !/^(时间|地点|人物|第)/.test(line.trim())) {
          return (
            <div key={i} className="ml-6 my-1 flex">
              <span className="text-slate-800 font-semibold shrink-0">
                {dialogueMatch[1]}：
              </span>
              <span className="text-slate-600 ml-1">{dialogueMatch[2]}</span>
            </div>
          );
        }

        // Action direction (action in brackets)
        const actionMatch = line.match(/^\[([^画面].*?)\]/);
        if (actionMatch) {
          return (
            <div key={i} className="text-slate-400 text-xs ml-6 my-1">
              {line}
            </div>
          );
        }

        // Empty line
        if (line.trim() === "") {
          return <div key={i} className="h-2" />;
        }

        // Default text
        return (
          <div key={i} className="text-slate-700 ml-2 my-0.5">
            {line}
          </div>
        );
      })}
    </div>
  );
}
