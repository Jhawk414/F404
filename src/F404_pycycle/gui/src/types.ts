/**
 * TypeScript definitions for the GE F404 cycle deck viewer and interpolator.
 */

export type EngineMode = 'dry' | 'wet' | string;

export interface AxisMeta {
  min: number;
  max: number;
  values: number[];
  single: boolean;
}

export interface ModeAxes {
  throttle_col: string;
  alt: AxisMeta;
  dTs: AxisMeta;
  throttle: AxisMeta;
  MN: AxisMeta;
}

export type DeckPoint = Record<string, number | null>;

export interface DeckModeData {
  throttle_col: string;
  axes: ModeAxes;
  points_count: number;
  columns: string[];
  points: DeckPoint[];
}

export interface DeckPayload {
  modes: EngineMode[];
  default_mode: EngineMode;
  deck_file?: string;
  deck_data: Record<EngineMode, DeckModeData>;
}

export interface OperatingPointInputs {
  mode: EngineMode;
  alt: number;
  dTs: number;
  throttle: number;
  throttle_col: string;
  T4: number;
  T7: number;
  MN: number;
}

export interface InterpolationCorner {
  alt: number;
  dTs: number;
  throttle: number;
  weight: number;
}

export interface InterpolationResult {
  inputs: OperatingPointInputs;
  outputs: Record<string, number | null>;
  method: 'multilinear' | 'exact' | 'idw';
  corners: InterpolationCorner[];
}

export interface DeckFileInfo {
  name: string;
  path: string;
  rel_path: string;
  size_bytes: number;
}
