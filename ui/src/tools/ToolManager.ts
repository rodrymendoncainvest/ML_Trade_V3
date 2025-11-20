// ui/src/tools/ToolManager.ts
import { ChartObject } from "./objects/ChartObject";
import { OverlayEvent } from "../components/ChartOverlay";

export type ToolType =
  | "none"
  | "trendline"
  | "horizontal"
  | "vertical"
  | "ray"
  | "fibonacci_retracement"
  | "fibonacci_extension"
  | "fibonacci_projection";

interface ToolManagerOptions {
  requestDraw: () => void;
}

export class ToolManager {
  private activeTool: ToolType = "none";
  private objects: ChartObject[] = [];
  private draft: ChartObject | null = null;
  private requestDraw: () => void;

  constructor(opts: ToolManagerOptions) {
    this.requestDraw = opts.requestDraw;
  }

  setTool(tool: ToolType) {
    this.activeTool = tool;
    this.draft = null; // limpar desenho incompleto
    this.requestDraw();
  }

  clearAll() {
    this.objects = [];
    this.draft = null;
    this.requestDraw();
  }

  getObjects() {
    return this.objects;
  }

  getDraft() {
    return this.draft;
  }

  // ---------------------------------------------------------------------
  // EVENTOS DO OVERLAY
  // ---------------------------------------------------------------------
  handleEvent(evt: OverlayEvent) {
    if (this.activeTool === "none") return;

    switch (evt.type) {
      case "mousedown":
        this.handleMouseDown(evt);
        break;
      case "mousemove":
        this.handleMouseMove(evt);
        break;
      case "mouseup":
        this.handleMouseUp(evt);
        break;
    }
  }

  // ---------------------------------------------------------------------
  // MOUSE DOWN
  // ---------------------------------------------------------------------
  handleMouseDown(evt: OverlayEvent) {
    // Criar draft com base no tipo ativo
    if (!this.draft) {
      this.draft = ChartObject.create(this.activeTool);
    }

    this.draft?.onMouseDown(evt);
    this.requestDraw();
  }

  // ---------------------------------------------------------------------
  // MOUSE MOVE
  // ---------------------------------------------------------------------
  handleMouseMove(evt: OverlayEvent) {
    if (!this.draft) return;

    this.draft.onMouseMove(evt);
    this.requestDraw();
  }

  // ---------------------------------------------------------------------
  // MOUSE UP
  // ---------------------------------------------------------------------
  handleMouseUp(evt: OverlayEvent) {
    if (!this.draft) return;

    const finished = this.draft.onMouseUp(evt);

    if (finished) {
      this.objects.push(this.draft);
      this.draft = null;

      // Se a ferramenta for "one-shot", volta a none
      if (
        this.activeTool !== "trendline" &&
        this.activeTool !== "fibonacci_retracement" &&
        this.activeTool !== "fibonacci_extension" &&
        this.activeTool !== "fibonacci_projection"
      ) {
        this.activeTool = "none";
      }
    }

    this.requestDraw();
  }

  // ---------------------------------------------------------------------
  // DRAW
  // ---------------------------------------------------------------------
  drawAll(ctx: CanvasRenderingContext2D) {
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    // Objetos finalizados
    for (const obj of this.objects) {
      obj.draw(ctx);
    }

    // Draft atual
    if (this.draft) {
      this.draft.draw(ctx);
    }
  }
}
