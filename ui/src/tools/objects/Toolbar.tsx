// ui/src/components/Toolbar.tsx
import React, { useState } from "react";
import ToolbarIcon from "./ToolbarIcon";

import {
  IconTrendline,
  IconHorizontal,
  IconVertical,
  IconFibRetracement,
  IconFibExtension,
  IconFibProjection,
  IconClear,
} from "./icons";

interface ToolbarProps {
  activeTool: string;
  setTool: (t: string) => void;
  clearAll: () => void;
}

export default function Toolbar({ activeTool, setTool, clearAll }: ToolbarProps) {
  return (
    <div
      style={{
        position: "absolute",
        left: "10px",
        top: "10px",
        zIndex: 20,
        display: "flex",
        flexDirection: "column",
        gap: "8px",
        padding: "4px",
        background: "rgba(0,0,0,0.3)",
        borderRadius: "8px",
        backdropFilter: "blur(4px)",
      }}
    >
      <ToolbarIcon
        active={activeTool === "trendline"}
        onClick={() => setTool("trendline")}
        title="Trendline"
      >
        {IconTrendline}
      </ToolbarIcon>

      <ToolbarIcon
        active={activeTool === "horizontal"}
        onClick={() => setTool("horizontal")}
        title="Horizontal Line"
      >
        {IconHorizontal}
      </ToolbarIcon>

      <ToolbarIcon
        active={activeTool === "vertical"}
        onClick={() => setTool("vertical")}
        title="Vertical Line"
      >
        {IconVertical}
      </ToolbarIcon>

      <ToolbarIcon
        active={activeTool === "fibonacci_retracement"}
        onClick={() => setTool("fibonacci_retracement")}
        title="Fibonacci Retracement"
      >
        {IconFibRetracement}
      </ToolbarIcon>

      <ToolbarIcon
        active={activeTool === "fibonacci_extension"}
        onClick={() => setTool("fibonacci_extension")}
        title="Fibonacci Extension"
      >
        {IconFibExtension}
      </ToolbarIcon>

      <ToolbarIcon
        active={activeTool === "fibonacci_projection"}
        onClick={() => setTool("fibonacci_projection")}
        title="Fibonacci Projection"
      >
        {IconFibProjection}
      </ToolbarIcon>

      <ToolbarIcon onClick={clearAll} title="Apagar todas">
        {IconClear}
      </ToolbarIcon>
    </div>
  );
}
