// ui/src/components/Toolbar.tsx
import React from "react";

interface ToolbarProps {
  activeTool: string;
  setTool: (tool: string) => void;
  clearAll: () => void;
}

export default function Toolbar({ activeTool, setTool, clearAll }: ToolbarProps) {
  return (
    <div className="toolbar">
      <button
        className={activeTool === "none" ? "active" : ""}
        onClick={() => setTool("none")}
      >
        Cursor
      </button>

      <button
        className={activeTool === "trendline" ? "active" : ""}
        onClick={() => setTool("trendline")}
      >
        Trendline
      </button>

      <button
        className={activeTool === "hline" ? "active" : ""}
        onClick={() => setTool("hline")}
      >
        Horizontal
      </button>

      <button onClick={clearAll}>Clear</button>
    </div>
  );
}
