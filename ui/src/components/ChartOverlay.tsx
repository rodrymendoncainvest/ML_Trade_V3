// ui/src/components/ChartOverlay.tsx
import React, { useEffect, useRef } from "react";

export interface OverlayEvent {
  type: "mousedown" | "mousemove" | "mouseup" | "dblclick" | "leave";
  x: number;
  y: number;
  originalEvent: MouseEvent;
}

interface Props {
  width: number;
  height: number;
  onEvent: (evt: OverlayEvent) => void;
  draw: (ctx: CanvasRenderingContext2D) => void;
}

const ChartOverlay: React.FC<Props> = ({ width, height, onEvent, draw }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Resize + redraw
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);
    draw(ctx);
  }, [width, height, draw]);

  // Mouse event translator
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handler = (type: OverlayEvent["type"]) => (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      onEvent({
        type,
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        originalEvent: e,
      });
    };

    canvas.addEventListener("mousedown", handler("mousedown"));
    canvas.addEventListener("mousemove", handler("mousemove"));
    canvas.addEventListener("mouseup", handler("mouseup"));
    canvas.addEventListener("dblclick", handler("dblclick"));
    canvas.addEventListener("mouseleave", handler("leave"));

    return () => {
      canvas.removeEventListener("mousedown", handler("mousedown"));
      canvas.removeEventListener("mousemove", handler("mousemove"));
      canvas.removeEventListener("mouseup", handler("mouseup"));
      canvas.removeEventListener("dblclick", handler("dblclick"));
      canvas.removeEventListener("mouseleave", handler("leave"));
    };
  }, [onEvent]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "auto",
        background: "transparent",
      }}
    />
  );
};

export default ChartOverlay;
