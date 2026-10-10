/**
 * Client-side cycle deck interpolator in TypeScript.
 *
 * Implements high-performance trilinear tensor-product interpolation with
 * normalized k-NN Inverse Distance Weighting fallback and derived propulsion
 * parameters (fuel flows, mass flow breakdowns, pressure ratios).
 */

import {
  DeckModeData,
  DeckPayload,
  DeckPoint,
  EngineMode,
  InterpolationCorner,
  InterpolationResult,
  OperatingPointInputs,
} from './types';

export class ClientDeckInterpolator {
  private payload: DeckPayload;
  private currentMode: EngineMode;

  constructor(payload: DeckPayload) {
    this.payload = payload;
    this.currentMode = payload.default_mode || payload.modes[0] || 'wet';
  }

  public getModes(): EngineMode[] {
    return this.payload.modes;
  }

  public getMode(): EngineMode {
    return this.currentMode;
  }

  public setMode(mode: EngineMode): void {
    if (this.payload.deck_data[mode]) {
      this.currentMode = mode;
    }
  }

  public getModeData(mode: EngineMode = this.currentMode): DeckModeData {
    const data = this.payload.deck_data[mode];
    if (!data) {
      throw new Error(`Mode '${mode}' not found in cycle deck.`);
    }
    return data;
  }

  /**
   * Interpolate all deck parameters at the given (alt, dTs, throttle) operating point.
   */
  public interpolate(
    alt: number,
    dTs: number,
    throttle: number,
    mode: EngineMode = this.currentMode
  ): InterpolationResult {
    const modeData = this.getModeData(mode);
    const axes = modeData.axes;
    const throttleCol = axes.throttle_col;

    const t4 = mode === 'wet' ? 3100.0 : throttle;
    const t7 = mode === 'wet' ? throttle : (modeData.points[0]?.['T7'] ?? t4);
    const mn = axes.MN?.values?.[0] ?? 0.001;

    const altVals = axes.alt.values;
    const dtsVals = axes.dTs.values;
    const thrVals = axes.throttle.values;

    // Attempt trilinear interpolation first
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

    let outputs: Record<string, number | null>;
    let method: 'multilinear' | 'exact' | 'idw';
    let corners: InterpolationCorner[];

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

    // Add derived propulsion quantities
    this.addDerivedQuantities(outputs, mode, alt, dTs, throttle);

    const inputs: OperatingPointInputs = {
      mode,
      alt,
      dTs,
      throttle,
      throttle_col: throttleCol,
      T4: t4,
      T7: t7,
      MN: mn,
    };

    return {
      inputs,
      outputs,
      method,
      corners,
    };
  }

  private tryMultilinear(
    modeData: DeckModeData,
    altVals: number[],
    dtsVals: number[],
    thrVals: number[],
    throttleCol: string,
    alt: number,
    dTs: number,
    throttle: number
  ): { outputs: Record<string, number | null>; corners: InterpolationCorner[] } | null {
    const [iAlt0, iAlt1, tAlt] = this.findInterval(altVals, alt);
    const [iDts0, iDts1, tDts] = this.findInterval(dtsVals, dTs);
    const [iThr0, iThr1, tThr] = this.findInterval(thrVals, throttle);

    const gAlt = [altVals[iAlt0], altVals[iAlt1]];
    const gDts = [dtsVals[iDts0], dtsVals[iDts1]];
    const gThr = [thrVals[iThr0], thrVals[iThr1]];

    const wAlt = [1.0 - tAlt, tAlt];
    const wDts = [1.0 - tDts, tDts];
    const wThr = [1.0 - tThr, tThr];

    // Build key lookup
    const lookup = new Map<string, DeckPoint>();
    for (const pt of modeData.points) {
      const key = `${pt['alt']}_${pt['dTs']}_${pt[throttleCol]}`;
      lookup.set(key, pt);
    }

    const corners: DeckPoint[] = [];
    const cornerWeights: number[] = [];

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

    const outputs: Record<string, number | null> = {};
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

    const cornerInfo: InterpolationCorner[] = corners
      .map((c, i) => ({
        alt: Number(c['alt']),
        dTs: Number(c['dTs']),
        throttle: Number(c[throttleCol]),
        weight: cornerWeights[i] / totalWeight,
      }))
      .filter((c) => c.weight > 1e-6);

    return { outputs, corners: cornerInfo };
  }

  private findInterval(vals: number[], x: number): [number, number, number] {
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

  private idwInterpolate(
    modeData: DeckModeData,
    throttleCol: string,
    alt: number,
    dTs: number,
    throttle: number,
    k: number = 8,
    power: number = 2.0
  ): {
    outputs: Record<string, number | null>;
    method: 'exact' | 'idw';
    corners: InterpolationCorner[];
  } {
    const axes = modeData.axes;
    const altSpan = Math.max(1.0, axes.alt.max - axes.alt.min);
    const dtsSpan = Math.max(1.0, axes.dTs.max - axes.dTs.min);
    const thrSpan = Math.max(1.0, axes.throttle.max - axes.throttle.min);

    const qAlt = (alt - axes.alt.min) / altSpan;
    const qDts = (dTs - axes.dTs.min) / dtsSpan;
    const qThr = (throttle - axes.throttle.min) / thrSpan;

    const points = modeData.points;
    const dists: { dist: number; index: number }[] = [];

    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      const pAlt = (Number(p['alt']) - axes.alt.min) / altSpan;
      const pDts = (Number(p['dTs']) - axes.dTs.min) / dtsSpan;
      const pThr = (Number(p[throttleCol]) - axes.throttle.min) / thrSpan;

      const d = Math.sqrt(
        (pAlt - qAlt) ** 2 + (pDts - qDts) ** 2 + (pThr - qThr) ** 2
      );

      if (d < 1e-6) {
        // Exact match
        const outputs: Record<string, number | null> = {};
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
    const weights: number[] = [];
    for (const item of topK) {
      const w = 1.0 / item.dist ** power;
      weights.push(w);
      sumWeights += w;
    }

    const normWeights = weights.map((w) => w / (sumWeights || 1.0));
    const outputs: Record<string, number | null> = {};

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

    const cornerInfo: InterpolationCorner[] = topK.map((item, i) => {
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

  private addDerivedQuantities(
    outputs: Record<string, number | null>,
    mode: EngineMode,
    _alt: number,
    _dTs: number,
    _throttle: number
  ): void {
    const fn = outputs['Fn'] ?? 0;
    const tsfc = outputs['TSFC'] ?? 0;
    const w = outputs['W'] ?? 0;
    const bpr = outputs['BPR'] ?? 0;
    const farCore = outputs['FAR_core'] ?? 0;
    const farAb = outputs['FAR_ab'] ?? 0;

    // Fuel flows
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

    // A8 nozzle area
    if (outputs['A8'] === undefined) {
      outputs['A8'] = null;
    }
  }
}
