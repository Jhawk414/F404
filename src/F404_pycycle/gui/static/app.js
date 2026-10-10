/**
 * GE F404 Turbofan Cycle Deck Explorer — Browser Application Runtime
 *
 * Implements high-performance client-side trilinear cycle deck interpolation,
 * Canvas operating curve rendering, and responsive slider interaction.
 */

// ── ClientDeckInterpolator ───────────────────────────────────────────────────

export class ClientDeckInterpolator {
  constructor(payload) {
    this.payload = payload;
    this.currentMode = payload.default_mode || payload.modes[0] || 'wet';
  }

  getModes() {
    return this.payload.modes;
  }

  getMode() {
    return this.currentMode;
  }

  setMode(mode) {
    if (this.payload.deck_data[mode]) {
      this.currentMode = mode;
    }
  }

  getModeData(mode = this.currentMode) {
    const data = this.payload.deck_data[mode];
    if (!data) {
      throw new Error(`Mode '${mode}' not found in cycle deck.`);
    }
    return data;
  }

  interpolate(alt, dTs, throttle, mode = this.currentMode) {
    const modeData = this.getModeData(mode);
    const axes = modeData.axes;
    const throttleCol = axes.throttle_col;

    const t4 = mode === 'wet' ? 3100.0 : throttle;
    const t7 = mode === 'wet' ? throttle : (modeData.points[0]?.['T7'] ?? t4);
    const mn = axes.MN?.values?.[0] ?? 0.001;

    const altVals = axes.alt.values;
    const dtsVals = axes.dTs.values;
    const thrVals = axes.throttle.values;

    const multilinear = this.tryMultilinear(
      modeData,
      altVals,
      dtsVals,
      thrVals,
      throttleCol,
      alt,
      dTs,
      throttle
    );

    let outputs;
    let method;
    let corners;

    if (multilinear) {
      outputs = multilinear.outputs;
      method = 'multilinear';
      corners = multilinear.corners;
    } else {
      const idwRes = this.idwInterpolate(modeData, throttleCol, alt, dTs, throttle);
      outputs = idwRes.outputs;
      method = idwRes.method;
      corners = idwRes.corners;
    }

    this.addDerivedQuantities(outputs, mode, alt, dTs, throttle);

    return {
      inputs: {
        mode,
        alt,
        dTs,
        throttle,
        throttle_col: throttleCol,
        T4: t4,
        T7: t7,
        MN: mn,
      },
      outputs,
      method,
      corners,
    };
  }

  tryMultilinear(modeData, altVals, dtsVals, thrVals, throttleCol, alt, dTs, throttle) {
    const [iAlt0, iAlt1, tAlt] = this.findInterval(altVals, alt);
    const [iDts0, iDts1, tDts] = this.findInterval(dtsVals, dTs);
    const [iThr0, iThr1, tThr] = this.findInterval(thrVals, throttle);

    const gAlt = [altVals[iAlt0], altVals[iAlt1]];
    const gDts = [dtsVals[iDts0], dtsVals[iDts1]];
    const gThr = [thrVals[iThr0], thrVals[iThr1]];

    const wAlt = [1.0 - tAlt, tAlt];
    const wDts = [1.0 - tDts, tDts];
    const wThr = [1.0 - tThr, tThr];

    const lookup = new Map();
    for (const pt of modeData.points) {
      const key = `${pt['alt']}_${pt['dTs']}_${pt[throttleCol]}`;
      lookup.set(key, pt);
    }

    const corners = [];
    const cornerWeights = [];

    let allFound = true;
    for (let ia = 0; ia < 2; ia++) {
      for (let idt = 0; idt < 2; idt++) {
        for (let ith = 0; ith < 2; ith++) {
          const key = `${gAlt[ia]}_${gDts[idt]}_${gThr[ith]}`;
          const pt = lookup.get(key);
          if (!pt) {
            allFound = false;
            break;
          }
          const w = wAlt[ia] * wDts[idt] * wThr[ith];
          corners.push(pt);
          cornerWeights.push(w);
        }
        if (!allFound) break;
      }
      if (!allFound) break;
    }

    if (!allFound || corners.length === 0) {
      return null;
    }

    let totalWeight = cornerWeights.reduce((a, b) => a + b, 0);
    if (totalWeight <= 0) totalWeight = 1.0;

    const outputs = {};
    for (const col of modeData.columns) {
      let sum = 0;
      let valid = false;
      for (let i = 0; i < corners.length; i++) {
        const val = corners[i][col];
        if (typeof val === 'number') {
          sum += cornerWeights[i] * val;
          valid = true;
        }
      }
      outputs[col] = valid ? sum / totalWeight : null;
    }

    const cornerInfo = corners
      .map((c, i) => ({
        alt: Number(c['alt']),
        dTs: Number(c['dTs']),
        throttle: Number(c[throttleCol]),
        weight: cornerWeights[i] / totalWeight,
      }))
      .filter((c) => c.weight > 1e-6);

    return { outputs, corners: cornerInfo };
  }

