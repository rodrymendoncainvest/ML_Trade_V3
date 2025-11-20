// ui/src/tools/objects/ChartObject.ts
// Base de objetos + classes de ferramentas

import { OverlayEvent } from "../../components/ChartOverlay";
import { ToolType } from "../ToolManager";

// -------------------------------------------------------------
//  Classe Base
// -------------------------------------------------------------
export abstract class ChartObject {
  abstract type: ToolType;
  protected points: { x: number; y: number }[] = [];

  static create(type: ToolType): ChartObject {
    switch (type) {
      case "trendline":
        return new Trendline();
      case "horizontal":
        return new HorizontalLine();
      case "vertical":
        return new VerticalLine();
      case "fibonacci_retracement":
        return new FibonacciRetracement();
      case "fibonacci_extension":
        return new FibonacciExtension();
      case "fibonacci_projection":
        return new FibonacciProjection();
      default:
        throw new Error("Tool não suportada: " + type);
    }
  }

  onMouseDown(evt: OverlayEvent): void {
    this.points.push({ x: evt.x, y: evt.y });
  }

  onMouseMove(evt: OverlayEvent): void {
    if (this.points.length === 0) return;
    this.points[this.points.length - 1] = { x: evt.x, y: evt.y };
  }

  abstract onMouseUp(evt: OverlayEvent): boolean; // retorna true quando finalizado
  abstract draw(ctx: CanvasRenderingContext2D): void;
}

// -------------------------------------------------------------
// 1) TRENDLINE (2 pontos)
// -------------------------------------------------------------
export class Trendline extends ChartObject {
  type: ToolType = "trendline";

  onMouseUp(): boolean {
    return this.points.length >= 2;
  }

  draw(ctx: CanvasRenderingContext2D) {
    if (this.points.length < 2) return;

    ctx.save();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
    ctx.lineWidth = 1.5;

    const p0 = this.points[0];
    const p1 = this.points[1];

    ctx.beginPath();
    ctx.moveTo(p0.x, p0.y);
    ctx.lineTo(p1.x, p1.y);
    ctx.stroke();
    ctx.restore();
  }
}

// -------------------------------------------------------------
// 2) HORIZONTAL LINE (1 ponto → largura total)
// -------------------------------------------------------------
export class HorizontalLine extends ChartObject {
  type: ToolType = "horizontal";

  onMouseUp(): boolean {
    return this.points.length >= 1;
  }

  draw(ctx: CanvasRenderingContext2D) {
    if (this.points.length === 0) return;

    const p = this.points[0];

    ctx.save();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
    ctx.lineWidth = 1;

    ctx.beginPath();
    ctx.moveTo(0, p.y);
    ctx.lineTo(ctx.canvas.width, p.y);
    ctx.stroke();

    ctx.restore();
  }
}

// -------------------------------------------------------------
// 3) VERTICAL LINE (1 ponto → altura total)
// -------------------------------------------------------------
export class VerticalLine extends ChartObject {
  type: ToolType = "vertical";

  onMouseUp(): boolean {
    return this.points.length >= 1;
  }

  draw(ctx: CanvasRenderingContext2D) {
    if (this.points.length === 0) return;

    const p = this.points[0];

    ctx.save();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
    ctx.lineWidth = 1;

    ctx.beginPath();
    ctx.moveTo(p.x, 0);
    ctx.lineTo(p.x, ctx.canvas.height);
    ctx.stroke();

    ctx.restore();
  }
}

// -------------------------------------------------------------
// 4) FIBONACCI RETRACEMENT (2 pontos)
// -------------------------------------------------------------
export class FibonacciRetracement extends ChartObject {
  type: ToolType = "fibonacci_retracement";

  levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];

  onMouseUp(): boolean {
    return this.points.length >= 2;
  }

  draw(ctx: CanvasRenderingContext2D) {
    if (this.points.length < 2) return;

    const p0 = this.points[0];
    const p1 = this.points[1];

    const minY = Math.min(p0.y, p1.y);
    const maxY = Math.max(p0.y, p1.y);

    ctx.save();
    ctx.lineWidth = 1;

    this.levels.forEach((lvl) => {
      const y = maxY - (maxY - minY) * lvl;

      ctx.strokeStyle = "rgba(255,255,255,0.25)";
      ctx.beginPath();
      ctx.moveTo(p0.x, y);
      ctx.lineTo(p1.x, y);
      ctx.stroke();

      ctx.fillStyle = "rgba(255,255,255,0.7)";
      ctx.font = "11px sans-serif";
      ctx.fillText((lvl * 100).toFixed(1) + "%", p1.x + 6, y + 3);
    });

    ctx.restore();
  }
}

// -------------------------------------------------------------
// 5) FIBONACCI EXTENSION (3 pontos)
// -------------------------------------------------------------
export class FibonacciExtension extends ChartObject {
  type: ToolType = "fibonacci_extension";

  levels = [0.618, 1, 1.272, 1.618, 2, 2.618];

  onMouseUp(): boolean {
    return this.points.length >= 3;
  }

  draw(ctx: CanvasRenderingContext2D) {
    if (this.points.length < 3) return;

    const A = this.points[0];
    const B = this.points[1];
    const C = this.points[2];

    const AB = B.y - A.y;

    ctx.save();

    this.levels.forEach((lvl) => {
      const y = C.y + AB * lvl;

      ctx.strokeStyle = "rgba(255,255,255,0.25)";
      ctx.lineWidth = 1;

      ctx.beginPath();
      ctx.moveTo(A.x, y);
      ctx.lineTo(C.x, y);
      ctx.stroke();

      ctx.fillStyle = "rgba(255,255,255,0.7)";
      ctx.font = "11px sans-serif";
      ctx.fillText(`FE ${lvl}`, C.x + 6, y + 3);
    });

    ctx.restore();
  }
}

// -------------------------------------------------------------
// 6) FIBONACCI PROJECTION (3 pontos)
// -------------------------------------------------------------
export class FibonacciProjection extends ChartObject {
  type: ToolType = "fibonacci_projection";

  levels = [1, 1.272, 1.618, 2, 2.618];

  onMouseUp(): boolean {
    return this.points.length >= 3;
  }

  draw(ctx: CanvasRenderingContext2D) {
    if (this.points.length < 3) return;

    const A = this.points[0];
    const B = this.points[1];
    const C = this.points[2];

    const BC = C.y - B.y;

    ctx.save();

    this.levels.forEach((lvl) => {
      const y = B.y - BC * lvl;

      ctx.strokeStyle = "rgba(255,255,255,0.25)";
      ctx.lineWidth = 1;

      ctx.beginPath();
      ctx.moveTo(A.x, y);
      ctx.lineTo(C.x, y);
      ctx.stroke();

      ctx.fillStyle = "rgba(255,255,255,0.7)";
      ctx.font = "11px sans-serif";
      ctx.fillText(`FP ${lvl}`, C.x + 6, y + 3);
    });

    ctx.restore();
  }
}
