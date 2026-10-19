# Engineering References & Methods Library

This directory archives foundational aerothermodynamic literature, empirical correlations, rig test evaluations, and analytical methods used across the cycle model and control algorithms.

Unlike [docs/unclassified_perf_data/](../unclassified_perf_data/README.md), which stores engine-specific performance numbers and flight test recordings for the General Electric F404, this library contains general aerothermal physics, component drag models, pressure loss correlations, and non-F404 rig experiments.

## Directory Structure and Vault Layout

This directory mirrors the unclassified performance data layout and operates as an Obsidian knowledge vault:

```
docs/references/
├── README.md                      # Topic-organized master index
├── md/                            # Converted papers and notes in markdown
│   ├── images/                    # Extracted figure image assets
│   │   └── Kumar 1980 - A Method of Estimating Pressure Loss Across Flame Holders in High Velocity Streams/
│   │       ├── figure-1.png
│   │       ├── figure-2.png
│   │       ├── figure-3.png
│   │       ├── figure-4.png
│   │       └── figure-5.png
│   └── Kumar 1980 - A Method of Estimating Pressure Loss Across Flame Holders in High Velocity Streams.md
└── pdf/                           # Archival source PDFs
    └── Kumar 1980 - A Method of Estimating Pressure Loss Across Flame Holders in High Velocity Streams.pdf
```

Key vault conventions:
- Converted markdown documents reside in `md/`.
- All figures live under `md/images/<Author Year - Title>/` with the same stem as the PDF and markdown file.
- Markdown notes link figures via relative paths (`![](images/<Author Year - Title>/<file>.png)`).
- Source PDFs reside in `pdf/`.

---

## Data and Method Provenance Taxonomy

Numerical values and equations throughout this index carry explicit provenance classifications to differentiate empirical measurements, chart readings, and analytical formulations:

- **[M-DIR] Direct Measurement**: Values recorded directly by physical instruments (such as rig rakes, static taps, load cells, or flowmeters).
- **[M-SPEC] Manufacturer Specification / Rating**: Nominal design targets, uncalibrated specification decks, or contractual program ratings.
- **[M-MOD] Model-Derived Synthesis**: Quantities computed by driving an aerothermodynamic cycle deck or gas generator model with recorded parameters.
- **[M-PLOT] Chart Reading**: Values scaled or digitized from published report plots.
- **[M-THY] Theory / Analytic**: Closed-form derivations or fitted correlations whose primary output is a mathematical equation or functional relationship rather than empirical data (e.g., Kumar Eq. 13).

Provenance tags cite the specific source artifact (e.g., `[M-THY: Eq. 13]` or `[M-PLOT: Fig. 2]`).

---

## Model Topic Index

### 1. Augmentor (Afterburner) Pressure Loss

#### Kumar (1980) - Flameholder Bluff-Body Pressure Loss in High Velocity Streams