  findInterval(vals, x) {
    if (vals.length <= 1) return [0, 0, 0.0];
    if (x <= vals[0]) return [0, 0, 0.0];
    if (x >= vals[vals.length - 1]) {
      const last = vals.length - 1;
      return [last, last, 0.0];
    }
    for (let i = 0; i < vals.length - 1; i++) {
      if (vals[i] <= x && x <= vals[i + 1]) {
        const span = vals[i + 1] - vals[i];
        const t = span > 1e-12 ? (x - vals[i]) / span : 0.0;
        return [i, i + 1, t];
      }
    }
    return [vals.length - 2, vals.length - 1, 1.0];
  }

  idwInterpolate(modeData, throttleCol, alt, dTs, throttle, k = 8, power = 2.0) {
    const axes = modeData.axes;
    const altSpan = Math.max(1.0, axes.alt.max - axes.alt.min);
    const dtsSpan = Math.max(1.0, axes.dTs.max - axes.dTs.min);
    const thrSpan = Math.max(1.0, axes.throttle.max - axes.throttle.min);

    const qAlt = (alt - axes.alt.min) / altSpan;
    const qDts = (dTs - axes.dTs.min) / dtsSpan;
    const qThr = (throttle - axes.throttle.min) / thrSpan;

    const points = modeData.points;
    const dists = [];

    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      const pAlt = (Number(p['alt']) - axes.alt.min) / altSpan;
      const pDts = (Number(p['dTs']) - axes.dTs.min) / dtsSpan;
      const pThr = (Number(p[throttleCol]) - axes.throttle.min) / thrSpan;

      const d = Math.sqrt(
        (pAlt - qAlt) ** 2 + (pDts - qDts) ** 2 + (pThr - qThr) ** 2
      );

      if (d < 1e-6) {
        const outputs = {};
        for (const col of modeData.columns) {
          outputs[col] = p[col];
        }
        return {
          outputs,
          method: 'exact',
          corners: [
            {
              alt: Number(p['alt']),
              dTs: Number(p['dTs']),
              throttle: Number(p[throttleCol]),
              weight: 1.0,
            },
          ],
        };
      }
      dists.push({ dist: d, index: i });
    }

    dists.sort((a, b) => a.dist - b.dist);
    const topK = dists.slice(0, Math.min(k, dists.length));

    let sumWeights = 0;
    const weights = [];
    for (const item of topK) {
      const w = 1.0 / item.dist ** power;
      weights.push(w);
      sumWeights += w;
    }

    const normWeights = weights.map((w) => w / (sumWeights || 1.0));
    const outputs = {};

    for (const col of modeData.columns) {
      let sum = 0;
      let valid = false;
      for (let i = 0; i < topK.length; i++) {
        const val = points[topK[i].index][col];
        if (typeof val === 'number') {
          sum += normWeights[i] * val;
          valid = true;
        }
      }
      outputs[col] = valid ? sum : null;
    }

