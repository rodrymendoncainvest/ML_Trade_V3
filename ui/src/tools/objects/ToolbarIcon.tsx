// ui/src/components/ToolbarIcon.tsx
import React from "react";

interface ToolbarIconProps {
  active?: boolean;
  onClick?: () => void;
  title?: string;
  children: React.ReactNode;
}

export default function ToolbarIcon({
  active = false,
  onClick,
  title,
  children,
}: ToolbarIconProps) {
  return (
    <button
      title={title}
      onClick={onClick}
      style={{
        width: "34px",
        height: "34px",
        borderRadius: "6px",
        border: active ? "1px solid #2563eb" : "1px solid #1f2937",
        background: active ? "#1d4ed8" : "#111827",
        color: "#e5e7eb",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        padding: 0,
      }}
    >
      {children}
    </button>
  );
}
