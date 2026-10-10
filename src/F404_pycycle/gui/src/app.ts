/**
 * Main application coordinator for the F404 cycle deck interactive GUI.
 */

import { ClientDeckInterpolator } from './interpolator';
import { InteractiveChart } from './charts';
import {
  DeckFileInfo,
  DeckPayload,
  EngineMode,
  InterpolationResult,
} from './types';

export class F404DeckApp {
  private interpolator: ClientDeckInterpolator | null = null;
  private thrustChart: InteractiveChart | null = null;
  private tsfcChart: InteractiveChart | null = null;
  private currentMode: EngineMode = 'wet';
  private currentAlt: number = 0;
  private currentDts: number = 0;
  private currentThrottle: number = 3800;

  public async init(): Promise<void> {
    this.initCharts();
    await this.loadDecksList();
    await this.loadDeckData();
    this.setupEventListeners();
  }

  private initCharts(): void {
    const thrustCanvas = document.getElementById('thrustChart') as HTMLCanvasElement;
    if (thrustCanvas) {
      this.thrustChart = new InteractiveChart(thrustCanvas, {
        title: 'Operating Line: Net Thrust vs Throttle',
        xLabel: 'Throttle Temperature',
        yLabel: 'Net Thrust',
        xUnit: 'degR',
        yUnit: 'lbf',
      });
    }

    const tsfcCanvas = document.getElementById('tsfcChart') as HTMLCanvasElement;
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

  private async loadDecksList(): Promise<void> {
    try {
      const res = await fetch('/api/decks');
      if (!res.ok) return;
      const data = await res.json();
      const select = document.getElementById('deckSelect') as HTMLSelectElement;
      if (!select) return;

      select.innerHTML = '';
      const decks: DeckFileInfo[] = data.decks || [];
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

  public async loadDeckData(path?: string): Promise<void> {
    const url = path ? `/api/deck-data?path=${encodeURIComponent(path)}` : '/api/deck-data';
    try {
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to load deck data: ${res.statusText}`);
      }
      const payload: DeckPayload = await res.json();
      this.interpolator = new ClientDeckInterpolator(payload);

      // Determine initial mode
      const modes = this.interpolator.getModes();
      this.setupModeToggles(modes);

      const mode = modes.includes('wet') ? 'wet' : modes[0];
      this.setMode(mode);
    } catch (e) {
      console.error('Deck load error:', e);
      this.showError(`Error loading deck: ${e}`);
    }
  }

  private setupModeToggles(modes: EngineMode[]): void {
    const container = document.getElementById('modeToggleContainer');
    if (!container) return;

    container.innerHTML = '';
    for (const m of modes) {
      const btn = document.createElement('button');
      btn.className = `px-3 py-1 text-xs font-semibold rounded-md border transition-all ${
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

  public setMode(mode: EngineMode): void {
    this.currentMode = mode;
    this.interpolator?.setMode(mode);

    // Update UI toggle buttons
    const container = document.getElementById('modeToggleContainer');
    if (container) {
      const buttons = container.querySelectorAll('button');
      buttons.forEach((b) => {
        if (b.textContent?.toLowerCase() === mode) {
          b.className = 'px-3 py-1 text-xs font-semibold rounded-md border bg-sky-500 text-white border-sky-400 shadow-sm';
        } else {
          b.className = 'px-3 py-1 text-xs font-semibold rounded-md border bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700';
        }
      });
    }

    this.configureSlidersForMode(mode);
    this.evaluate();
  }

  private configureSlidersForMode(mode: EngineMode): void {
    if (!this.interpolator) return;
    const modeData = this.interpolator.getModeData(mode);
    const axes = modeData.axes;

    // Alt slider
    const altSlider = document.getElementById('altSlider') as HTMLInputElement;
    const altVal = document.getElementById('altValue') as HTMLElement;
    if (altSlider) {
      altSlider.min = axes.alt.min.toString();
      altSlider.max = axes.alt.max.toString();
      altSlider.step = (axes.alt.values.length > 1 ? Math.min(250, (axes.alt.max - axes.alt.min) / 10) : 100).toString();
      altSlider.value = axes.alt.min.toString();
      this.currentAlt = axes.alt.min;
      if (altVal) altVal.textContent = `${this.currentAlt.toFixed(0)} ft`;
    }

    // dTs slider
    const dtsSlider = document.getElementById('dtsSlider') as HTMLInputElement;
    const dtsVal = document.getElementById('dtsValue') as HTMLElement;
    if (dtsSlider) {
      dtsSlider.min = axes.dTs.min.toString();
      dtsSlider.max = axes.dTs.max.toString();
      dtsSlider.step = '1';
      dtsSlider.value = '0';
      this.currentDts = Math.max(axes.dTs.min, Math.min(axes.dTs.max, 0));
      dtsSlider.value = this.currentDts.toString();
      if (dtsVal) dtsVal.textContent = `${this.currentDts >= 0 ? '+' : ''}${this.currentDts.toFixed(0)} °R`;
    }

    // Throttle slider
    const thrSlider = document.getElementById('thrSlider') as HTMLInputElement;
    const thrVal = document.getElementById('thrValue') as HTMLElement;
    const thrLabel = document.getElementById('thrLabel') as HTMLElement;
    if (thrSlider) {
      thrSlider.min = axes.throttle.min.toString();
      thrSlider.max = axes.throttle.max.toString();
      thrSlider.step = '10';
      thrSlider.value = axes.throttle.max.toString();
      this.currentThrottle = axes.throttle.max;
      if (thrLabel) {
        thrLabel.textContent = mode === 'wet' ? 'Augmentor Exit Temp (T7)' : 'Turbine Inlet Temp (T4)';
      }
      if (thrVal) thrVal.textContent = `${this.currentThrottle.toFixed(0)} °R`;
    }
  }

  private setupEventListeners(): void {
    const altSlider = document.getElementById('altSlider') as HTMLInputElement;
    const altVal = document.getElementById('altValue') as HTMLElement;
    altSlider?.addEventListener('input', () => {
      this.currentAlt = parseFloat(altSlider.value);
      if (altVal) altVal.textContent = `${this.currentAlt.toFixed(0)} ft`;
      this.evaluate();
    });

    const dtsSlider = document.getElementById('dtsSlider') as HTMLInputElement;
    const dtsVal = document.getElementById('dtsValue') as HTMLElement;
    dtsSlider?.addEventListener('input', () => {
      this.currentDts = parseFloat(dtsSlider.value);
      if (dtsVal) dtsVal.textContent = `${this.currentDts >= 0 ? '+' : ''}${this.currentDts.toFixed(0)} °R`;
      this.evaluate();
    });

    const thrSlider = document.getElementById('thrSlider') as HTMLInputElement;
    const thrVal = document.getElementById('thrValue') as HTMLElement;
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

  public resetToDesignPoint(): void {
    if (!this.interpolator) return;
    const modeData = this.interpolator.getModeData(this.currentMode);
    const axes = modeData.axes;

    this.currentAlt = 0;
    this.currentDts = 0;
    this.currentThrottle = axes.throttle.max;

    const altSlider = document.getElementById('altSlider') as HTMLInputElement;
    if (altSlider) altSlider.value = '0';
    const altVal = document.getElementById('altValue') as HTMLElement;
    if (altVal) altVal.textContent = '0 ft';

    const dtsSlider = document.getElementById('dtsSlider') as HTMLInputElement;
    if (dtsSlider) dtsSlider.value = '0';
    const dtsVal = document.getElementById('dtsValue') as HTMLElement;
    if (dtsVal) dtsVal.textContent = '+0 °R';

    const thrSlider = document.getElementById('thrSlider') as HTMLInputElement;
    if (thrSlider) thrSlider.value = axes.throttle.max.toString();
    const thrVal = document.getElementById('thrValue') as HTMLElement;
    if (thrVal) thrVal.textContent = `${axes.throttle.max.toFixed(0)} °R`;

    this.evaluate();
  }

  public evaluate(): void {
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

  private updateReadouts(res: InterpolationResult): void {
    const o = res.outputs;

    // Helper formatter
    const fmt = (val: number | null | undefined, dec = 2, mult = 1) => {
      if (val === null || val === undefined || !isFinite(val)) return '—';
      return (val * mult).toFixed(dec);
    };

    // Primary cards
    const setText = (id: string, text: string) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };

    const fn = o['Fn'] ?? 0;
    setText('outFn', fmt(fn, 1));
    setText('outFnKn', `${fmt(fn, 2, 0.00444822)} kN`);

    const fg = o['Fg'] ?? 0;
    setText('outFg', fmt(fg, 1));

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
    setText('outWfCore', `${fmt(wfCore, 3)} lbm/s`);

    const wfAb = o['Wf_ab'] ?? 0;
    setText('outWfAb', `${fmt(wfAb, 3)} lbm/s`);

    // Nozzle Area A8
    const a8 = o['A8'];
    if (a8 !== null && a8 !== undefined) {
      setText('outA8', fmt(a8, 2));
    } else {
      setText('outA8', '— (Schema pending)');
    }

    // Aeromechanical & thermodynamic cycle
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

    // Temperatures
    setText('outT4', `${fmt(res.inputs.T4, 0)} °R`);
    setText('outT7', `${fmt(res.inputs.T7, 0)} °R`);

    // Status pill
    const methodBadge = document.getElementById('methodBadge');
    if (methodBadge) {
      if (res.method === 'multilinear') {
        methodBadge.textContent = 'Trilinear Grid';
        methodBadge.className = 'px-2 py-0.5 text-xs font-medium rounded-full bg-emerald-900/60 text-emerald-400 border border-emerald-700/50';
      } else if (res.method === 'exact') {
        methodBadge.textContent = 'Exact Node';
        methodBadge.className = 'px-2 py-0.5 text-xs font-medium rounded-full bg-blue-900/60 text-blue-400 border border-blue-700/50';
      } else {
        methodBadge.textContent = 'k-NN IDW Local';
        methodBadge.className = 'px-2 py-0.5 text-xs font-medium rounded-full bg-amber-900/60 text-amber-400 border border-amber-700/50';
      }
    }

    // Corner table inspection
    this.updateCornerTable(res);
  }

  private updateCornerTable(res: InterpolationResult): void {
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
        <td class="py-1 px-2 text-sky-400 font-semibold">${(c.weight * 100).toFixed(1)}%</td>
      `;
      tbody.appendChild(row);
    }
  }

  private updateCharts(): void {
    if (!this.interpolator) return;
    const modeData = this.interpolator.getModeData(this.currentMode);
    const axes = modeData.axes;
    const thrVals = axes.throttle.values;

    // Generate curve across throttle at current alt and dTs
    const steps = 15;
    const thrMin = axes.throttle.min;
    const thrMax = axes.throttle.max;
    const thrStep = (thrMax - thrMin) / steps;

    const currentLinePoints: { x: number; y: number }[] = [];
    const tsfcPoints: { x: number; y: number }[] = [];

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

    // Active operating points
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
            color: '#38bdf8', // sky-400
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
            color: '#34d399', // emerald-400
            lineWidth: 2.5,
          },
        ],
        { x: curFn, y: curTsfc }
      );
    }
  }

  private showError(msg: string): void {
    const banner = document.getElementById('errorBanner');
    if (banner) {
      banner.textContent = msg;
      banner.classList.remove('hidden');
    }
  }
}

// Browser bootstrap
declare global {
  interface Window {
    f404App: F404DeckApp;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const app = new F404DeckApp();
  window.f404App = app;
  app.init();
});