    const cornerInfo = topK.map((item, i) => {
      const pt = points[item.index];
      return {
        alt: Number(pt['alt']),
        dTs: Number(pt['dTs']),
        throttle: Number(pt[throttleCol]),
        weight: normWeights[i],
      };
    });

    return {
      outputs,
      method: 'idw',
      corners: cornerInfo,
    };
  }

  addDerivedQuantities(outputs, mode, _alt, _dTs, _throttle) {
    const fn = outputs['Fn'] ?? 0;
    const tsfc = outputs['TSFC'] ?? 0;
    const w = outputs['W'] ?? 0;
    const bpr = outputs['BPR'] ?? 0;
    const farCore = outputs['FAR_core'] ?? 0;

    if (outputs['Wf_tot_pph'] === undefined || outputs['Wf_tot_pph'] === null) {
      outputs['Wf_tot_pph'] = tsfc * fn;
    }
    if (outputs['Wf_tot'] === undefined || outputs['Wf_tot'] === null) {
      outputs['Wf_tot'] = (tsfc * fn) / 3600.0;
    }

    if (outputs['Wf_core'] === undefined || outputs['Wf_core'] === null) {
      const wCore = bpr >= 0 ? w / (1.0 + bpr) : w;
      outputs['Wf_core'] = wCore * farCore;
    }

    if (outputs['Wf_ab'] === undefined || outputs['Wf_ab'] === null) {
      if (mode === 'wet') {
        const wfTot = outputs['Wf_tot'] ?? 0;
        const wfCore = outputs['Wf_core'] ?? 0;
        outputs['Wf_ab'] = Math.max(0, wfTot - wfCore);
      } else {
        outputs['Wf_ab'] = 0.0;
      }
    }

    if (outputs['A8'] === undefined) {
      outputs['A8'] = null;
    }
  }
}

// ── InteractiveChart ──────────────────────────────────────────────────────────

