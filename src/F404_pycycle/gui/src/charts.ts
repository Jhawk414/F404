/**
 * High-performance HTML5 Canvas chart renderer in TypeScript.
 *
 * Lightweight, zero-dependency alternative to Plotly for instantaneous 60+ FPS
 * operating curve rendering during continuous slider dragging.
 */

export interface Point2D {
  x: number;
  y: number;
}

export interface SeriesConfig {
  name: string;
  points: Point2D[];
  color: string;
  lineWidth?: number;
  dashed?: boolean;
}

export interface ChartOptions {
  xLabel: string;
  yLabel: string;
  title: string;
  xUnit?: string;
  yUnit?: string;
}

export class InteractiveChart {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private options: ChartOptions;
  private seriesList: SeriesConfig[] = [];
  private activePoint: Point2D | null = null;
  private margin = { top: 35, right: 25, bottom: 45, left: 65 };

  constructor(canvas: HTMLCanvasElement, options: ChartOptions) {
    this.canvas = canvas;
    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('Canvas 2D context not supported');
    }
    this.ctx = context;
    this.options = options;
  }

  public setData(seriesList: SeriesConfig[], activePoint: Point2D | null = null): void {
    this.seriesList = seriesList;
    this.activePoint = activePoint;
    this.render();
  }

  public setActivePoint(point: Point2D | null): void {
    this.activePoint = point;
    this.render();
  }

  public render(): void {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();

    const width = Math.max(280, rect.width || this.canvas.width);
    const height = Math.max(180, rect.height || this.canvas.height);

    if (this.canvas.width !== width * dpr || this.canvas.height !== height * dpr) {
      this.canvas.width = width * dpr;
      this.canvas.height = height * dpr;
    }

    this.ctx.resetTransform?.();
    this.ctx.scale(dpr, dpr);

    // Clear background
    this.ctx.fillStyle = '#0f172a'; // slate-900
    this.ctx.fillRect(0, 0, width, height);

    if (this.seriesList.length === 0 && !this.activePoint) {
      this.drawPlaceholder(width, height, 'No data available');
      return;
    }

    // Determine data bounds
    let xMin = Infinity;
    let xMax = -Infinity;
    let yMin = Infinity;
    let yMax = -Infinity;

    for (const s of this.seriesList) {
      for (const p of s.points) {
        if (p.x < xMin) xMin = p.x;
        if (p.x > xMax) xMax = p.x;
        if (p.y < yMin) yMin = p.y;
        if (p.y > yMax) yMax = p.y;
      }
    }

    if (this.activePoint) {
      if (this.activePoint.x < xMin) xMin = this.activePoint.x;
      if (this.activePoint.x > xMax) xMax = this.activePoint.x;
      if (this.activePoint.y < yMin) yMin = this.activePoint.y;
      if (this.activePoint.y > yMax) yMax = this.activePoint.y;
    }

    if (!isFinite(xMin) || !isFinite(xMax) || xMin === xMax) {
      xMin = (xMin === Infinity ? 0 : xMin) - 100;
      xMax = (xMax === -Infinity ? 100 : xMax) + 100;
    }
    if (!isFinite(yMin) || !isFinite(yMax) || yMin === yMax) {
      yMin = (yMin === Infinity ? 0 : yMin) - 100;
      yMax = (yMax === -Infinity ? 100 : yMax) + 100;
    }

    // Add 5% padding
    const xPad = (xMax - xMin) * 0.05 || 1;
    const yPad = (yMax - yMin) * 0.08 || 1;
    xMin -= xPad;
    xMax += xPad;
    yMin -= yPad;
    yMax += yPad;

    const plotW = width - this.margin.left - this.margin.right;
    const plotH = height - this.margin.top - this.margin.bottom;

    const toScreenX = (x: number) => this.margin.left + ((x - xMin) / (xMax - xMin)) * plotW;
    const toScreenY = (y: number) => this.margin.top + plotH - ((y - yMin) / (yMax - yMin)) * plotH;

    // Draw Grid & Axes
    this.drawGrid(width, height, plotW, plotH, xMin, xMax, yMin, yMax, toScreenX, toScreenY);

    // Draw Series
    for (const s of this.seriesList) {
      if (s.points.length === 0) continue;
      this.ctx.beginPath();
      this.ctx.strokeStyle = s.color;
      this.ctx.lineWidth = s.lineWidth || 2;
      if (s.dashed) {
        this.ctx.setLineDash([4, 4]);
      } else {
        this.ctx.setLineDash([]);
      }

      for (let i = 0; i < s.points.length; i++) {
        const sx = toScreenX(s.points[i].x);
        const sy = toScreenY(s.points[i].y);
        if (i === 0) this.ctx.moveTo(sx, sy);
        else this.ctx.lineTo(sx, sy);
      }
      this.ctx.stroke();

      // Small points
      this.ctx.fillStyle = s.color;
      for (const p of s.points) {
        const sx = toScreenX(p.x);
        const sy = toScreenY(p.y);
        this.ctx.beginPath();
        this.ctx.arc(sx, sy, 2.5, 0, Math.PI * 2);
        this.ctx.fill();
      }
    }

    this.ctx.setLineDash([]);

    // Draw Active Point Marker
    if (this.activePoint) {
      const ax = toScreenX(this.activePoint.x);
      const ay = toScreenY(this.activePoint.y);

      // Glow halo
      this.ctx.beginPath();
      this.ctx.arc(ax, ay, 9, 0, Math.PI * 2);
      this.ctx.fillStyle = 'rgba(56, 189, 248, 0.25)'; // sky-400 translucent
      this.ctx.fill();

      // Outer ring
      this.ctx.beginPath();
      this.ctx.arc(ax, ay, 6, 0, Math.PI * 2);
      this.ctx.strokeStyle = '#38bdf8';
      this.ctx.lineWidth = 2.5;
      this.ctx.stroke();

      // Center dot
      this.ctx.beginPath();
      this.ctx.arc(ax, ay, 3, 0, Math.PI * 2);
      this.ctx.fillStyle = '#ffffff';
      this.ctx.fill();

      // Readout badge
      const badgeText = `${this.activePoint.y.toFixed(1)} ${this.options.yUnit || ''}`.trim();
      this.ctx.font = '600 11px system-ui, sans-serif';
      this.ctx.fillStyle = '#38bdf8';
      this.ctx.fillText(badgeText, ax + 10, ay - 8);
    }

    // Chart Title
    this.ctx.font = '600 13px system-ui, sans-serif';
    this.ctx.fillStyle = '#f8fafc'; // slate-50
    this.ctx.fillText(this.options.title, this.margin.left, 20);
  }

  private drawGrid(
    width: number,
    height: number,
    plotW: number,
    plotH: number,
    xMin: number,
    xMax: number,
    yMin: number,
    yMax: number,
    toX: (x: number) => number,
    toY: (y: number) => number
  ): void {
    this.ctx.strokeStyle = '#1e293b'; // slate-800
    this.ctx.lineWidth = 1;

    // Y Grid lines & ticks
    const yTicks = 5;
    this.ctx.font = '10px system-ui, sans-serif';
    this.ctx.fillStyle = '#64748b'; // slate-500
    this.ctx.textAlign = 'right';
    this.ctx.textBaseline = 'middle';

    for (let i = 0; i <= yTicks; i++) {
      const val = yMin + (i / yTicks) * (yMax - yMin);
      const sy = toY(val);

      this.ctx.beginPath();
      this.ctx.moveTo(this.margin.left, sy);
      this.ctx.lineTo(this.margin.left + plotW, sy);
      this.ctx.stroke();

      const label = val >= 1000 ? (val / 1000).toFixed(1) + 'k' : val.toFixed(val < 10 ? 2 : 0);
      this.ctx.fillText(label, this.margin.left - 8, sy);
    }

    // X Grid lines & ticks
    const xTicks = 5;
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'top';

    for (let i = 0; i <= xTicks; i++) {
      const val = xMin + (i / xTicks) * (xMax - xMin);
      const sx = toX(val);

      this.ctx.beginPath();
      this.ctx.moveTo(sx, this.margin.top);
      this.ctx.lineTo(sx, this.margin.top + plotH);
      this.ctx.stroke();

      const label = val >= 1000 ? (val / 1000).toFixed(1) + 'k' : val.toFixed(0);
      this.ctx.fillText(label, sx, this.margin.top + plotH + 8);
    }

    // Axis Labels
    this.ctx.font = '11px system-ui, sans-serif';
    this.ctx.fillStyle = '#94a3b8'; // slate-400
    this.ctx.textAlign = 'center';

    // X-axis label
    const xLabelText = `${this.options.xLabel} ${this.options.xUnit ? `(${this.options.xUnit})` : ''}`.trim();
    this.ctx.fillText(xLabelText, this.margin.left + plotW / 2, height - 12);

    // Y-axis label (rotated)
    this.ctx.save();
    this.ctx.translate(16, this.margin.top + plotH / 2);
    this.ctx.rotate(-Math.PI / 2);
    const yLabelText = `${this.options.yLabel} ${this.options.yUnit ? `(${this.options.yUnit})` : ''}`.trim();
    this.ctx.fillText(yLabelText, 0, 0);
    this.ctx.restore();
  }

  private drawPlaceholder(width: number, height: number, msg: string): void {
    this.ctx.font = '12px system-ui, sans-serif';
    this.ctx.fillStyle = '#64748b';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText(msg, width / 2, height / 2);
  }
}
