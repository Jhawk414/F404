"""Cycle-deck loader and multidimensional interpolator.

Provides fast interpolation across altitude, ISA temperature offset (dTs),
and throttle (T4 in dry mode, T7 in wet mode) from pre-computed cycle decks,
without needing OpenMDAO or numerical solvers at evaluation time.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


class DeckInterpolator:
    """Multidimensional interpolator for F404 cycle decks.

    Supports rectilinear tensor-product trilinear interpolation with a robust
    normalized k-nearest-neighbors Inverse Distance Weighting (IDW) fallback
    for non-tensor-product boundaries or missing points.
    """

    def __init__(self, data: Union[str, Path, pd.DataFrame, List[Union[str, Path]]]):
        if isinstance(data, (str, Path)):
            self.df = self._load_path(Path(data))
        elif isinstance(data, list):
            dfs = [self._load_path(Path(p)) for p in data]
            self.df = pd.concat(dfs, ignore_index=True)
        elif isinstance(data, pd.DataFrame):
            self.df = data.copy()
        else:
            raise TypeError(f"Unsupported data source type: {type(data)}")

        self._validate_and_normalize()
        self._build_index()

    @staticmethod
    def _load_path(path: Path) -> pd.DataFrame:
        if path.is_file():
            return pd.read_csv(path)
        if path.is_dir():
            csv_files = sorted(path.glob("cycle_deck_*.csv"))
            if not csv_files:
                csv_files = sorted(path.glob("*.csv"))
            if not csv_files:
                raise FileNotFoundError(f"No CSV deck files found in directory {path}")
            dfs = [pd.read_csv(f) for f in csv_files]
            return pd.concat(dfs, ignore_index=True)
        raise FileNotFoundError(f"Deck path does not exist: {path}")

    def _validate_and_normalize(self) -> None:
        required_cols = {'alt', 'dTs'}
        if not required_cols.issubset(self.df.columns):
            missing = required_cols - set(self.df.columns)
            raise ValueError(f"Cycle deck missing required columns: {missing}")

        if 'mode' not in self.df.columns:
            # Infer mode from T7: if T7 is swept or >= 3200, assume wet; otherwise dry
            if 'T7' in self.df.columns and (self.df['T7'] > 3100).any():
                self.df['mode'] = 'wet'
            else:
                self.df['mode'] = 'dry'

        # Ensure numeric columns are floats
        for col in self.df.columns:
            if col != 'mode':
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

        # Drop duplicates if any
        sort_cols = [c for c in ['mode', 'alt', 'dTs', 'T4', 'T7', 'MN'] if c in self.df.columns]
        if sort_cols:
            self.df = self.df.drop_duplicates(subset=sort_cols).reset_index(drop=True)

    def _build_index(self) -> None:
        self.modes = sorted(self.df['mode'].dropna().unique().tolist())
        self._mode_data: Dict[str, pd.DataFrame] = {}
        self._mode_axes: Dict[str, Dict[str, Any]] = {}

        for mode in self.modes:
            mdf = self.df[self.df['mode'] == mode].copy()
            self._mode_data[mode] = mdf

            throttle_col = 'T7' if mode == 'wet' else 'T4'
            if throttle_col not in mdf.columns:
                # Fallback if specific column is absent
                throttle_col = 'T4' if 'T4' in mdf.columns else 'T7'

            axes: Dict[str, Any] = {
                'throttle_col': throttle_col,
                'alt': self._axis_meta(mdf['alt']),
                'dTs': self._axis_meta(mdf['dTs']),
                'throttle': self._axis_meta(mdf[throttle_col]),
            }

            if 'MN' in mdf.columns and len(mdf['MN'].unique()) > 1:
                axes['MN'] = self._axis_meta(mdf['MN'])
            else:
                default_mn = float(mdf['MN'].iloc[0]) if 'MN' in mdf.columns and len(mdf) > 0 else 0.001
                axes['MN'] = {'min': default_mn, 'max': default_mn, 'values': [default_mn], 'single': True}

            self._mode_axes[mode] = axes

    @staticmethod
    def _axis_meta(series: pd.Series) -> Dict[str, Any]:
        vals = sorted(series.dropna().unique().tolist())
        return {
            'min': float(vals[0]) if vals else 0.0,
            'max': float(vals[-1]) if vals else 0.0,
            'values': [float(v) for v in vals],
            'single': len(vals) <= 1,
        }

    def get_modes(self) -> List[str]:
        """Return list of engine modes present in the deck ('dry', 'wet')."""
        return list(self.modes)

    def get_axes(self, mode: Optional[str] = None) -> Dict[str, Any]:
        """Return operating ranges and grid points for the requested mode."""
        if mode is None:
            mode = self.modes[0]
        if mode not in self._mode_axes:
            raise ValueError(f"Unknown mode '{mode}'. Available: {self.modes}")
        return self._mode_axes[mode]

    def get_output_columns(self, mode: Optional[str] = None) -> List[str]:
        """Return list of output columns available in the deck."""
        if mode is None:
            mode = self.modes[0]
        mdf = self._mode_data[mode]
        skip = {'alt', 'dTs', 'T4', 'T7', 'MN', 'mode'}
        return [c for c in mdf.columns if c not in skip]

    def interpolate(
        self,
        mode: str,
        alt: float,
        dTs: float,
        throttle: float,
        mn: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Interpolate all deck parameters at the specified operating point."""
        if mode not in self._mode_data:
            if len(self.modes) == 1:
                mode = self.modes[0]
            else:
                raise ValueError(f"Mode '{mode}' not in deck. Available: {self.modes}")

        mdf = self._mode_data[mode]
        axes = self._mode_axes[mode]
        throttle_col = axes['throttle_col']

        # Determine T4 and T7 values for input tracking
        if mode == 'wet':
            t7 = throttle
            t4 = float(mdf['T4'].iloc[0]) if 'T4' in mdf.columns else 3100.0
        else:
            t4 = throttle
            t7 = float(mdf['T7'].iloc[0]) if 'T7' in mdf.columns else t4

        if mn is None:
            mn = axes['MN']['values'][0] if axes['MN']['values'] else 0.001

        # Coordinate axes: (alt, dTs, throttle)
        alt_vals = axes['alt']['values']
        dts_vals = axes['dTs']['values']
        thr_vals = axes['throttle']['values']

        # Try multilinear interpolation first
        multilinear_result = self._try_multilinear(
            mdf, alt_vals, dts_vals, thr_vals, throttle_col, alt, dTs, throttle
        )

        if multilinear_result is not None:
            interp_outputs, method, points = multilinear_result
        else:
            # Fallback to normalized k-NN Inverse Distance Weighting
            interp_outputs, method, points = self._idw_interpolate(
                mdf, axes, throttle_col, alt, dTs, throttle
            )

        # Compute derived quantities if needed
        self._add_derived_quantities(interp_outputs, mode, alt, dTs, throttle, t4, t7)

        return {
            'inputs': {
                'mode': mode,
                'alt': float(alt),
                'dTs': float(dTs),
                'throttle': float(throttle),
                'throttle_col': throttle_col,
                'T4': float(t4),
                'T7': float(t7),
                'MN': float(mn),
            },
            'outputs': interp_outputs,
            'method': method,
            'corners': points,
        }

    def _try_multilinear(
        self,
        mdf: pd.DataFrame,
        alt_vals: List[float],
        dts_vals: List[float],
        thr_vals: List[float],
        throttle_col: str,
        alt: float,
        dTs: float,
        throttle: float,
    ) -> Optional[Tuple[Dict[str, float], str, List[Dict[str, Any]]]]:
        """Attempt trilinear interpolation on a bounding box."""
        i_alt0, i_alt1, t_alt = self._find_interval(alt_vals, alt)
        i_dts0, i_dts1, t_dts = self._find_interval(dts_vals, dTs)
        i_thr0, i_thr1, t_thr = self._find_interval(thr_vals, throttle)

        grid_alt = [alt_vals[i_alt0], alt_vals[i_alt1]]
        grid_dts = [dts_vals[i_dts0], dts_vals[i_dts1]]
        grid_thr = [thr_vals[i_thr0], thr_vals[i_thr1]]

        # 8 corners
        corners = []
        corner_weights = []

        w_alt = [1.0 - t_alt, t_alt]
        w_dts = [1.0 - t_dts, t_dts]
        w_thr = [1.0 - t_thr, t_thr]

        # Fast lookup map
        lookup = {}
        for _, row in mdf.iterrows():
            key = (row['alt'], row['dTs'], row[throttle_col])
            lookup[key] = row

        all_found = True
        for ia, a in enumerate(grid_alt):
            for idt, dt in enumerate(grid_dts):
                for ith, th in enumerate(grid_thr):
                    key = (a, dt, th)
                    if key not in lookup:
                        all_found = False
                        break
                    w = w_alt[ia] * w_dts[idt] * w_thr[ith]
                    corners.append(lookup[key])
                    corner_weights.append(w)
                if not all_found:
                    break
            if not all_found:
                break

        if not all_found or len(corners) == 0:
            return None

        # Interpolate all numeric columns
        numeric_cols = [c for c in mdf.select_dtypes(include=[np.number]).columns if c != 'mode']
        outputs: Dict[str, float] = {}

        total_weight = sum(corner_weights)
        if total_weight <= 0:
            total_weight = 1.0

        for col in numeric_cols:
            val = sum(w * c[col] for w, c in zip(corner_weights, corners)) / total_weight
            outputs[col] = float(val)

        point_info = [
            {
                'alt': float(c['alt']),
                'dTs': float(c['dTs']),
                'throttle': float(c[throttle_col]),
                'weight': float(w / total_weight),
            }
            for w, c in zip(corner_weights, corners)
            if w > 1e-6
        ]

        return outputs, 'multilinear', point_info

    @staticmethod
    def _find_interval(vals: List[float], x: float) -> Tuple[int, int, float]:
        if len(vals) == 1:
            return 0, 0, 0.0
        if x <= vals[0]:
            return 0, 0, 0.0
        if x >= vals[-1]:
            last = len(vals) - 1
            return last, last, 0.0

        for i in range(len(vals) - 1):
            if vals[i] <= x <= vals[i + 1]:
                span = vals[i + 1] - vals[i]
                t = (x - vals[i]) / span if span > 1e-12 else 0.0
                return i, i + 1, t

        return len(vals) - 2, len(vals) - 1, 1.0

    def _idw_interpolate(
        self,
        mdf: pd.DataFrame,
        axes: Dict[str, Any],
        throttle_col: str,
        alt: float,
        dTs: float,
        throttle: float,
        k: int = 8,
        power: float = 2.0,
    ) -> Tuple[Dict[str, float], str, List[Dict[str, Any]]]:
        """Normalized Inverse Distance Weighting across k nearest points."""
        alt_span = max(1.0, axes['alt']['max'] - axes['alt']['min'])
        dts_span = max(1.0, axes['dTs']['max'] - axes['dTs']['min'])
        thr_span = max(1.0, axes['throttle']['max'] - axes['throttle']['min'])

        q_alt = (alt - axes['alt']['min']) / alt_span
        q_dts = (dTs - axes['dTs']['min']) / dts_span
        q_thr = (throttle - axes['throttle']['min']) / thr_span

        p_alt = (mdf['alt'].to_numpy() - axes['alt']['min']) / alt_span
        p_dts = (mdf['dTs'].to_numpy() - axes['dTs']['min']) / dts_span
        p_thr = (mdf[throttle_col].to_numpy() - axes['throttle']['min']) / thr_span

        dists = np.sqrt((p_alt - q_alt) ** 2 + (p_dts - q_dts) ** 2 + (p_thr - q_thr) ** 2)

        # Exact match
        exact_match_idx = np.where(dists < 1e-6)[0]
        numeric_cols = [c for c in mdf.select_dtypes(include=[np.number]).columns if c != 'mode']

        if len(exact_match_idx) > 0:
            idx = exact_match_idx[0]
            row = mdf.iloc[idx]
            outputs = {col: float(row[col]) for col in numeric_cols}
            point_info = [{
                'alt': float(row['alt']),
                'dTs': float(row['dTs']),
                'throttle': float(row[throttle_col]),
                'weight': 1.0,
            }]
            return outputs, 'exact', point_info

        k = min(k, len(mdf))
        nearest_indices = np.argsort(dists)[:k]
        nearest_dists = dists[nearest_indices]

        weights = 1.0 / (nearest_dists ** power)
        weight_sum = np.sum(weights)
        norm_weights = weights / weight_sum

        outputs = {}
        for col in numeric_cols:
            vals = mdf[col].iloc[nearest_indices].to_numpy()
            outputs[col] = float(np.sum(norm_weights * vals))

        point_info = [
            {
                'alt': float(mdf['alt'].iloc[idx]),
                'dTs': float(mdf['dTs'].iloc[idx]),
                'throttle': float(mdf[throttle_col].iloc[idx]),
                'weight': float(nw),
            }
            for idx, nw in zip(nearest_indices, norm_weights)
        ]

        return outputs, 'idw', point_info

    def _add_derived_quantities(
        self,
        outputs: Dict[str, float],
        mode: str,
        alt: float,
        dTs: float,
        throttle: float,
        t4: float,
        t7: float,
    ) -> None:
        """Derive standard propulsion quantities like total fuel mass flow."""
        fn = outputs.get('Fn', 0.0)
        tsfc = outputs.get('TSFC', 0.0)
        w = outputs.get('W', 0.0)
        bpr = outputs.get('BPR', 0.0)
        far_core = outputs.get('FAR_core', 0.0)
        far_ab = outputs.get('FAR_ab', 0.0)

        # Total fuel flow in lbm/hr (pph) and lbm/s
        if 'Wf_tot_pph' not in outputs:
            outputs['Wf_tot_pph'] = tsfc * fn
        if 'Wf_tot' not in outputs:
            outputs['Wf_tot'] = (tsfc * fn) / 3600.0

        # Core and afterburner fuel flow
        if 'Wf_core' not in outputs:
            # Core air mass flow W_core = W / (1 + BPR)
            w_core = w / (1.0 + bpr) if bpr >= 0 else w
            outputs['Wf_core'] = w_core * far_core

        if 'Wf_ab' not in outputs:
            if mode == 'wet':
                # In wet mode, AB fuel flow is the remainder of total fuel flow
                outputs['Wf_ab'] = max(0.0, outputs['Wf_tot'] - outputs['Wf_core'])
            else:
                outputs['Wf_ab'] = 0.0

        # Nozzle area placeholder if absent
        if 'A8' not in outputs:
            outputs['A8'] = None

    def export_deck_data(self) -> Dict[str, Any]:
        """Export full deck points and axes metadata to a JSON-ready dictionary."""
        modes_payload: Dict[str, Any] = {}
        for mode in self.modes:
            mdf = self._mode_data[mode]
            axes = self._mode_axes[mode]
            throttle_col = axes['throttle_col']

            # Keep numeric columns
            numeric_cols = [c for c in mdf.select_dtypes(include=[np.number]).columns]

            # List of records
            records = mdf[numeric_cols].to_dict(orient='records')

            # Ensure all values are JSON-serializable
            for r in records:
                for k, v in list(r.items()):
                    if pd.isna(v) or not math.isfinite(v):
                        r[k] = None
                    else:
                        r[k] = float(v)

            modes_payload[mode] = {
                'throttle_col': throttle_col,
                'axes': axes,
                'points_count': len(records),
                'columns': numeric_cols,
                'points': records,
            }

        return {
            'modes': self.modes,
            'default_mode': self.modes[0],
            'deck_data': modes_payload,
        }