export class InteractiveChart {
  constructor(canvas, options) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.options = options;
    this.seriesList = [];
    this.activePoint = null;
    this.margin = { top: 35, right: 25, bottom: 45, left: 65 };
  }

  setData(seriesList, activePoint = null) {
    this.seriesList = seriesList;
    this.activePoint = activePoint;
    this.render();
  }

  setActivePoint(point) {
    this.activePoint = point;
    this.render();
  }

  render() {
    if (!this.ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();

    const width = Math.max(280, rect.width || this.canvas.width);
    const height = Math.max(180, rect.height || this.canvas.height);

    if (this.canvas.width !== Math.round(width * dpr) || this.canvas.height !== Math.round(height * dpr)) {
      this.canvas.width = Math.round(width * dpr);
      this.canvas.height = Math.round(height * dpr);
    }

    this.ctx.resetTransform?.();
    this.ctx.scale(dpr, dpr);

    this.ctx.fillStyle = '#090d16'; // deep slate
    this.ctx.fillRect(0, 0, width, height);

    if (this.seriesList.length === 0 && !this.activePoint) {
      this.ctx.font = '12px system-ui, sans-serif';
      this.ctx.fillStyle = '#64748b';
      this.ctx.textAlign = 'center';
      this.ctx.fillText('No data available', width / 2, height / 2);
      return;
    }

    let xMin = Infinity, xMax = -Infinity;
    let yMin = Infinity, yMax = -Infinity;

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

    const xPad = (xMax - xMin) * 0.05 || 1;
    const yPad = (yMax - yMin) * 0.08 || 1;
    xMin -= xPad;
    xMax += xPad;
    yMin -= yPad;
    yMax += yPad;

    const plotW = width - this.margin.left - this.margin.right;
    const plotH = height - this.margin.top - this.margin.bottom;

    const toScreenX = (x) => this.margin.left + ((x - xMin) / (xMax - xMin)) * plotW;
    const toScreenY = (y) => this.margin.top + plotH - ((y - yMin) / (yMax - yMin)) * plotH;

    // Grid lines & labels
    this.ctx.strokeStyle = '#1e293b';
    this.ctx.lineWidth = 1;

    const yTicks = 5;
    this.ctx.font = '10px JetBrains Mono, monospace';
    this.ctx.fillStyle = '#64748b';
    this.ctx.textAlign = 'right';
    this.ctx.textBaseline = 'middle';

    for (let i = 0; i <= yTicks; i++) {
      const val = yMin + (i / yTicks) * (yMax - yMin);
      const sy = toScreenY(val);

      this.ctx.beginPath();
      this.ctx.moveTo(this.margin.left, sy);
      this.ctx.lineTo(this.margin.left + plotW, sy);
      this.ctx.stroke();

      const label = val >= 1000 ? (val / 1000).toFixed(1) + 'k' : val.toFixed(val < 10 ? 2 : 0);
      this.ctx.fillText(label, this.margin.left - 8, sy);
    }

    const xTicks = 5;
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'top';

    for (let i = 0; i <= xTicks; i++) {
      const val = xMin + (i / xTicks) * (xMax - xMin);
      const sx = toScreenX(val);

      this.ctx.beginPath();
      this.ctx.moveTo(sx, this.margin.top);
      this.ctx.lineTo(sx, this.margin.top + plotH);
      this.ctx.stroke();

      const label = val >= 1000 ? (val / 1000).toFixed(1) + 'k' : val.toFixed(0);
      this.ctx.fillText(label, sx, this.margin.top + plotH + 8);
    }

    // Axis titles
    this.ctx.font = '11px Inter, sans-serif';
    this.ctx.fillStyle = '#94a3b8';

    const xLabelText = `${this.options.xLabel} ${this.options.xUnit ? `(${this.options.xUnit})` : ''}`.trim();
    this.ctx.fillText(xLabelText, this.margin.left + plotW / 2, height - 12);

    this.ctx.save();
    this.ctx.translate(16, this.margin.top + plotH / 2);
    this.ctx.rotate(-Math.PI / 2);
    const yLabelText = `${this.options.yLabel} ${this.options.yUnit ? `(${this.options.yUnit})` : ''}`.trim();
    this.ctx.fillText(yLabelText, 0, 0);
    this.ctx.restore();

    // Series
    for (const s of this.seriesList) {
      if (s.points.length === 0) continue;
      this.ctx.beginPath();
      this.ctx.strokeStyle = s.color;
      this.ctx.lineWidth = s.lineWidth || 2;
      for (let i = 0; i < s.points.length; i++) {
        const sx = toScreenX(s.points[i].x);
        const sy = toScreenY(s.points[i].y);
        if (i === 0) this.ctx.moveTo(sx, sy);
        else this.ctx.lineTo(sx, sy);
      }
      this.ctx.stroke();

      this.ctx.fillStyle = s.color;
      for (const p of s.points) {
        const sx = toScreenX(p.x);
        const sy = toScreenY(p.y);
        this.ctx.beginPath();
        this.ctx.arc(sx, sy, 2.5, 0, Math.PI * 2);
        this.ctx.fill();
      }
    }

    // Active marker
    if (this.activePoint) {
      const ax = toScreenX(this.activePoint.x);
      const ay = toScreenY(this.activePoint.y);

      this.ctx.beginPath();
      this.ctx.arc(ax, ay, 9, 0, Math.PI * 2);
      this.ctx.fillStyle = 'rgba(56, 189, 248, 0.25)';
      this.ctx.fill();

      this.ctx.beginPath();
      this.ctx.arc(ax, ay, 5.5, 0, Math.PI * 2);
      this.ctx.strokeStyle = '#38bdf8';
      this.ctx.lineWidth = 2.5;
      this.ctx.stroke();

      this.ctx.beginPath();
      this.ctx.arc(ax, ay, 2.5, 0, Math.PI * 2);
      this.ctx.fillStyle = '#ffffff';
      this.ctx.fill();

      const badgeText = `${this.activePoint.y.toFixed(1)} ${this.options.yUnit || ''}`.trim();
      this.ctx.font = '600 11px JetBrains Mono, monospace';
      this.ctx.fillStyle = '#38bdf8';
      this.ctx.fillText(badgeText, ax + 10, ay - 8);
    }

    // Title
    this.ctx.font = '600 13px Inter, sans-serif';
    this.ctx.fillStyle = '#f8fafc';
    this.ctx.textAlign = 'left';
    this.ctx.fillText(this.options.title, this.margin.left, 20);
  }
}

