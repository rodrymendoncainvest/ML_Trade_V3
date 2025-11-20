// ui/src/components/ToolManager.ts

import type { ChartApi } from "lightweight-charts";

export type ToolType = "none" | "trendline" | "hline" | "eraser";

interface Point {
    x: number;
    y: number;
}

export default class ToolManager {
    private canvas: HTMLCanvasElement | null = null;
    private ctx: CanvasRenderingContext2D | null = null;
    private chart: ChartApi | null = null;

    private activeTool: ToolType = "none";
    private isDrawing = false;

    private start: Point | null = null;
    private end: Point | null = null;

    private drawnObjects: { tool: ToolType; start: Point; end: Point }[] = [];

    connect(canvas: HTMLCanvasElement, chart: ChartApi) {
        this.canvas = canvas;
        this.chart = chart;
        this.ctx = canvas.getContext("2d");

        this.resizeCanvas();
        window.addEventListener("resize", () => this.resizeCanvas());

        canvas.addEventListener("mousedown", (e) => this.onMouseDown(e));
        canvas.addEventListener("mousemove", (e) => this.onMouseMove(e));
        canvas.addEventListener("mouseup", (e) => this.onMouseUp(e));

        this.drawAll();
    }

    setTool(tool: ToolType) {
        this.activeTool = tool;
    }

    clearAll() {
        this.drawnObjects = [];
        this.drawAll();
    }

    private onMouseDown(e: MouseEvent) {
        if (!this.canvas) return;
        if (this.activeTool === "none") return;

        const rect = this.canvas.getBoundingClientRect();
        this.start = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        this.end = { ...this.start };
        this.isDrawing = true;
    }

    private onMouseMove(e: MouseEvent) {
        if (!this.canvas || !this.isDrawing || !this.start) return;

        const rect = this.canvas.getBoundingClientRect();
        this.end = { x: e.clientX - rect.left, y: e.clientY - rect.top };

        this.drawAll();
        this.drawCurrent();
    }

    private onMouseUp() {
        if (!this.isDrawing || !this.start || !this.end) return;

        this.drawnObjects.push({
            tool: this.activeTool,
            start: { ...this.start },
            end: { ...this.end },
        });

        this.isDrawing = false;
        this.start = null;
        this.end = null;

        this.drawAll();
    }

    private resizeCanvas() {
        if (!this.canvas) return;

        const parent = this.canvas.parentElement;
        if (!parent) return;

        this.canvas.width = parent.clientWidth;
        this.canvas.height = parent.clientHeight;

        this.drawAll();
    }

    private drawAll() {
        if (!this.ctx || !this.canvas) return;

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        for (const obj of this.drawnObjects) {
            this.ctx.strokeStyle = obj.tool === "trendline" ? "#4caf50" : "#e67e22";
            this.ctx.lineWidth = 2;

            this.ctx.beginPath();
            this.ctx.moveTo(obj.start.x, obj.start.y);
            this.ctx.lineTo(obj.end.x, obj.end.y);
            this.ctx.stroke();
        }
    }

    private drawCurrent() {
        if (!this.ctx || !this.start || !this.end) return;

        this.ctx.strokeStyle = "#3498db";
        this.ctx.lineWidth = 2;

        this.ctx.beginPath();
        this.ctx.moveTo(this.start.x, this.start.y);
        this.ctx.lineTo(this.end.x, this.end.y);
        this.ctx.stroke();
    }
}