- **Note**: [Kumar 1980 - A Method of Estimating Pressure Loss Across Flame Holders in High Velocity Streams.md](md/Kumar%201980%20-%20A%20Method%20of%20Estimating%20Pressure%20Loss%20Across%20Flame%20Holders%20in%20High%20Velocity%20Streams.md)
- **Source PDF**: [Kumar 1980 - A Method of Estimating Pressure Loss Across Flame Holders in High Velocity Streams.pdf](pdf/Kumar%201980%20-%20A%20Method%20of%20Estimating%20Pressure%20Loss%20Across%20Flame%20Holders%20in%20High%20Velocity%20Streams.pdf)
- **Citation**: R. K. Kumar, *A Method of Estimating Pressure Loss Across Flame Holders in High Velocity Streams*, Combustion Science and Technology, Vol. 21, Issue 5–6, pp. 199–203, 1980. DOI: [10.1080/00102208008946936](https://doi.org/10.1080/00102208008946936).
- **Summary**: Formulates an empirical correlation for the stagnation pressure loss coefficient ($C_D$) across multi-ring V-gutter flameholders in high-velocity duct flows as a function of geometric blockage ratio ($\beta$), gutter included angle ($\theta$), and axial ring stagger ($\xi$). Demonstrates via 20-inch afterburner duct testing that flameholder $C_D$ is essentially invariant with Reynolds number in the highly turbulent regime ($N_{RE} = 5\times 10^5$ to $13\times 10^5$).

##### Used by the Model

1. **Approach Dynamic Head over Stagnation Pressure [M-THY: Eq. 13]**:
   $$\frac{q}{P_{01}} = \frac{1}{2} \gamma M_0^2 \left( 1 + \frac{\gamma - 1}{2} M_0^2 \right)^{-\frac{\gamma}{\gamma - 1}}$$
   - **Verification**: Matches Kumar (1980) Eq. 13 exactly:
     $$\frac{\Delta P}{P_{01}} = \frac{1}{2} C_D \gamma M_0^2 \left( 1 + \frac{\gamma - 1}{2} M_0^2 \right)^{-\frac{\gamma}{\gamma - 1}} = C_D \left(\frac{q}{P_{01}}\right)$$
   - **Code usage**: Implemented in `_dynamic_head(g, m)` in [`src/f404/engine_model.py`](../../src/f404/engine_model.py). Used in `AugmentorControl` to compute total augmentor stagnation pressure drop:
     $$\Delta P / P_t = q \cdot \left[ C_D + \eta (\tau - 1) \right]$$
     where $\tau = T_{t7} / T_{t6}$, $C_D$ is the cold flameholder drag loss, and $\eta (\tau - 1)$ represents the fundamental Rayleigh momentum pressure loss due to heat addition.

2. **Flameholder Drag Coefficient vs Blockage [M-THY: Eq. 5]**:
   $$C_D = K \frac{\beta^2 (2 - \beta)}{(1 - \beta)^2} \left[\sin\left(\frac{\theta}{2}\right)\right]^n, \quad K = 4.0, \quad n = 0.5$$
   - **Verification**: Matches Kumar (1980) Eq. 5 and empirical constants on p. 200 exactly.
   - **Nominal value**: For typical afterburner configurations with $\beta \approx 0.29$ to $0.31$ and included angle $\theta = 30^\circ$ ($\sin 15^\circ \approx 0.2588$):
     - At $\beta = 0.29$: $C_D \approx 0.58$
     - At $\beta = 0.30$: $C_D \approx 0.635$
     - At $\beta = 0.307$: $C_D \approx 0.676$ (Kumar theoretical $0.69$, best fit $0.70$)
     - At $\beta = 0.31$: $C_D \approx 0.695$
   - **Code usage**: Sets baseline augmentor cold drag coefficient `AB_CD = 0.65` in [`src/f404/mp_cycle.py`](../../src/f404/mp_cycle.py) (corresponding to $\beta \approx 30.2\%$ at $\theta = 30^\circ$, consistent with the RM12 augmentor rig).

3. **Stagger Attenuation [M-THY: Eqs. 8, 11]**:
   $$\bar{C}_D = K \left[ \frac{\beta_1^2 (2 - \beta_1)}{(1 - \beta_1)^2} + \frac{\beta_2^2 (2 - 2\beta_1 - \beta_2)}{(1 - \beta_1)^3 (1 - \beta_1 - \beta_2)^2} \right] \left[\sin\left(\frac{\theta}{2}\right)\right]^n$$
   - Axially staggering concentric flameholder rings by $\xi = L/d \ge 2$ places downstream rings in the wake contraction of upstream rings, reducing effective drag by $>20\%$ compared to coplanar layouts ($C_D = 0.47 \to 0.37$ in Fig. 4).

##### Key Experimental Geometries and Rigs [M-DIR: Section 3 & 4]

| Parameter | Value | Units | Provenance / Notes |
| :--- | :--- | :--- | :--- |
| Rig Duct Diameter | 20.0 | in (0.508 m) | [M-DIR: p. 200] GTRE test rig with antiscreech liner & spray bars |
| Duct Flow Area ($A$) | 314.16 | in$^2$ (0.2027 m$^2$) | [M-DIR: p. 201] Calculated from 20-in circular duct |
| Three-Ring Gutter Diameters | 14.75, 9.00, 3.40 | in | [M-DIR: p. 201] Mean ring diameters |
| Gutter Width ($d$) | 1.0 | in (25.4 mm) | [M-DIR: p. 201] Nominal width across gutters |
| Connecting Gutter Area | 11.0 | in$^2$ | [M-DIR: p. 201] Radial connecting struts |
| Three-Ring Projected Area ($a$) | 96.0 | in$^2$ (0.0619 m$^2$) | [M-DIR: p. 201] Total blocked area |
| Three-Ring Geometric Blockage ($\beta$) | 30.7% (0.307) | — | [M-DIR: p. 201] $a / A = 96 / 314.16$ |
| Three-Ring Gutter Included Angle ($\theta$) | 30 | deg | [M-DIR: p. 201] V-gutter opening angle |
| Two-Ring Blockage ($\beta$) | 38.0% (0.380) | — | [M-DIR: p. 201] High blockage test case |
| Two-Ring Gutter Included Angle ($\theta$) | 25 | deg | [M-DIR: p. 201] Narrow V-gutter |
| Staggered Flameholder Outer Ring Area ($a_1$) | 62.2 | in$^2$ | [M-DIR: p. 202] Outer ring |
| Staggered Flameholder Inner Ring Area ($a_2$) | 23.0 | in$^2$ | [M-DIR: p. 202] Inner ring (located first) |
| Staggered Flameholder Total Blockage ($\beta$) | 27.1% (0.271) | — | [M-DIR: p. 202] Coplanar baseline for stagger test |

##### Digitized Performance Data

###### Three-Ring V-Gutter Pressure Loss vs Approach Mach [M-PLOT / M-THY: Fig. 2]
Configuration: $\beta = 0.307$, $\theta = 30^\circ$, Theoretical $C_D = 0.69$, Best-Fit $C_D = 0.70$.

| Free Stream Mach ($M_0$) | Measured $\Delta P / P_{01}$ [M-PLOT] | Incompressible Eq. 13 ($C_D=0.70$) [M-THY] | Compressible Eq. 14 ($C_D=0.70$) [M-THY] |
| :---: | :---: | :---: | :---: |
| 0.16 | 0.90% | 1.15% | 0.95% |
| 0.19 | 1.50% | 1.62% | 1.50% |
| 0.21 | 1.95% | 1.98% | 1.95% |
| 0.27 | 3.20% | 3.28% | 3.20% |
| 0.32 | 4.85% | 4.45% | 4.85% |
| 0.36 | 6.80% | 5.50% | 6.80% |

> [!NOTE]
> For $M_0 \le 0.25$, the incompressible formulation (Eq. 13) closely tracks test data. Above $M_0 \approx 0.3$, fluid compressibility increases the total pressure defect; the momentum/continuity formulation (Eq. 14) matches measured data up to $M_0 = 0.37$.

###### Two-Ring Stagger Attenuation vs Approach Mach [M-PLOT / M-THY: Fig. 4]
Configuration: Two rings ($a_1 = 62.2\text{ in}^2, a_2 = 23\text{ in}^2, \theta = 30^\circ$).

| Free Stream Mach ($M_0$) | 0" Stagger ($C_D = 0.47$) [M-PLOT] | 2" Stagger ($C_D = 0.46$) [M-PLOT] | 4" Stagger ($C_D = 0.37$) [M-PLOT] |
| :---: | :---: | :---: | :---: |
| 0.15 | 0.95% | 0.95% | 0.75% |
| 0.21 | 1.55% | 1.50% | 1.15% |
| 0.26 | 2.30% | 2.00% | 1.68% |
| 0.31 | 3.00% | 2.65% | 2.35% |
| 0.36 | 4.50% | 3.55% | 3.15% |

###### Reynolds Number Independence [M-PLOT: Fig. 5]
Approach flow Reynolds number tested from $N_{RE} = 5\times 10^5$ to $13\times 10^5$:
- Non-staggered ($\beta = 0.38$): Drag coefficient $C_d$ varies mildly between $1.9$ and $2.4$ (mean $\sim 2.1$).
- $0''$ Stagger ($\beta = 0.27$): $C_d \approx 1.3 - 1.6$ (mean $\sim 1.4$).
- $2''$ Stagger ($\beta = 0.27$): $C_d \approx 1.3 - 1.4$ (essentially constant at $1.36$).
- $4''$ Stagger ($\beta = 0.27$): $C_d \approx 1.05 - 1.18$ (essentially constant at $1.12$).

---

### 2. Planned Literature Additions

The references library is architected to house upcoming aerothermal and component methodology papers:

| Topic Area | Target Literature | Scope / Focus | Intended Model Application |
| :--- | :--- | :--- | :--- |
| **Flameholder Aerodynamics** | NASA RM E54C30, E53J14, E57C01 | Fundamental bluff body and gutter drag test cell rakes | Sizing blockage, gutter angle sensitivities |
| **Augmentor Combustion** | NASA TN D-6839 | TF30 afterburner efficiency, stability, and lean limits | Augmentor combustion efficiency ($\eta_{ab}$) curves |
| **Turbofan Flameholder Rig** | ICAS-90-5.3.4 | Volvo Flygmotor RM12 afterburner flameholder rig | RM12/F404 mixed-flow approach Mach & flameholder geometry |
| **Exhaust Nozzles** | NASA TM-X series | Convergent-divergent nozzle thrust and discharge coefficients | $C_d$ and $C_{fg}$ calibration across nozzle pressure ratios |
| **Engine Transients** | AGARD CP-324 / NASA TP | Gas turbine transient modeling & volume pack effects | Inter-component volume dynamics and fuel schedules |