// ── F404DeckApp ───────────────────────────────────────────────────────────────

export class F404DeckApp {
  constructor() {
    this.interpolator = null;
    this.thrustChart = null;
    this.tsfcChart = null;
    this.currentMode = 'wet';
    this.currentAlt = 0;
    this.currentDts = 0;
    this.currentThrottle = 3800;
  }

  async init() {
    this.initCharts();
    await this.loadDecksList();
    await this.loadDeckData();
    this.setupEventListeners();
  }

  initCharts() {
    const thrustCanvas = document.getElementById('thrustChart');
    if (thrustCanvas) {
      this.thrustChart = new InteractiveChart(thrustCanvas, {
        title: 'Operating Line: Net Thrust vs Throttle',
        xLabel: 'Throttle Temp',
        yLabel: 'Net Thrust',
        xUnit: 'degR',
        yUnit: 'lbf',
      });
    }

    const tsfcCanvas = document.getElementById('tsfcChart');
    if (tsfcCanvas) {
      this.tsfcChart = new InteractiveChart(tsfcCanvas, {
        title: 'Operating Loop: TSFC vs Net Thrust',
        xLabel: 'Net Thrust',
        yLabel: 'TSFC',
        xUnit: 'lbf',
        yUnit: 'lbm/hr/lbf',
      });
    }

    window.addEventListener('resize', () => {
      this.updateCharts();
    });
  }

  async loadDecksList() {
    try {
      const res = await fetch('/api/decks');
      if (!res.ok) return;
      const data = await res.json();
      const select = document.getElementById('deckSelect');
      if (!select) return;

      select.innerHTML = '';
      const decks = data.decks || [];
      for (const d of decks) {
        const opt = document.createElement('option');
        opt.value = d.path;
        opt.textContent = `${d.name} (${(d.size_bytes / 1024).toFixed(1)} KB)`;
        if (data.active_deck === d.path) {
          opt.selected = true;
        }
        select.appendChild(opt);
      }

      select.addEventListener('change', async () => {
        await this.loadDeckData(select.value);
      });
    } catch (e) {
      console.warn('Could not load decks list', e);
    }
  }

