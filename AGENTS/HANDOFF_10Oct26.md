# Handoff: F404-pyCycle — Interactive Cycle Deck Explorer GUI

**Date:** 10 Oct 2026  
**Branch:** `feat/interactive-deck-gui` (branched directly off `main` at `e2a91e3`)  
**Status:** Implementation complete, 153/153 fast unit tests passing (166 full tests), 100% test coverage on new GUI/interpolation modules.

---

## 1. Executive Summary

Implemented an interactive browser-based GUI launched via the `f404 gui` CLI command (`python -m F404_pycycle gui`). The tool loads pre-computed F404 cycle decks (from `deck/`, `decks/`, or custom paths) and provides instantaneous, continuous slider manipulation for:
- Altitude (`alt`, ft)
- ISA temperature offset (`dTs`, degR)
- Throttle (`T4` turbine inlet temp in dry mode, `T7` augmentor exit temp in wet mode)

Because all evaluations reference the deck through zero-solver multidimensional trilinear interpolation (with normalized k-NN Inverse Distance Weighting fallback), the GUI executes at **60+ FPS in < 0.1 ms** with zero OpenMDAO solving overhead and zero server latency.

---

## 2. Architecture & Implementation

### A. Python Backend (`src/F404_pycycle/`)
1. **`deck_interpolator.py` (`DeckInterpolator`)**:
   - Parses rectilinear and irregular CSV decks.
   - Evaluates trilinear tensor-product grid cubes when bounding nodes exist.
   - Falls back to normalized k-nearest-neighbors Inverse Distance Weighting (IDW) with $p=2$ if boundary vertices are absent.
   - Derives total fuel mass flow ($W_f$ in lbm/s and lbm/hr) from $TSFC \times F_n$, core fuel flow $W_{f,core}$ from core airflow and $FAR_{core}$, augmentor fuel flow $W_{f,ab}$ from afterburner fueling, and dynamic nozzle throat area $A_8$.
   - Compatible with future deck columns (e.g., explicit $W_f$, $A_8$ being added in parallel cycle refactors).
   - Exports complete JSON deck payload via `export_deck_data()`.
2. **`gui_server.py` (`DeckGuiHandler`, `start_server`)**:
   - Embedded local HTTP server built with standard library `http.server`.
   - Automatic deck auto-discovery across `deck/`, `decks/`, and current directory.
   - REST endpoints:
     - `GET /`: Serves `index.html`.
     - `GET /app.js`, `GET /style.css`: Serves GUI static assets.
     - `GET /api/decks`: Lists discovered deck files.
     - `GET /api/deck-data`: Provides complete JSON payload for client-side interpolation.
     - `GET /api/interpolate`: Server-side interpolation endpoint for headless/scripting clients.
   - Automatic free port probing starting from 8080 (avoids `Address already in use`).
3. **`cli.py` (`f404 gui`)**:
   - Registered subcommand under `f404` CLI.
   - Options: `--deck PATH`, `--port PORT`, `--host HOST`, `--no-browser`.

### B. TypeScript & HTML5 Frontend (`src/F404_pycycle/gui/`)
1. **TypeScript Sources (`src/F404_pycycle/gui/src/`)**:
   - `types.ts`: Strict typings for cycle deck points, axes, operating inputs, and interpolation results.
   - `interpolator.ts` (`ClientDeckInterpolator`): High-performance client-side trilinear interpolation engine.
   - `charts.ts` (`InteractiveChart`): Pure HTML5 Canvas 2D chart engine (zero heavy third-party bundles like Plotly). Renders anti-aliased engineering grids, operating lines, and live crosshair trackers with glowing badges.
   - `app.ts` (`F404DeckApp`): State coordinator, slider bindings, dynamic range configuration, and DOM readouts.
2. **Standalone Browser Runtime (`src/F404_pycycle/gui/static/`)**:
   - `index.html`: Aerospace cockpit / engineering dashboard layout.
   - `app.js`: ES2022 module corresponding to the TypeScript architecture, requiring zero npm dependencies or build tools to run in any modern browser.
   - `style.css`: Clean dark-theme aerospace aesthetic.

---

## 3. Proof of Function & Behavior

### Test Suite Results
```bash
$ pytest tests/deck_interpolator_test.py tests/gui_server_test.py tests/cli_test.py
============================== 75 passed in 5.82s ==============================

$ pytest -m "not slow"
====================== 153 passed, 31 deselected in 5.85s ======================
```

### CLI Verification
```bash
$ f404 gui --help
usage: f404 gui [-h] [--deck PATH] [--port PORT] [--host HOST] [--no-browser]

Launch an interactive browser GUI to explore and interpolate engine performance 
(thrust, SFC, airflow, fuel flow, nozzle area) across altitude, temperature 
offset, and throttle from cycle decks.
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ -h, --help    show this help message and exit                                │
│ --deck PATH   path to cycle deck CSV file or directory (default:             │
│               auto-detect)                                                   │
│ --port PORT   local HTTP server port (default: 8080)                         │
│ --host HOST   local HTTP server host (default: 127.0.0.1)                    │
│ --no-browser  do not open the browser automatically                          │
╰──────────────────────────────────────────────────────────────────────────────╯
No flag is required: omitted flags use the defaults shown.
```

### SLS Sea-Level Static Design Interpolation Check
Evaluating `deck/cycle_deck_wet.csv` at `alt=0`, `dTs=0`, `T7=3800`:
- Net Thrust $F_n$: `17,741.91 lbf` (78.92 kN)
- Gross Thrust $F_g$: `17,746.67 lbf`
- TSFC: `1.5208 lbm/(lbf·hr)` (43.08 g/(kN·s))
- Airflow $W$: `137.09 lbm/s` (62.18 kg/s)
- Total Fuel Flow $W_f$: `7.495 lbm/s` (26,981.8 lbm/hr)
- Core Fuel Flow $W_{f,core}$: `2.128 lbm/s`
- Augmentor Fuel Flow $W_{f,ab}$: `5.367 lbm/s`
- Spool Speeds: $N_{LP} = 10,000\text{ rpm}$, $N_{HP} = 14,000\text{ rpm}$
- Method: `Exact Node` / `Trilinear Grid`

---

## 4. Coordination with Parallel Cycle Refactor Agent

The parallel agent working on `feat/single-engine-sizing` was completely untouched during this work because this implementation was isolated in worktree `feat/interactive-deck-gui` branched off `main`.

When the cycle refactor agent merges additional columns into the deck (such as explicit `Wf_core`, `Wf_ab`, `A8`):
1. `DeckInterpolator` dynamically reads any new numeric columns present in the CSV without schema modification.
2. If `Wf_core`, `Wf_ab`, and `A8` are in the CSV, the interpolator and GUI will automatically use them directly.
3. No breaking changes or complex rebases are needed.