  async loadDeckData(path) {
    const url = path ? `/api/deck-data?path=${encodeURIComponent(path)}` : '/api/deck-data';
    try {
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to load deck data: ${res.statusText}`);
      }
      const payload = await res.json();
      this.interpolator = new ClientDeckInterpolator(payload);

      const modes = this.interpolator.getModes();
      this.setupModeToggles(modes);

      const mode = modes.includes('wet') ? 'wet' : modes[0];
      this.setMode(mode);
    } catch (e) {
      console.error('Deck load error:', e);
      this.showError(`Error loading deck: ${e}`);
    }
  }

  setupModeToggles(modes) {
    const container = document.getElementById('modeToggleContainer');
    if (!container) return;

    container.innerHTML = '';
    for (const m of modes) {
      const btn = document.createElement('button');
      btn.className = `px-3 py-1 text-xs font-semibold rounded-md border transition-all cursor-pointer ${
        m === this.currentMode
          ? 'bg-sky-500 text-white border-sky-400 shadow-sm'
          : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
      }`;
      btn.textContent = m.toUpperCase();
      btn.addEventListener('click', () => {
        this.setMode(m);
      });
      container.appendChild(btn);
    }
  }

  setMode(mode) {
    this.currentMode = mode;
    this.interpolator?.setMode(mode);

    const container = document.getElementById('modeToggleContainer');
    if (container) {
      const buttons = container.querySelectorAll('button');
      buttons.forEach((b) => {
        if (b.textContent?.toLowerCase() === mode) {
          b.className = 'px-3 py-1 text-xs font-semibold rounded-md border bg-sky-500 text-white border-sky-400 shadow-sm cursor-pointer';
        } else {
          b.className = 'px-3 py-1 text-xs font-semibold rounded-md border bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700 cursor-pointer';
        }
      });
    }

    this.configureSlidersForMode(mode);
    this.evaluate();
  }

  configureSlidersForMode(mode) {
    if (!this.interpolator) return;
    const modeData = this.interpolator.getModeData(mode);
    const axes = modeData.axes;

    const altSlider = document.getElementById('altSlider');
    const altVal = document.getElementById('altValue');
    if (altSlider) {
      altSlider.min = axes.alt.min.toString();
      altSlider.max = axes.alt.max.toString();
      altSlider.step = (axes.alt.values.length > 1 ? Math.min(250, (axes.alt.max - axes.alt.min) / 10) : 100).toString();
      altSlider.value = axes.alt.min.toString();
      this.currentAlt = axes.alt.min;
      if (altVal) altVal.textContent = `${this.currentAlt.toFixed(0)} ft`;
    }

    const dtsSlider = document.getElementById('dtsSlider');
    const dtsVal = document.getElementById('dtsValue');
    if (dtsSlider) {
      dtsSlider.min = axes.dTs.min.toString();
      dtsSlider.max = axes.dTs.max.toString();
      dtsSlider.step = '1';
      this.currentDts = Math.max(axes.dTs.min, Math.min(axes.dTs.max, 0));
      dtsSlider.value = this.currentDts.toString();
      if (dtsVal) dtsVal.textContent = `${this.currentDts >= 0 ? '+' : ''}${this.currentDts.toFixed(0)} °R`;
    }

    const thrSlider = document.getElementById('thrSlider');
    const thrVal = document.getElementById('thrValue');
    const thrLabel = document.getElementById('thrLabel');
    if (thrSlider) {
      thrSlider.min = axes.throttle.min.toString();
      thrSlider.max = axes.throttle.max.toString();
      thrSlider.step = '10';
      thrSlider.value = axes.throttle.max.toString();
      this.currentThrottle = axes.throttle.max;
      if (thrLabel) {
        thrLabel.textContent = mode === 'wet' ? 'Throttle (T7 Augmentor Exit)' : 'Throttle (T4 Turbine Inlet)';
      }
      if (thrVal) thrVal.textContent = `${this.currentThrottle.toFixed(0)} °R`;
    }
  }

  setupEventListeners() {
    const altSlider = document.getElementById('altSlider');
    const altVal = document.getElementById('altValue');
    altSlider?.addEventListener('input', () => {
      this.currentAlt = parseFloat(altSlider.value);
      if (altVal) altVal.textContent = `${this.currentAlt.toFixed(0)} ft`;
      this.evaluate();
    });

    const dtsSlider = document.getElementById('dtsSlider');
    const dtsVal = document.getElementById('dtsValue');
    dtsSlider?.addEventListener('input', () => {
      this.currentDts = parseFloat(dtsSlider.value);
      if (dtsVal) dtsVal.textContent = `${this.currentDts >= 0 ? '+' : ''}${this.currentDts.toFixed(0)} °R`;
      this.evaluate();
    });

    const thrSlider = document.getElementById('thrSlider');
    const thrVal = document.getElementById('thrValue');
    thrSlider?.addEventListener('input', () => {
      this.currentThrottle = parseFloat(thrSlider.value);
      if (thrVal) thrVal.textContent = `${this.currentThrottle.toFixed(0)} °R`;
      this.evaluate();
    });

    const resetBtn = document.getElementById('resetBtn');
    resetBtn?.addEventListener('click', () => {
      this.resetToDesignPoint();
    });
  }

  resetToDesignPoint() {
    if (!this.interpolator) return;
    const modeData = this.interpolator.getModeData(this.currentMode);
    const axes = modeData.axes;

    this.currentAlt = 0;
    this.currentDts = 0;
    this.currentThrottle = axes.throttle.max;

    const altSlider = document.getElementById('altSlider');
    if (altSlider) altSlider.value = '0';
    const altVal = document.getElementById('altValue');
    if (altVal) altVal.textContent = '0 ft';

    const dtsSlider = document.getElementById('dtsSlider');
    if (dtsSlider) dtsSlider.value = '0';
    const dtsVal = document.getElementById('dtsValue');
    if (dtsVal) dtsVal.textContent = '+0 °R';

    const thrSlider = document.getElementById('thrSlider');
    if (thrSlider) thrSlider.value = axes.throttle.max.toString();
    const thrVal = document.getElementById('thrValue');
    if (thrVal) thrVal.textContent = `${axes.throttle.max.toFixed(0)} °R`;

    this.evaluate();
  }

  evaluate() {
    if (!this.interpolator) return;

    const res = this.interpolator.interpolate(
      this.currentAlt,
      this.currentDts,
      this.currentThrottle,
      this.currentMode
    );

    this.updateReadouts(res);
    this.updateCharts();
  }

  updateReadouts(res) {
    const o = res.outputs;

    const fmt = (val, dec = 2, mult = 1) => {
      if (val === null || val === undefined || !isFinite(val)) return '—';
      return (val * mult).toFixed(dec);
    };

    const setText = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };

    const fn = o['Fn'] ?? 0;
    setText('outFn', fmt(fn, 1));
    setText('outFnKn', `${fmt(fn, 2, 0.00444822)} kN`);

    const fg = o['Fg'] ?? 0;
    setText('outFg', `${fmt(fg, 1)} lbf`);

    const tsfc = o['TSFC'] ?? 0;
    setText('outTsfc', fmt(tsfc, 4));
    setText('outTsfcSi', `${fmt(tsfc, 2, 28.325)} g/(kN·s)`);

    const w = o['W'] ?? 0;
    setText('outW', fmt(w, 2));
    setText('outWKg', `${fmt(w, 2, 0.453592)} kg/s`);

    const wfTot = o['Wf_tot'] ?? 0;
    const wfPph = o['Wf_tot_pph'] ?? (wfTot * 3600);
    setText('outWf', fmt(wfTot, 3));
    setText('outWfPph', `${fmt(wfPph, 1)} lbm/hr`);

    const wfCore = o['Wf_core'] ?? 0;
    setText('outWfCore', `${fmt(wfCore, 3)}`);

    const wfAb = o['Wf_ab'] ?? 0;
    setText('outWfAb', `${fmt(wfAb, 3)}`);

    const a8 = o['A8'];
    if (a8 !== null && a8 !== undefined) {
      setText('outA8', fmt(a8, 2));
    } else {
      setText('outA8', '— (Schema pending)');
    }

    setText('outBpr', fmt(o['BPR'], 4));
    setText('outOpr', fmt(o['OPR'], 2));
    setText('outFanPr', fmt(o['fan_PR'], 3));
    setText('outHpcPr', fmt(o['hpc_PR'], 3));
    setText('outHptPr', fmt(o['hpt_PR'], 3));
    setText('outLptPr', fmt(o['lpt_PR'], 3));
    setText('outLpNmech', fmt(o['LP_Nmech'], 0));
    setText('outHpNmech', fmt(o['HP_Nmech'], 0));
    setText('outFarCore', fmt(o['FAR_core'], 5));
    setText('outFarAb', fmt(o['FAR_ab'], 5));

    setText('outT4', `${fmt(res.inputs.T4, 0)} °R`);
    setText('outT7', `${fmt(res.inputs.T7, 0)} °R`);

    const methodBadge = document.getElementById('methodBadge');
    if (methodBadge) {
      if (res.method === 'multilinear') {
        methodBadge.textContent = 'Trilinear Grid';
        methodBadge.className = 'px-2.5 py-1 text-xs font-mono font-medium rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800';
      } else if (res.method === 'exact') {
        methodBadge.textContent = 'Exact Node';
        methodBadge.className = 'px-2.5 py-1 text-xs font-mono font-medium rounded-full bg-blue-950/80 text-blue-400 border border-blue-800';
      } else {
        methodBadge.textContent = 'k-NN IDW Local';
        methodBadge.className = 'px-2.5 py-1 text-xs font-mono font-medium rounded-full bg-amber-950/80 text-amber-400 border border-amber-800';
      }
    }

    this.updateCornerTable(res);
  }

  updateCornerTable(res) {
    const tbody = document.getElementById('cornersTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    for (const c of res.corners) {
      const row = document.createElement('tr');
      row.className = 'border-b border-slate-800/60 hover:bg-slate-800/40 text-xs font-mono';
      row.innerHTML = `
        <td class="py-1 px-2 text-slate-300">${c.alt.toFixed(0)}</td>
        <td class="py-1 px-2 text-slate-300">${c.dTs >= 0 ? '+' : ''}${c.dTs.toFixed(0)}</td>
        <td class="py-1 px-2 text-slate-300">${c.throttle.toFixed(0)}</td>
        <td class="py-1 px-2 text-sky-400 font-semibold text-right">${(c.weight * 100).toFixed(1)}%</td>
      `;
      tbody.appendChild(row);
    }
  }

  updateCharts() {
    if (!this.interpolator) return;
    const modeData = this.interpolator.getModeData(this.currentMode);
    const axes = modeData.axes;

    const steps = 15;
    const thrMin = axes.throttle.min;
    const thrMax = axes.throttle.max;
    const thrStep = (thrMax - thrMin) / steps;

    const currentLinePoints = [];
    const tsfcPoints = [];

    for (let i = 0; i <= steps; i++) {
      const th = thrMin + i * thrStep;
      const pt = this.interpolator.interpolate(this.currentAlt, this.currentDts, th, this.currentMode);
      const fn = pt.outputs['Fn'];
      const tsfc = pt.outputs['TSFC'];
      if (fn !== null && fn !== undefined) {
        currentLinePoints.push({ x: th, y: fn });
        if (tsfc !== null && tsfc !== undefined) {
          tsfcPoints.push({ x: fn, y: tsfc });
        }
      }
    }

    const currentPt = this.interpolator.interpolate(
      this.currentAlt,
      this.currentDts,
      this.currentThrottle,
      this.currentMode
    );
    const curFn = currentPt.outputs['Fn'] ?? 0;
    const curTsfc = currentPt.outputs['TSFC'] ?? 0;

    if (this.thrustChart) {
      this.thrustChart.setData(
        [
          {
            name: `Alt ${this.currentAlt.toFixed(0)} ft, dT ${this.currentDts.toFixed(0)} °R`,
            points: currentLinePoints,
            color: '#38bdf8',
            lineWidth: 2.5,
          },
        ],
        { x: this.currentThrottle, y: curFn }
      );
    }

    if (this.tsfcChart) {
      this.tsfcChart.setData(
        [
          {
            name: `TSFC Loop`,
            points: tsfcPoints,
            color: '#34d399',
            lineWidth: 2.5,
          },
        ],
        { x: curFn, y: curTsfc }
      );
    }
  }

  showError(msg) {
    const banner = document.getElementById('errorBanner');
    if (banner) {
      banner.textContent = msg;
      banner.classList.remove('hidden');
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const app = new F404DeckApp();
  window.f404App = app;
  app.init();
});
