# F404 Unclassified Performance Data Index

This directory archives public technical reports, flight test evaluations, ground test cell campaigns, and engineering papers for the General Electric F404 turbofan engine.

## Directory Structure and Vault Layout

This folder operates as a standalone Obsidian knowledge vault. Markdown notes link across documents using internal wikilinks (using double brackets around note titles) and reference figures stored in dedicated subdirectories.

```
docs/unclassified_perf_data/
├── README.md                      # Vault root and master index
├── md/                            # Converted technical papers in Obsidian markdown
│   ├── images/                    # Extracted figure image assets
│   │   ├── ada164562/             # Figures for Frith (1985)
│   │   ├── exhaust-gas-pt-survey/ # Figures for Walton & Burcham (1986)
│   │   ├── hadzic-2010/           # Figures for Hadzic et al. (2010)
│   │   ├── nasa-tm-4140/          # Figures for Conners (1989)
│   │   ├── nasa-tm-4240/          # Figures for Johnson (1990)
│   │   ├── nasa-tm-4538/          # Figures for Ennix et al. (1993)
│   │   ├── nasa-tp-3001/          # Figures for Ray (1990)
│   │   ├── powel-1990/            # Figures for Powel (1990)
│   │   └── yuhas-1992/            # Figures for Yuhas & Ray (1992)
│   ├── ADA164562 The General Electric F404 - Engine of the RAAF's New Fighter.md
│   ├── Exhaust-Gas P & T Survey of F404-GE-400 engine.md
│   ├── Hadzic 2010 - Limited Qualification Tests of an F404 Engine with Blended FT-SPK and NATO F-34 Fuel.md
│   ├── NASA TM 4140 - Measurement Effects on the Calculation of In-Flight Thrust for an F404 turbofan engine.md
│   ├── NASA TM 4538 - Flight-Determine Engine Exhaust Characteristics of an F404 Engine in an F-18 Airplane.md
│   ├── NASA TM-4240 - A simple Dynamic Engine Model for Use in a Real-time Aircraft Simulation with Thrust Vectoring.md
│   ├── NASA TP 3001 - Evaluation of Various Thrust Calibration Techniques on an F404 Engine (April 1990).md
│   ├── Powel 1990 - On the Leading Edge, Combining Maturity and Advanced Technology on the F404 Turbofan Engine.md
│   └── Yuhas 1992 - Effects of Bleed ir Extraction of Thrust Levels of the F404-GE-400 Turbofan Engine.md
└── pdf/                           # Original source PDF documents
    ├── ADA164562 The General Electric F404 - Engine of the RAAF's New Fighter.pdf
    ├── Exhaust-Gas P & T Survey of F404-GE-400 engine.pdf
    ├── F404 Family Data Sheet_UPDATED.pdf
    ├── Hadzic 2010 - Limited Qualification Tests of an F404 Engine with Blended FT-SPK and NATO F-34 Fuel.pdf
    ├── NASA TM 4140 - Measurement Effects on the Calculation of In-Flight Thrust for an F404 turbofan engine.pdf
    ├── NASA TM 4538 - Flight-Determine Engine Exhaust Characteristics of an F404 Engine in an F-18 Airplane.pdf
    ├── NASA TM-4240 - A simple Dynamic Engine Model for Use in a Real-time Aircraft Simulation with Thrust Vectoring.pdf
    ├── NASA TP 3001 - Evaluation of Various Thrust Calibration Techniques on an F404 Engine (April 1990).pdf
    ├── Powel 1990 - On the Leading Edge, Combining Maturity and Advanced Technology on the F404 Turbofan Engine.pdf
    └── Yuhas 1992 - Effects of Bleed ir Extraction of Thrust Levels of the F404-GE-400 Turbofan Engine.pdf
```

Key vault conventions:
- Converted markdown documents reside in `md/`.
- All figures live under `md/images/<paper-folder>/`. Notes embed figures via relative paths (`![](images/<paper-folder>/<file>.jpg)`).
- Source PDFs reside in `pdf/`.
- Frontmatter blocks track source citations, report numbers, publication years, and status tags.

---

## Data Provenance Taxonomy

Numerical values throughout this index carry explicit provenance classifications to distinguish empirical data from model outputs:

- **[M-DIR] Direct Measurement**: Values recorded by physical instruments (such as test cell load cells, traversing rakes, Venturi flowmeters, and test cell scales).
- **[M-SPEC] Manufacturer Specification / Rating**: Nominal design targets, uncalibrated engine specification decks, or contractual program ratings published by General Electric or defense acquisition offices.
- **[M-MOD] Model-Derived Synthesis**: Quantities computed by driving an aerothermodynamic cycle deck or gas generator model with recorded flight or test parameters (such as GE In-Flight Thrust Program 83112, GE Dynamic Real Time Model R88AEB427, or Computing Devices Company SGTM).
- **[M-PLOT] Chart Reading**: Values scaled or digitized from published report plots.

---

## Literature Inventory

| Document Note | Lead Author | Year | Report Identifier | Test Campaign / Context | Primary Research Focus |
| :--- | :--- | :---: | :--- | :--- | :--- |
| [ADA164562 (Frith 1985)](md/ADA164562%20The%20General%20Electric%20F404%20-%20Engine%20of%20the%20RAAF%27s%20New%20Fighter.md) | D. A. Frith | 1985 | ARL-AERO-PROP-TM-426 / AD-A164 562 | RAAF F/A-18 induction, NAPC altitude tests, CAC assembly | Baseline F404-GE-400 cycle, component stages, cooling bleeds, control schedules |
| [Walton & Burcham (1986)](md/Exhaust-Gas%20P%20%26%20T%20Survey%20of%20F404-GE-400%20engine.md) | J. T. Walton | 1986 | NASA TM-88273 | NASA Lewis PSL Cell 4 ground altitude tests (S/N 215209) | Exhaust nozzle exit rakes, gas temperature profiles, wake pressure defects, Mach profiles |
| [Conners (1989)](md/NASA%20TM%204140%20-%20Measurement%20Effects%20on%20the%20Calculation%20of%20In-Flight%20Thrust%20for%20an%20F404%20turbofan%20engine.md) | T. R. Conners | 1989 | NASA TM-4140 / AIAA-89-2364 | X-29A flight research program at NASA Ames-Dryden | Sensor error propagation, WT vs AP in-flight thrust calculation methods, sensitivity derivatives |
| [Powel (1990)](md/Powel%201990%20-%20On%20the%20Leading%20Edge%2C%20Combining%20Maturity%20and%20Advanced%20Technology%20on%20the%20F404%20Turbofan%20Engine.md) | S. F. Powel IV | 1990 | ASME 90-GT-149 | GE Aircraft Engines fleet review (>2M EFH) | F404 family growth (F404-402 EPE, RM12, F412, Growth II/III), materials, deterioration control logic |
| [Ray (1990)](md/NASA%20TP%203001%20-%20Evaluation%20of%20Various%20Thrust%20Calibration%20Techniques%20on%20an%20F404%20Engine%20%28April%201990%29.md) | R. J. Ray | 1990 | NASA TP-3001 (Errata May 1990) | NASA Lewis PSL Cell 4 (S/N 215-209) and X-29A flight test | Load-cell scale thrust calibration, ComDev SGTM algorithm, GE IFT gas generator deck |
| [Johnson (1990)](md/NASA%20TM-4240%20-%20A%20simple%20Dynamic%20Engine%20Model%20for%20Use%20in%20a%20Real-time%20Aircraft%20Simulation%20with%20Thrust%20Vectoring.md) | S. A. Johnson | 1990 | NASA TM-4240 / AIAA-90-2166 | F-18 HARV thrust-vectoring simulation at NASA Ames-Dryden | Real-time dynamic engine surrogate, 3D look-up tables, PLA lag filters, HARV vane drag penalties |
| [Yuhas & Ray (1992)](md/Yuhas%201992%20-%20Effects%20of%20Bleed%20ir%20Extraction%20of%20Thrust%20Levels%20of%20the%20F404-GE-400%20Turbofan%20Engine.md) | A. J. Yuhas | 1992 | NASA TM-104247 / AIAA 92-3092 | F/A-18 HARV ground test on EAFB Universal Horizontal Thrust Stand | HPC customer bleed extraction, linear thrust penalty slopes, control nozzle modulation |
| [Ennix et al. (1993)](md/NASA%20TM%204538%20-%20Flight-Determine%20Engine%20Exhaust%20Characteristics%20of%20an%20F404%20Engine%20in%20an%20F-18%20Airplane.md) | K. A. Ennix | 1993 | NASA TM-4538 / AIAA-93-2543 | F-18 subsonic flyovers over Rogers Dry Lake for HSCT jet noise | In-flight exhaust gas properties, C-D nozzle expansion states, invariant exit Mach number |
| [Hadzic et al. (2010)](md/Hadzic%202010%20-%20Limited%20Qualification%20Tests%20of%20an%20F404%20Engine%20with%20Blended%20FT-SPK%20and%20NATO%20F-34%20Fuel.md) | R. Hadzic | 2010 | ASME GT2010-23402 | NRC Canada Test Cell #4 qualification campaign (CF-18) | 50/50 FT-SPK synthetic kerosene blend, fuel density effects, spool match invariance, acoustic stability |
| [F404 Family Data Sheet (2006)](pdf/F404%20Family%20Data%20Sheet_UPDATED.pdf) | GEAE | 2006 | OEM Product Sheet | Commercial and military marketing specifications | Unconverted PDF summary for F404-GE-402, F404-GE-102, and RM12 ratings |

---

## Technical Summaries and Performance Data

### 1. Frith (1985) - Baseline Cycle Architecture and RAAF Induction

- **Note**: [ADA164562 The General Electric F404 - Engine of the RAAF's New Fighter.md](md/ADA164562%20The%20General%20Electric%20F404%20-%20Engine%20of%20the%20RAAF%27s%20New%20Fighter.md)
- **Source PDF**: [ADA164562 The General Electric F404 - Engine of the RAAF's New Fighter.pdf](pdf/ADA164562%20The%20General%20Electric%20F404%20-%20Engine%20of%20the%20RAAF%27s%20New%20Fighter.pdf)
- **Citation**: D. A. Frith, *The General Electric F404 - Engine of the RAAF's New Fighter*, Aeronautical Research Laboratories, Melbourne, Australia, Report ARL-AERO-PROP-TM-426 (AD-A164 562), July 1985.
- **Context**: Technical orientation for the Royal Australian Air Force induction of the McDonnell Douglas F/A-18 Hornet. Details development history from the YJ101 prototype, full-scale development milestones, and component aerothermodynamics.

#### Experimental and Operational Scope
- Full-scale development testing reached Preliminary Flight Rating Test (PFRT) at 1,000 engine test hours.
- 150-hour Military Endurance Test completed at the Naval Air Propulsion Center (NAPC) altitude cell, including sustained testing at Mach 1.6 and 35,000 ft.
- Flight clearance included extreme attitude trials exceeding 90 deg pitch attitude at Mach 0.15 to 0.40 between 35,000 and 40,000 ft without engine stall or flameout.
- Production assembly established at Commonwealth Aircraft Corporation (CAC) in Melbourne at 20 engines per year.

#### Measurement and Instrumentation Assumptions
- In-flight Engine Condition Monitoring System (IECMS) tracks low-cycle fatigue by calculating Equivalent Full Thermal Cycles from turbine exhaust temperature ($T_5$).
- Control sensors monitor inlet temperature ($T_1$), ambient pressure ($P_0$), fan speed ($N_1$), compressor inlet temperature ($T_{2.5}$), core speed ($N_2$), combustor static pressure ($PS_3$), and turbine exhaust temperature ($T_5$).
- Engine uses hydromechanical control below military power and electronic supervisory control at military power and afterburning.

#### Key Performance Metrics [M-SPEC / Program Ratings: Figures 1, 3, 4, 14, 28, text p. 8]

| Parameter | Value (US Units) | Value (SI Units) | Operating Condition / Source |
| :--- | :--- | :--- | :--- |
| Maximum Augmented Thrust (Max A/B) | 16,000 lbf | 71.17 kN | Sea Level Static (SLS), Standard Day |
| Maximum Dry Thrust (IRP) | 10,600 lbf | 47.15 kN | SLS, Standard Day |
| Maximum A/B Specific Fuel Consumption | 1.84 to 1.85 lb/(hr·lbf) | 52.1 g/(kN·s) | SLS, Max A/B |
| Dry Specific Fuel Consumption | 0.78 to 0.81 lb/(hr·lbf) | 22.1 g/(kN·s) | SLS, IRP |
| Total Engine Air Mass Flow | 142 lb/s | 64.4 kg/s | SLS, Max Dry |
| Bypass Ratio (BPR) | 0.34 | 0.34 | Design point |
| Overall Pressure Ratio (OPR) | 25.0:1 | 25.0:1 | SLS, Max Dry |
| Fan Pressure Ratio (FPR) | 4.1:1 | 4.1:1 | 3-stage fan |
| Fan Physical Rotor Speed ($N_1$) | 13,270 rpm | 13,270 rpm | 100% mechanical design speed |
| Fan Tip Speed | 1,592 ft/s | 485.2 m/s | Design point |
| Fan Corrected Speed Limit | 104.4% | 104.4% | Cold-day ceiling ($T_1 < 444.5^\circ\text{R}$) |
| High-Pressure Compressor Pressure Ratio | 6.0:1 (nominal 6.3:1) | 6.0:1 | 7-stage compressor |
| High-Pressure Rotor Speed ($N_2$) | 16,810 rpm | 16,810 rpm | 100% mechanical design speed |
| Average Compressor Stage Temperature Rise | 52 °C | 52 K | Across 7 stages |
| Compressor Discharge Temperature ($T_3$) | 520 °C | 793 K | Combustor entrance |
| Turbine Inlet Temperature (TIT) | 1,390 °C (2,994 °R) | 1,663 K | Design point |
| TIT Control Limit Ceiling | 2,980 °R (1,382 °C) | 1,656 K | Flat-rated temperature ceiling |
| HPT Nozzle Guide Vane Cooling Bleed | 11% of CDP | 11% of CDP | From compressor discharge |
| Combustor Liner Shell Cooling Bleed | 3.0% of engine air | 3.0% of engine air | Film cooling flow |
| Bare Engine Dry Weight | 2,180 lb | 988.8 kg | Uninstalled bare weight |
| Overall Length | 159 in | 4.039 m | Front flange to exit plane |
| Maximum Outer Diameter | 35 in | 0.889 m | Outer casing flange |
| Thrust-to-Weight Ratio | 7.3:1 (7.5:1 class) | 7.3:1 | Uninstalled dry engine |
| Idle to IRP Acceleration Time | < 4.0 s | < 4.0 s | Sea level static transient |
| Combustor Pressure Upper Override ($PS_3$) | $\ge$ 425 psia | $\ge$ 2,930 kPa | Control schedule limit |
| Combustor Pressure Lower Override ($PS_3$) | $\le$ 80 psia | $\le$ 551.6 kPa | Minimum burner pressure limit |

#### Relevance to Cycle Modeling
Frith supplies the foundation for 0D thermodynamic station modeling: 3 fan stages, 7 compressor stages, single-stage HPT, single-stage LPT, and confluent mixed flow. The engine directs 11% of compressor discharge air to cool the first-stage turbine guide vanes. The bypass ratio is low (0.34), acting as a leaky turbojet that delivers high specific thrust while duct air cools the engine casing.

---

### 2. Walton & Burcham (1986) - Exhaust-Gas Pressure and Temperature Surveys

- **Note**: [Exhaust-Gas P & T Survey of F404-GE-400 engine.md](md/Exhaust-Gas%20P%20%26%20T%20Survey%20of%20F404-GE-400%20engine.md)
- **Source PDF**: [Exhaust-Gas P & T Survey of F404-GE-400 engine.pdf](pdf/Exhaust-Gas%20P%20%26%20T%20Survey%20of%20F404-GE-400%20engine.pdf)
- **Citation**: James T. Walton and Frank W. Burcham, Jr., *Exhaust-Gas Pressure and Temperature Survey of F404-GE-400 Turbofan Engine*, NASA TM-88273, December 1986.
- **Context**: Ground altitude tests in NASA Lewis Propulsion System Laboratory Test Cell 4 using F404-GE-400 engine S/N 215209 (from the X-29A program). The data established exhaust plume gradients to design post-exit thrust-vectoring vanes for the F-18 HARV.

#### Experimental and Measurement Assumptions
- Tests deployed a water-cooled traversing rake with five probes mounted 2.0 in aft of the nozzle exit plane (Station 9).
- Probe suite contained three Pitot probes (87% Platinum / 13% Rhodium alloy) and two bare-wire thermocouples (Iridium vs 60% Iridium / 40% Rhodium alloy).
- Data reduction applied normal shock corrections to Pitot readings (15% total pressure loss at supersonic exit speeds) and radiation corrections to thermocouples (+10 °R at 1,500 °R; +100 °R at 3,000 °R).
- Test conditions:
  - Condition 1: Mach 0.30 at 30,000 ft ($PT_1 = 4.65\text{ psia}$, $P_{\text{amb}} = 4.39\text{ psia}$, $TT_1 = 464.8^\circ\text{R}$).
  - Condition 2: Mach 0.87 at 24,000 ft ($PT_1 = 9.30\text{ psia}$, $P_{\text{amb}} = 5.70\text{ psia}$, $TT_1 = 504.5^\circ\text{R}$).

#### Key Measured Survey Results [M-DIR: Traversing Rake at Station R (2 in aft of nozzle exit), Figures 9, 10, 11]

*Note on measurement location: Values represent local stagnation pressures and temperatures recorded by probe tips traversing the exhaust plume 2 inches downstream of the nozzle exit plane (Station R), not bulk 1D mixed flow station values.*

| Test Condition | Power Setting (PLA) | Outer Edge Radius | Peak Total Pressure ($PT_9$) | Centerline Total Pressure | Peak Total Temp ($TT_9$) | Centerline Total Temp | Expansion State |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| M 0.30, 30k ft | Intermediate (87°) | 9.5 in | 19.1 psia (1.5 in inside lip) | 15.5 psia | 1,780 °R (centerline crest) | 1,780 °R | Proper expansion |
| M 0.30, 30k ft | Mid A/B (110°) | 11.5 in | 18.0 psia (1.5 in inside lip) | 14.8 psia | 2,900 °R (2.4 in inside lip) | 2,440 °R | Overexpanded |
| M 0.30, 30k ft | High A/B (120°) | 12.0 in | 16.2 psia (1.25 in inside lip) | 13.8 psia | 3,400 °R (2.0 in inside lip) | 2,750 °R | Overexpanded |
| M 0.30, 30k ft | Max A/B (130°) | 13.0 in | 16.0 psia (1.0 in inside lip) | 12.5 psia | 3,750 °R (2.0 in inside lip) | 3,300 °R | Overexpanded |
| M 0.87, 24k ft | Intermediate (87°) | 10.5 in | 39.1 psia (expansion crest) | 29.5 psia | 1,880 °R (centerline crest) | 1,880 °R | Underexpanded |
| M 0.87, 24k ft | High A/B (120°) | 12.5 in | 30.5 psia (2.0 in inside lip) | 19.8 psia | 3,366 °R (2.0 in inside lip) | 2,950 °R | Underexpanded |
| M 0.87, 24k ft | Max A/B (130°) | 13.5 in | 31.5 psia (median) | 20.0 psia | 3,800 °R (45 deg peak) | 3,550 °R | Proper expansion |

#### Key Conclusions and Modeling Relevance
- The exhaust total pressure drops by 20% to 45% along the nozzle centerline across all power settings. The turbine rear centerbody wake and residual swirl persist through the afterburner duct, creating an on-axis momentum defect.
- Afterburning creates steep radial temperature gradients. The outer 1.0 to 2.5 in of the plume carries cool fan duct bypass air that protects the nozzle liner, adjacent to an afterburning flame core reaching 3,750 to 3,800 °R.
- The cam-linked nozzle schedule does not match ideal expansion across off-design points. Low-speed high-altitude flight produces overexpanded nozzle flow with internal oblique shocks. High subsonic cruise produces underexpanded flow with exit expansion fans. Cycle models must calculate gross thrust using the complete momentum plus pressure-area equation rather than assuming ambient exit static pressure.

---

### 3. Conners (1989) - Measurement Error Effects on In-Flight Thrust

- **Note**: [NASA TM 4140 - Measurement Effects on the Calculation of In-Flight Thrust for an F404 turbofan engine.md](md/NASA%20TM%204140%20-%20Measurement%20Effects%20on%20the%20Calculation%20of%20In-Flight%20Thrust%20for%20an%20F404%20turbofan%20engine.md)
- **Source PDF**: [NASA TM 4140 - Measurement Effects on the Calculation of In-Flight Thrust for an F404 turbofan engine.pdf](pdf/NASA%20TM%204140%20-%20Measurement%20Effects%20on%20the%20Calculation%20of%20In-Flight%20Thrust%20for%20an%20F404%20turbofan%20engine.pdf)
- **Citation**: Timothy R. Conners, *Measurement Effects on the Calculation of In-Flight Thrust for an F404 Turbofan Engine*, NASA TM-4140 / AIAA-89-2364, September 1989.
- **Context**: Evaluation of sensor error propagation through the General Electric In-Flight Thrust (IFT) program (Program 83112) for the X-29A flight research program at NASA Ames-Dryden.

#### Experimental and Analytical Methodology
- Analyzed 10 measured flight inputs: Mach ($M$), altitude ($ALT$), inlet total temperature ($TT_1$), fan speed ($N_1$), fan guide vane angle ($FVG$), turbine discharge total pressure ($PT_{558}$), nozzle throat area ($A_8$), core fuel flow ($WFE$), afterburner fuel flow ($WFAB$), and fuel heating value ($FHV$).
- Evaluated two thrust formulations: Mass Flow-Temperature (WT) and Area-Pressure (AP).
- Calculated linear influence coefficients ($C_i = \Delta FN\% / 1\%$ parameter change) and verified them against full nonlinear error evaluations.

#### Sensor Ranges and Absolute Uncertainties [M-DIR Instrumentation Specifications: Table 1 of TM-4140]

| Parameter | Sensor / Source | Operating Range | Absolute Uncertainty ($\pm$) |
| :--- | :--- | :--- | :--- |
| Mach Number ($M$) | Aircraft air data system | 0 to 2.0 | 0.005 |
| Pressure Altitude ($ALT$) | Aircraft air data system | 0 to 60,000 ft | 60.0 ft |
| Inlet Total Temperature ($TT_1$) | Resistance temperature device | 400 to 860 °R | 8.6 °R |
| Fan Rotor Speed ($N_1$) | Eddy-current magnetic sensor | 0 to 13,270 rpm | 132.7 rpm |
| Fan Guide Vane Angle ($FVG$) | Rotary LVDT | 0 to 55 deg | 1.1 deg |
| Turbine Discharge Pressure ($PT_{558}$) | 4 rakes $\times$ 5 probes (heated transducer) | 0 to 60 psia | 0.16 psia |
| Nozzle Throat Area ($A_8$) | Actuator linear LVDT | 220 to 540 in² | 10.8 in² |
| Core Fuel Flow ($WFE$) | Volumetric flowmeter + temperature | 0 to 12,000 lb/hr | 240.0 lb/hr |
| Afterburner Fuel Flow ($WFAB$) | Volumetric flowmeter + temperature | 0 to 30,000 lb/hr | 600.0 lb/hr |
| Fuel Heating Value ($FHV$) | Laboratory fuel sample analysis | 18,200 to 18,600 Btu/lb | 93.0 Btu/lb |

#### Net Thrust Uncertainty Comparison across Flight Envelope [M-MOD: Synthesized via GE IFT Program 83112, Table 2 of TM-4140]

| Flight Condition | Power Setting (PLA) | Baseline Net Thrust | WT Uncertainty ($UFNWT$) | AP Uncertainty ($UFNAP$) | AP/WT Error Ratio |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 10k ft, M 0.4 | 87° (Intermediate) | 7,318 lbf | 2.50% | 5.34% | 2.14x |
| 10k ft, M 0.4 | 130° (Max A/B) | 11,664 lbf | 1.16% | 3.00% | 2.59x |
| 10k ft, M 0.8 | 87° (Intermediate) | 7,928 lbf | 2.65% | 7.02% | 2.65x |
| 10k ft, M 0.8 | 130° (Max A/B) | 13,892 lbf | 1.47% | 3.73% | 2.54x |
| 30k ft, M 0.9 | 87° (Intermediate) | 4,547 lbf | 2.60% | 7.62% | 2.93x |
| 30k ft, M 0.9 | 130° (Max A/B) | 8,022 lbf | 1.48% | 4.09% | 2.76x |
| 30k ft, M 1.2 | 87° (Intermediate) | 5,478 lbf | 2.84% | 9.07% | 3.19x |
| 30k ft, M 1.2 | 130° (Max A/B) | 10,477 lbf | 1.33% | 3.85% | 2.89x |
| 40k ft, M 0.8 | 87° (Intermediate) | 2,675 lbf | 2.53% | 7.23% | 2.86x |
| 40k ft, M 0.8 | 109° (Mid A/B) | 3,639 lbf | 7.99% | 5.92% | 0.74x |
| 40k ft, M 0.8 | 130° (Max A/B) | 4,654 lbf | 1.49% | 4.04% | 2.71x |
| 40k ft, M 1.6 | 70° (Part Power) | 4,251 lbf | 3.13% | 10.41% | 3.33x |
| 40k ft, M 1.6 | 87° (Intermediate) | 4,252 lbf | 3.13% | 10.39% | 3.32x |
| 40k ft, M 1.6 | 130° (Max A/B) | 9,012 lbf | 2.11% | 5.34% | 2.53x |
| **Envelope Average** | **All Settings** | N/A | **3.19%** | **6.11%** | **1.92x** |

#### Key Conclusions and Modeling Relevance
- The Mass Flow-Temperature (WT) method cuts net thrust uncertainty in half compared to the Area-Pressure (AP) method (3.19% mean error vs 6.11%).
- WT benefits from an error cancellation mechanism: fan speed ($N_1$) sets inlet airflow ($W_1$) and downstream nozzle mass flow ($W_8$). Errors in $N_1$ bias both gross thrust and ram drag in the same direction, cancelling out in net thrust ($FN = FG - FR$).
- AP does not experience this cancellation. It calculates gross thrust from nozzle pressure and throat area ($A_8$), while using airflow only to compute ram drag. Actuator LVDT uncertainty in $A_8$ ($\pm 10.8\text{ in}^2$) accounts for 70% to 90% of total AP thrust error.
- Linear influence coefficients match full nonlinear calculations within 0.11% average discrepancy, proving that cycle model Jacobians capture engine measurement sensitivity.

---

### 4. Powel (1990) - Fleet Maturity and Family Growth Roadmap

- **Note**: [Powel 1990 - On the Leading Edge, Combining Maturity and Advanced Technology on the F404 Turbofan Engine.md](md/Powel%201990%20-%20On%20the%20Leading%20Edge%2C%20Combining%20Maturity%20and%20Advanced%20Technology%20on%20the%20F404%20Turbofan%20Engine.md)
- **Source PDF**: [Powel 1990 - On the Leading Edge, Combining Maturity and Advanced Technology on the F404 Turbofan Engine.pdf](pdf/Powel%201990%20-%20On%20the%20Leading%20Edge%2C%20Combining%20Maturity%20and%20Advanced%20Technology%20on%20the%20F404%20Turbofan%20Engine.pdf)
- **Citation**: S. F. Powel IV, *On the Leading Edge: Combining Maturity and Advanced Technology on the F404 Turbofan Engine*, ASME Paper 90-GT-149, June 1990.
- **Context**: Programmatic and technical review by the Manager of F404 Advanced Programs at GE Aircraft Engines. Reviews operational experience across 2,000 deliveries and 2 million flight hours, presenting technology scaling paths.

#### Operational Milestones and Durability Fixes
- Shop visit rate dropped from 14.5 visits per 1,000 EFH early in service down to 1.0 visit per 1,000 EFH. In-flight shutdown rate fell to 0.10 per 1,000 EFH.
- Constant-dollar production cost fell by 53% between FY79 and FY88.
- Outer flap aerodynamic wear resolved by switching to shingled outer flaps adapted from the F110.
- Afterburner liner buckling at high dynamic pressures resolved by adding circumferential stiffening rings.
- Compressor rub friction fires resolved by replacing the forward titanium compressor casing with M152 steel and installing a PMR-15 polyimide composite outer bypass duct. The net engine weight increased by only 1 lb.

#### F404 Derivative Family Performance Comparison [M-SPEC / Program Ratings: Figures 3, 12, 15, 17]

| Variant | Aircraft Application | Max A/B Thrust | Dry Thrust (MIL) | Fan Airflow | Fan PR | TIT Delta vs -400 | Key Structural & Aerodynamic Features |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **F404-GE-400** | F/A-18A/B/C/D | 16,000 lbf | ~11,000 lbf | 145 lb/s | ~4.2 | 0 °F (ref) | Baseline 3-fan, 7-compressor, single-crystal HPT baseline |
| **F404-GE-402 (EPE)** | F/A-18C/D (post-1992) | 17,700 lbf | ~12,000 lbf | 145 lb/s (+2% speed) | ~4.2 | +100 °F MIL / +175 °F AB | Single-crystal airfoils, RM12 afterburner (+5-6% eff), M152 steel case |
| **F404/RM12** | Saab JAS 39 Gripen | 18,100 lbf | ~12,000 lbf | 160 lb/s (+10.3%) | 4.2 to ~5.0 | Elevated | Strengthened fan (1.1 lb bird ingestion), DSR80H buckets, DEC with SEF |
| **F404/F2J3** | India LCA | ~19,000 lbf | ~12,500 lbf | 160 lb/s | 4.2 to ~5.0 | Elevated | RM12 fan and afterburner, hot-day cycle schedule match |
| **F404-GE-100D / 400D** | A-4S-1 / A-6F | None (Dry only) | 11,000 to 11,500 lbf | 145 lb/s | ~4.2 | Baseline | Non-afterburning, cast titanium midframe (-30 lb), DEC |
| **F412-GE-400** | A-12 Avenger II ATA | None (Dry only) | Medium bypass | 200 lb/s | Unstated | +200 °F | Scaled 200 lb/s fan, Core II compressor, 2-stage LPT, multihole combustor |
| **Growth II (Study)** | Hornet 2000 studies | 20,000 to 23,000 lbf | Unstated | 160 to 170 lb/s | 4.2 to ~5.0 | +200 to +300 °F | Core II (+5% flow, +2% HPT eff), FADEC, AVEN vectoring nozzle option |
| **Growth III (Study)** | Advanced studies | 22,500 to >24,000 lbf | Unstated | 180 lb/s | Unstated | +200 to +300 °F | Core III (+10% flow, +2% comp eff, +2% HPT eff), 9.5:1 T/W class |
| **Non-A/B Studies** | Patrol / Transport | None (Dry only) | 12,000 to 19,000 lbf | 200 to 550 lb/s | Unstated | Unstated | Bypass ratio 0.8 to 5.0 across four study points |

#### Key Conclusions and Modeling Relevance
- Moving from the 16,000 lbf -400 to the 17,700 lbf -402 EPE did not resize the fan. GE increased fan speed by up to 2%, elevated dry TIT by +100 °F, elevated afterburning TIT by +175 °F, and integrated the RM12 afterburner.
- Engine aging is compensated by opening the variable exhaust nozzle throat ($A_8$). This holds fan speed and $T_5$ constant while lowering the fan operating line, preserving hot section life at the expense of a small performance penalty.
- Thermal barrier coatings on turbine airfoils yield +150 °F higher turbine rotor inlet temperature at constant cooling flow, or permit a 10% reduction in cooling bleed at constant temperature.

---

### 5. Ray (1990) - Ground and Flight Thrust Calculation Benchmark

- **Note**: [NASA TP 3001 - Evaluation of Various Thrust Calibration Techniques on an F404 Engine (April 1990).md](md/NASA%20TP%203001%20-%20Evaluation%20of%20Various%20Thrust%20Calibration%20Techniques%20on%20an%20F404%20Engine%20%28April%201990%29.md)
- **Source PDF**: [NASA TP 3001 - Evaluation of Various Thrust Calibration Techniques on an F404 Engine (April 1990).pdf](pdf/NASA%20TP%203001%20-%20Evaluation%20of%20Various%20Thrust%20Calibration%20Techniques%20on%20an%20F404%20Engine%20%28April%201990%29.pdf)
- **Citation**: Ronald J. Ray, *Evaluation of Various Thrust Calibration Techniques on an F404 Engine*, NASA Technical Paper 3001 (Errata issued May 1990: title corrected to *Evaluation of Various Thrust Calculation Techniques on an F404 Engine*), April 1990.
- **Context**: Investigation evaluating four thrust calculation techniques against load-cell thrust measurements in NASA Lewis PSL Test Cell 4 using F404-GE-400 engine S/N 215-209. Results were confirmed using X-29A flight test data.

#### Methods Evaluated
1. **Scale Measured Thrust ($FG_{\text{meas}}$)**: Overhead thrust bed with multi-axis calibrated load cells and bellmouth inlet in PSL Cell 4.
2. **In-Flight Thrust Program WT Method ($FG_{WT}$)**: Mass Flow-Temperature gas generator technique (GE Program 83112).
3. **In-Flight Thrust Program AP Method ($FG_{AP}$)**: Area-Pressure gas generator technique (GE Program 83112).
4. **Simplified Gross Thrust Method ($FG_{SGTM}$)**: 1D gas dynamic model developed by Computing Devices Company using only internal pressures ($PT_{558}$, $PS_6$, $PS_7$) and ambient static pressure ($P_0$).
5. **Engine Specification Model ($FG_{\text{spec}}$)**: Uncalibrated cycle deck predicting average F404-GE-400 performance (GE Program 80031A(U)).

#### Accuracy Comparison Against PSL Load-Cell Measurements [Direct Comparison of M-MOD against M-DIR Load Cells: Table 6 of TP-3001]

| Power Setting Regime | Test Points | Method | Mean Bias Error | $2\sigma$ Random Error Band |
| :--- | :---: | :--- | :--- | :--- |
| **Full Range (PLA 40° to 130°)** | 131 | $FG_{WT}$ (Mass Flow–Temp) | +0.03% | $\pm 1.12\%$ |
| | 131 | $FG_{AP}$ (Area-Pressure) | -0.05% | $\pm 1.28\%$ |
| | 131 | $FG_{SGTM}$ (ComDev 1D) | -0.07% | $\pm 1.80\%$ |
| | 131 | $FG_{\text{spec}}$ (Uncalibrated Deck) | -1.30% | $\pm 8.74\%$ |
| **Dry Power (PLA 40° to 87°)** | 81 | $FG_{WT}$ | +0.04% | $\pm 1.33\%$ |
| | 81 | $FG_{AP}$ | -0.16% | $\pm 1.29\%$ |
| | 81 | $FG_{SGTM}$ | -0.04% | $\pm 2.14\%$ |
| | 81 | $FG_{\text{spec}}$ | -0.01% | $\pm 11.57\%$ |
| **Afterburning (PLA 90° to 130°)** | 50 | $FG_{WT}$ | +0.01% | $\pm 0.68\%$ |
| | 50 | $FG_{AP}$ | +0.12% | $\pm 1.18\%$ |
| | 50 | $FG_{SGTM}$ | +0.10% | $\pm 1.04\%$ |
| | 50 | $FG_{\text{spec}}$ | -2.09% | $\pm 4.22\%$ |
| **Flight Idle (PLA 31°)** | 19 | $FG_{WT}$ | -0.05% | $\pm 4.22\%$ |
| | 19 | $FG_{AP}$ | +1.72% | $\pm 10.04\%$ |
| | 19 | $FG_{SGTM}$ | Invalid below 40° PLA | Invalid below 40° PLA |
| | 19 | $FG_{\text{spec}}$ | -29.69% | $\pm 23.69\%$ |

#### Computational Resource Benchmarks (ELXSI 6400 Computer)
- ComDev SGTM consumed 9.50% of the memory and 2.21% of the CPU execution time required by the GE IFT program.
- GE Specification model consumed 1,745% of the memory and 248% of the CPU time required by the GE IFT program.

#### Relevance to Cycle Modeling
Uncalibrated manufacturer specification models deviate from individual production engines: across the full operational range (PLA 40° to 130°, 131 test points), the specification model exhibited a 2σ random scatter of ±8.74% (at dry power PLA 40° to 87°, 2σ scatter was ±11.57%; at flight idle, mean bias reached -29.69% with ±23.69% 2σ scatter). Cycle decks require empirical tuning factors to match specific physical engines. The Computing Devices Company SGTM formulation demonstrated a 2σ random scatter band of ±1.04% relative to the NASA Lewis PSL load-cell thrust cradle during afterburning (PLA 90° to 130°), measuring gross thrust from five internal pressure taps without fuel flow meters or mechanical throat area sensors.

---

### 6. Johnson (1990) - Dynamic Engine Simulation for Thrust Vectoring

- **Note**: [NASA TM-4240 - A simple Dynamic Engine Model for Use in a Real-time Aircraft Simulation with Thrust Vectoring.md](md/NASA%20TM-4240%20-%20A%20simple%20Dynamic%20Engine%20Model%20for%20Use%20in%20a%20Real-time%20Aircraft%20Simulation%20with%20Thrust%20Vectoring.md)
- **Source PDF**: [NASA TM-4240 - A simple Dynamic Engine Model for Use in a Real-time Aircraft Simulation with Thrust Vectoring.pdf](pdf/NASA%20TM-4240%20-%20A%20simple%20Dynamic%20Engine%20Model%20for%20Use%20in%20a%20Real-time%20Aircraft%20Simulation%20with%20Thrust%20Vectoring.pdf)
- **Citation**: Steven A. Johnson, *A Simple Dynamic Engine Model for Use in a Real-Time Aircraft Simulation With Thrust Vectoring*, NASA TM-4240 / AIAA-90-2166, October 1990.
- **Context**: Development of a real-time dynamic engine model for the NASA F-18 HARV thrust-vectoring flight simulator at NASA Ames-Dryden. Replaced the iterative GE Dynamic Real Time Model with 3D table interpolation and dynamic filters.

#### Model Architecture and Computational Gains
- Cockpit throttle angle ($PLA$) is processed through a first-order lag filter and rate limiter to yield shaped throttle position ($PLA'$).
- $PLA'$, altitude, and Mach index into steady-state tables generating gross thrust ($FG$), ram drag ($F_{\text{ram}}$), nozzle pressure ratio ($NPR$), nozzle throat area ($A_8$), inlet spillage drag ($D_{\text{inl}}$), and nozzle aft-end drag increment ($D_{\text{noz}}$).
- Execution time fell from 4.0 ms to 0.3 ms per frame on a Gould Sel 97 simulation computer (92.5% reduction), with a 75% reduction in code size and memory footprint.
- Steady-state parameters agreed within 3% of the parent GE model. Transient gross thrust agreed within 20%; nozzle area agreed within 25%.

#### Dynamic Filter Parameters

| Power Regime | PLA Span | Filter Time Constant ($\tau$) | Positive Rate Limit ($\dot{PLA}_{\max}$) | Decreasing Throttle Limit |
| :--- | :--- | :--- | :--- | :--- |
| Non-Afterburning | 31° to 87° | 0.625 s | +19.03 deg/s | None (pure 1st-order decay) |
| Afterburning | 87° to 130° | 0.550 s | +26.81 deg/s | None (pure 1st-order decay) |

#### Full Envelope Max A/B Gross Thrust Grid ($FG$, lbf) [M-MOD: GE Dynamic Real Time Model R88AEB427, Figure 4 of TM-4240]

*Provenance note: This grid represents an off-line tabular surrogate synthesized by running the GE nonlinear dynamic aerothermodynamic cycle deck (Report R88AEB427) across flight conditions. It represents model-derived cycle predictions rather than load-cell thrust stand measurements.*

| Mach Number | Sea Level | 10,000 ft | 20,000 ft | 30,000 ft | 35,000 ft | 40,000 ft | 50,000 ft |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.0 | 16,000 | 12,300 | 8,900 | 5,800 | 4,600 | 3,500 | 2,200 |
| 0.2 | 16,500 | 12,800 | 9,100 | 6,000 | 4,700 | 3,600 | 2,300 |
| 0.4 | 18,500 | 14,500 | 10,200 | 6,900 | 5,300 | 4,100 | 2,800 |
| 0.6 | 20,600 | 16,000 | 11,800 | 8,100 | 6,200 | 4,700 | 3,200 |
| 0.8 | 23,800 | 18,600 | 13,900 | 9,800 | 7,800 | 5,900 | 3,700 |
| 1.0 | 25,000 | 21,800 | 16,400 | 11,900 | 9,400 | 7,400 | 4,500 |
| 1.2 | 27,200 | 25,200 | 19,700 | 14,700 | 11,800 | 9,500 | 5,600 |
| 1.4 | 29,800 | 27,300 | 23,000 | 17,500 | 14,700 | 11,800 | 7,100 |
| 1.6 | 32,500 | 29,300 | 25,000 | 20,600 | 17,500 | 14,300 | 8,600 |
| 1.8 | 36,000 | 33,800 | 27,200 | 22,600 | 20,400 | 16,500 | 9,900 |

#### Installed Drag and Thrust-Vectoring Losses
- At Mach 0.7 and 35,000 ft (Max A/B), installation drag ($F_{\text{ram}} + D_{\text{inl}} + D_{\text{noz}}$) consumes 1,223 lbf (18.5% of gross thrust).
- Deflecting post-exit HARV vanes into the plume reduces axial thrust ($CFGX$):
  - 5 deg deflection: 0.7% thrust loss (30 lbf).
  - 15 deg deflection: 7.7% thrust loss (310 lbf).
  - 25 deg max deflection: 24.4% thrust loss (980 to 1,000 lbf per engine).

#### Relevance to Cycle Modeling
Johnson supplies full flight envelope gross thrust tables for validating pyCycle off-design points. The paper defines installed net thrust book-keeping:
$$FNP = FG \cdot CFGX - F_{\text{ram}} - D_{\text{inl}} - D_{\text{noz}}$$
At high speed and altitude, ram drag and installation increments consume substantial portions of gross thrust, emphasizing the need to separate thermodynamic gross thrust from installed net propulsive force.

---

### 7. Yuhas & Ray (1992) - Compressor Bleed Extraction Thrust Penalties

- **Note**: [Yuhas 1992 - Effects of Bleed ir Extraction of Thrust Levels of the F404-GE-400 Turbofan Engine.md](md/Yuhas%201992%20-%20Effects%20of%20Bleed%20ir%20Extraction%20of%20Thrust%20Levels%20of%20the%20F404-GE-400%20Turbofan%20Engine.md)
- **Source PDF**: [Yuhas 1992 - Effects of Bleed ir Extraction of Thrust Levels of the F404-GE-400 Turbofan Engine.pdf](pdf/Yuhas%201992%20-%20Effects%20of%20Bleed%20ir%20Extraction%20of%20Thrust%20Levels%20of%20the%20F404-GE-400%20Turbofan%20Engine.pdf)
- **Citation**: Andrew J. Yuhas and Ronald J. Ray, *Effects of Bleed Air Extraction on Thrust Levels of the F404-GE-400 Turbofan Engine*, NASA TM-104247 / AIAA-92-3092, July 1992.
- **Context**: Installed static ground tests on the Universal Horizontal Thrust Stand at Edwards AFB using the NASA F/A-18 HARV. Evaluated using compressor bleed air to power pneumatic forebody flow control nozzles for yaw control at high angles of attack.

#### Experimental Setup and Measurement Techniques
- Bleed air was drawn from the annular manifold at the high-pressure compressor discharge (Station 3).
- Airflow passed into the Excess Bleed Air System (EBAS) through 3-in and 6-in Venturi flowmeters, with aircraft ECS capped and fed by external carts.
- Dual load cells on Platform 3 of the thrust stand measured net thrust.
- Ambient conditions: altitude 2,082 to 2,143 ft MSL, ambient temperature $+11^\circ\text{R}$ to $+45^\circ\text{R}$ above standard day (70 to 104 °F), winds under 15 kts.
- Evaluated bleed extraction rates up to 3.5 lb/s across part power (92% $N_2$), military power, and maximum afterburning.

#### Measured Thrust Loss Slopes [M-DIR: Platform 3 Dual Load Cells and Venturi Flowmeters, Table 2 of TM-104247]

$$\text{Thrust (lbf)} = (\text{Bleed Flow Rate [lb/s]}) \times \text{Slope} + \text{Zero-Bleed Intercept}$$

| Power Setting | Engine | Data Source | Slope (lbf / (lb/s bleed)) | Zero-Bleed Intercept (lbf) | % Loss per 1 lb/s Bleed |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **92% $N_2$ (Part)** | Left | Model (LP005S) | -97 | 5,875 | 1.65% |
| | Left | **Measured** | **-125** | **6,311** | **1.98%** |
| | Right | Model (LP005S) | -89 | 5,503 | 1.62% |
| | Right | **Measured** | **-100** | **6,079** | **1.64%** |
| **Military Power** | Left | Model (LP005S) | -245 | 9,194 | 2.66% |
| | Left | **Measured** | **-177** | **8,774** | **2.02%** |
| | Right | Model (LP005S) | -246 | 9,086 | 2.70% |
| | Right | **Measured** | **-189** | **8,690** | **2.17%** |
| **Maximum A/B** | Left | Model (LP005S) | -421 | 13,241 | 3.18% |
| | Left | **Measured** | **-371** | **12,873** | **2.88%** |
| | Right | Model (LP005S) | -428 | 12,983 | 3.29% |
| | Right | **Measured** | **-344** | **12,033** | **2.85%** |

#### Operational Limits and Control Coupling
- Manufacturer maximum customer bleed limits (GE model LP005S):
  - Part power: ~5.0% to 7.3% of compressor airflow (~4.1 to 4.3 lb/s at test conditions).
  - Military power: ~2.7% of compressor airflow (~3.0 to 3.1 lb/s).
  - Maximum A/B: ~2.7% of compressor airflow (~2.9 to 2.95 lb/s).
- Thrust loss remains linear up to 3.5 lb/s bleed extraction, extending past the manufacturer specification ceiling.
- At military and afterburning power, the control system modulates nozzle area ($A_8$) to hold scheduled turbine exhaust temperature ($T_{56}$), preventing steady-state over-temperature.
- Rule of thumb: at military power, each 1% increase in customer bleed extraction cuts net thrust by 2%.

#### Relevance to Cycle Modeling
Distinguishes customer bleeds from internal turbine cooling bleeds. Customer bleed air exits the cycle at Station 3 without entering the combustor, turbine, or afterburner. Turbine cooling bleed air is reinjected into turbine stages or the mixer, recovering mass and momentum downstream. Customer bleed extraction imposes a much larger thrust penalty per pound of air. In max A/B, the thrust penalty doubles (-344 to -371 lbf/(lb/s) vs -177 to -189 lbf/(lb/s) dry) because each pound of extracted air removes mass from the afterburner.

---

### 8. Ennix, Burcham, & Webb (1993) - Exhaust Characteristics in Flight

- **Note**: [NASA TM 4538 - Flight-Determine Engine Exhaust Characteristics of an F404 Engine in an F-18 Airplane.md](md/NASA%20TM%204538%20-%20Flight-Determine%20Engine%20Exhaust%20Characteristics%20of%20an%20F404%20Engine%20in%20an%20F-18%20Airplane.md)
- **Source PDF**: [NASA TM 4538 - Flight-Determine Engine Exhaust Characteristics of an F404 Engine in an F-18 Airplane.pdf](pdf/NASA%20TM%204538%20-%20Flight-Determine%20Engine%20Exhaust%20Characteristics%20of%20an%20F404%20Engine%20in%20an%20F-18%20Airplane.pdf)
- **Citation**: Kimberly A. Ennix, Frank W. Burcham, Jr., and Lannie D. Webb, *Flight-Determined Engine Exhaust Characteristics of an F404 Engine in an F-18 Airplane*, NASA TM-4538 / AIAA-93-2543, October 1993.
- **Context**: 95 flyovers of an F-18 over Rogers Dry Lake at Edwards AFB supporting High-Speed Civil Transport subsonic climb noise research. Processed recorded flight parameters through the GE In-Flight Thrust program (Program 83112) using 1D isentropic nozzle relations.

#### Flight Test Scope and Data Provenance
- Pilot stabilized level flight over ground microphones, throttled left engine to flight idle (35° PLA) to isolate noise, and operated right engine at test power.
- Evaluated subsonic climb profile (Mach 0.32 at 3,850 ft to Mach 0.89 at 32,307 ft, intermediate power 102° PLA).
- Evaluated level flight sweeps at 3,800 ft (Mach 0.34 to 0.92, PLA 75° to 102°).
- Evaluated static ground pad runs (AFFTC Edwards, PLA 80° to 102°).
- *Data Provenance Note*: The aircraft carried no physical rake probes or immersion sensors in the exhaust plume. Engineers recorded standard engine sensors onboard and processed them through the GE In-Flight Thrust program (Program 83112, gas generator method) using 1D isentropic nozzle equations. All tabulated exhaust velocities ($V_9, V_{\text{jet}}$), Mach numbers ($M_9, M_{\text{jet}}$), temperatures ($T_8$), and thrusts ($FG$) represent model-derived outputs [M-MOD].

#### Quantitative Exhaust Data Compilation

#### Climb-to-Cruise Profile (PLA = 102°, Intermediate Power; [M-MOD] Table 2 of TM-4538)

| Mach | Altitude (ft MSL) | NPR | Throat Temp ($T_8$, °R) | Mass Flow ($W_8$, lb/s) | Throat Area ($A_8$, in²) | Area Ratio ($AE_9/AE_8$) | Static Ratio ($P_{s9}/P_{\text{amb}}$) | Gross Thrust ($FG$, lbf) | Exit Mach ($M_9$) | Exit Velocity ($V_9$, ft/s) | Ideal Velocity ($V_{\text{jet}}$, ft/s) | Expansion State |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 0.32 | 3,850 | 2.930 | 1,687.0 | 127.6 | 274.6 | 1.430 | 0.539 | 9,125 | 1.69 | 2,744 | 2,305 | Overexpanded |
| 0.61 | 7,292 | 3.090 | 1,683.6 | 132.7 | 298.3 | 1.490 | 0.531 | 9,703 | 1.81 | 2,872 | 2,388 | Overexpanded |
| 0.68 | 12,324 | 3.375 | 1,689.6 | 116.6 | 293.4 | 1.470 | 0.588 | 8,810 | 1.80 | 2,861 | 2,466 | Overexpanded |
| 0.77 | 22,331 | 4.420 | 1,687.2 | 89.2 | 261.5 | 1.390 | 0.868 | 7,381 | 1.73 | 2,780 | 2,679 | Overexpanded |
| 0.89 | 32,307 | 5.240 | 1,682.9 | 66.4 | 251.2 | 1.360 | 1.071 | 5,726 | 1.70 | 2,749 | 2,796 | Underexpanded |

#### Level Speed Sweep at 3,800 ft Altitude ([M-MOD] Table 3 of TM-4538)

| Throttle (PLA) | Mach | NPR | Throat Temp ($T_8$, °R) | Mass Flow ($W_8$, lb/s) | Throat Area ($A_8$, in²) | Area Ratio ($AE_9/AE_8$) | Static Ratio ($P_{s9}/P_{\text{amb}}$) | Gross Thrust ($FG$, lbf) | Exit Mach ($M_9$) | Exit Velocity ($V_9$, ft/s) | Ideal Velocity ($V_{\text{jet}}$, ft/s) | Expansion State |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 75° | 0.34 | 2.244 | 1,423.5 | 92.8 | 249.2 | 1.380 | 0.440 | 5,305 | 1.72 | 2,544 | 1,888 | Overexpanded |
| 80° | 0.61 | 2.782 | 1,542.9 | 107.1 | 245.3 | 1.350 | 0.778 | 7,119 | 1.69 | 2,621 | 2,184 | Overexpanded |
| 100° | 0.80 | 3.658 | 1,718.7 | 163.5 | 303.3 | 1.488 | 0.628 | 12,673 | 1.81 | 2,897 | 2,556 | Overexpanded |
| 102° | 0.92 | 4.136 | 1,713.0 | 177.5 | 297.2 | 1.459 | 0.737 | 14,289 | 1.79 | 2,867 | 2,649 | Overexpanded |

#### Static Ground Runs (AFFTC Edwards, 2,300 ft MSL, Mach 0.0; [M-MOD] Table 4 of TM-4538)

| Throttle (PLA) | NPR | Throat Temp ($T_8$, °R) | Mass Flow ($W_8$, lb/s) | Throat Area ($A_8$, in²) | Area Ratio ($AE_9/AE_8$) | Static Ratio ($P_{s9}/P_{\text{amb}}$) | Gross Thrust ($FG$, lbf) | Exit Mach ($M_9$) | Exit Velocity ($V_9$, ft/s) | Ideal Velocity ($V_{\text{jet}}$, ft/s) | Expansion State |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 80° | 2.055 | 1,437.3 | 91.3 | 249.0 | 1.240 | 0.413 | 4,979 | 1.71 | 2,543 | 1,801 | Overexpanded |
| 87° | 2.330 | 1,527.8 | 100.7 | 249.0 | 1.280 | 0.465 | 6,122 | 1.71 | 2,629 | 1,998 | Overexpanded |
| 92° | 2.610 | 1,622.1 | 110.1 | 249.0 | 1.280 | 0.520 | 7,326 | 1.70 | 2,702 | 2,176 | Overexpanded |
| 102° | 2.720 | 1,671.9 | 120.6 | 264.0 | 1.320 | 0.520 | 8,718 | 1.74 | 2,785 | 2,253 | Overexpanded |

#### Key Conclusions and Modeling Relevance
- Nozzle exit Mach number ($M_9$) remains invariant between 1.69 and 1.81 across all flight conditions, altitudes, and power settings. The cam linkage constrains the effective area expansion ratio ($AE_9/AE_8$) to a narrow band between 1.24 and 1.49.
- During intermediate-power climb, throat total temperature ($T_8$) is held between 1,683 and 1,690 °R across altitudes, and rises to 1,713 to 1,719 °R at low altitude high subsonic speeds.
- Flow expansion crossover occurs near Mach 0.85 between 22,000 and 32,000 ft altitude. Below this crossover, the nozzle operates overexpanded. Above 32,000 ft, nozzle pressure ratio exceeds 5.0 and the nozzle runs underexpanded ($P_{s9}/P_{\text{amb}} = 1.071$).

---

### 9. Hadzic et al. (2010) - Synthetic Fuel Blend Engine Qualification

- **Note**: [Hadzic 2010 - Limited Qualification Tests of an F404 Engine with Blended FT-SPK and NATO F-34 Fuel.md](md/Hadzic%202010%20-%20Limited%20Qualification%20Tests%20of%20an%20F404%20Engine%20with%20Blended%20FT-SPK%20and%20NATO%20F-34%20Fuel.md)
- **Source PDF**: [Hadzic 2010 - Limited Qualification Tests of an F404 Engine with Blended FT-SPK and NATO F-34 Fuel.pdf](pdf/Hadzic%202010%20-%20Limited%20Qualification%20Tests%20of%20an%20F404%20Engine%20with%20Blended%20FT-SPK%20and%20NATO%20F-34%20Fuel.pdf)
- **Citation**: Rastko Hadzic, Jeffrey Bird, Wajid A. Chishty, Darrin Little, and Pierre Poitras, *Limited Qualification Tests of an F404 Engine with Blended Fischer Tropsch SPK and NATO F-34 Fuel*, ASME Paper GT2010-23402, June 2010.
- **Context**: Tri-nation TTCP qualification testing in NRC Canada Test Cell #4 (Ottawa) using a Canadian Forces CF-18 F404-GE-400 engine. 56.1 total test cell hours (34.6 endurance hours) comparing 100% Jet A-1 against a 50/50 semi-synthetic blend with Fischer-Tropsch synthetic paraffinic kerosene (FT-SPK).

#### Fuel Properties and Test Scope
- Baseline fuel: 100% Jet A-1 / NATO F-34 kerosene.
- Test fuel (SSJF): 50% NATO F-34 + 50% FT-SPK (blend of 2/3 Sasol coal-to-liquid IPK and 1/3 Shell gas-to-liquid kerosene).
- Fuel lower heating value (LHV): SSJF possessed +1.3% higher net heat of combustion (43.6 vs 43.1 MJ/kg).
- Fuel density: SSJF possessed 3.6% lower density (784 vs 811.3 kg/m³), with 37% lower aromatics and 55% lower sulfur.
- Engine fuel control density dial remained fixed at 0.81 throughout the campaign.

#### Key Performance Comparisons [M-DIR: Test Cell #4 Cradle and Rakes, Table A-1 and Figures 6-12 of GT2010-23402]

| Parameter / Metric | Unit | Measurement Uncertainty | Baseline Jet A-1 | Test Blend (SSJF Pre-Endurance) | Test Blend (SSJF Post-Endurance) | Observed Delta vs Baseline |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| Fuel Lower Heating Value | MJ/kg | N/A | 43.12 | 43.58 | 43.61 | +1.3% higher LHV |
| Fuel Density at 15 °C | kg/m³ | N/A | 811.3 | 784.0 | 782.5 | -3.6% lower density |
| Start: Time to Light | s | N/A | 7.9 to 8.1 | Within baseline | Within baseline | No difference (<0.3 s scatter) |
| Start: Time to Idle | s | N/A | 20.0 to 21.3 | Within baseline | Within baseline | No difference (<0.3 s scatter) |
| Start: Peak EGT | °C | $\pm 0.9\%$ ratio | ~560 to 570 | ~570 | ~570 | < 1% variation |
| Spool Speed Ratio ($N_1/N_2$) | ratio | $\pm 0.4\%$ | Baseline line | Matches baseline | Matches baseline | Zero bias (within $\pm 0.4\%$ band) |
| Corrected Airflow | N/A | $\pm 0.7\%$ | Baseline ref | Within $\pm 0.6\%$ | Within $\pm 0.6\%$ | Zero shift (within uncertainty) |
| Corrected Fuel Flow ($WFR$) | N/A | $\pm 0.8\%$ | Baseline ref | Biased ~3% lower | Within $\pm 0.8\%$ | Pre: -3% bias; Post: within band |
| Corrected SFC ($SFCR$) | N/A | $\pm 0.9\%$ | Repeatable $\pm 0.4\%$ | +1.2% | -1.4% | Pre: +1.2%; Post: -1.4% |
| Temperature Ratio ($T_5/P_1$) | ratio | $\pm 0.9\%$ | Baseline ref | Within $\pm 0.5\%$ | Within $\pm 0.5\%$ | Zero bias |
| Fan Guide Vane Schedule | deg | N/A | Baseline ($\pm 2^\circ$) | Matches baseline | Matches baseline | No bias |
| Compressor Guide Vanes | deg | N/A | Baseline ($\pm 1^\circ$) | Matches baseline | Matches baseline | No bias |
| Nozzle Area (NPI) | % area | N/A | Baseline ($\pm 0.5\%$) | -7% at max temp trim | Within $\pm 1\%$ | Pre: 7% more closed at trim |
| Idle to IRP Slam Accel ($FWT$) | N/A | $\pm 1.1\%$ | Within 1.0% / 0.3 s | Within 0.8% / 0.2 s | Within 0.8% / 0.2 s | Identical (<0.3 s delta) |
| IRP to Max A/B Slam Accel | N/A | $\pm 1.1\%$ | Within 0.3% / 0.1 s | Within 1.0% / 0.3 s | Within 1.0% / 0.3 s | Identical (<0.3 s delta) |
| A/B Liner Peak Wall Temp | K | $\pm 0.9\%$ | ~550 K | ~550 K | ~550 K | No difference |
| Combustor Noise Peak | Hz / psid | N/A | 515 Hz / ~0.04 psid | 520 Hz / ~0.05 psid | 520 Hz / ~0.05 psid | +5 Hz shift, +0.01 psid |
| A/B Screech / Rumble | Hz | N/A | 182 Hz and 640 Hz | 182 Hz and 640 Hz | 182 Hz and 640 Hz | Identical frequencies |

#### Relevance to Cycle Modeling
Turbomachinery component matching ($N_1/N_2$ spool split, airflow vs corrected speed, guide vane schedules) is invariant to fuel chemistry. Cycle model component maps require zero modification when modeling synthetic fuel blends. Burner fuel mass flow scales with the reciprocal of lower heating value ($\dot{m}_f \propto 1/\text{LHV}$), while lower fuel density demands higher volumetric metering capability from fuel control pumps.

---

## Cross-Study Multi-Condition Reference Map

The table below cross-indexes key performance metrics and aerothermodynamic parameters across the corpus for the F404-GE-400. Operating conditions vary across ground static test cells, altitude simulation chambers, and flight test installations. Each row identifies its operating environment and data provenance.

| Parameter | Value (US / SI Units) | Operating Condition | Provenance & Sources | Modeling Significance |
| :--- | :--- | :--- | :--- | :--- |
| **Max Augmented Thrust ($FG$)** | 16,000 lbf (71.2 kN) | Sea Level Static, Standard Day | [M-SPEC] Frith (1985), Powel (1990); [M-MOD] Johnson (1990) | Uninstalled SLS sizing point |
| **Max Dry Thrust (IRP)** | 10,600 lbf (47.2 kN) | Sea Level Static, Standard Day | [M-SPEC] Frith (1985), Powel (1990) | Uninstalled SLS dry military rating |
| **Max A/B Specific Fuel Consumption** | 1.84 to 1.85 lb/(hr·lbf) (52.1 g/(kN·s)) | Sea Level Static, Standard Day | [M-SPEC] Frith (1985) | SLS Max A/B fuel economy |
| **Dry Specific Fuel Consumption** | 0.78 to 0.81 lb/(hr·lbf) (22.1 g/(kN·s)) | Sea Level Static, Standard Day | [M-SPEC] Frith (1985) | SLS IRP fuel economy |
| **Engine Mass Airflow** | 142 to 145 lb/s (64.4 to 65.8 kg/s) | Sea Level Static, Standard Day | [M-SPEC] Frith (1985) (142 lb/s), Powel (1990) (145 lb/s) | Inlet sizing mass flow |
| **Bypass Ratio (BPR)** | 0.34 | Sea Level Static, Design Point | [M-SPEC] Frith (1985) | Mixer bypass-to-core flow ratio |
| **Overall Pressure Ratio (OPR)** | 25.0:1 | Sea Level Static, Design Point | [M-SPEC] Frith (1985), Powel (1990) | Design cycle pressure ratio |
| **Fan Pressure Ratio (FPR)** | 4.1:1 (nominal 4:1) | Sea Level Static, Design Point | [M-SPEC] Frith (1985), Powel (1990) | 3-stage fan pressure ratio |
| **High-Pressure Compressor PR (HPC PR)** | 6.0:1 (nominal 6.3:1) | Sea Level Static, Design Point | [M-SPEC] Frith (1985) | 7-stage core compressor pressure ratio |
| **Fan Rotor Speed ($N_1$)** | 13,270 rpm | Sea Level Static, Design Point | [M-SPEC] Frith (1985); [M-DIR] Conners (1989) | 100% mechanical LP spool speed |
| **Core Rotor Speed ($N_2$)** | 16,810 rpm | Sea Level Static, Design Point | [M-SPEC] Frith (1985) | 100% mechanical HP spool speed |
| **Turbine Inlet Temperature (TIT)** | 1,390 °C (2,994 °R / 1,663 K) | Sea Level Static, Design Point | [M-SPEC] Frith (1985) | Hot gas path thermodynamic design point |
| **TIT Control Limit Ceiling** | 2,980 °R (1,382 °C / 1,656 K) | Flat-rated temperature ceiling | [M-SPEC] Frith (1985) | Flat-rated combustor exit limit |
| **HPT Vane Cooling Bleed** | 11% of CDP | Sea Level Static, Max Dry | [M-SPEC] Frith (1985) | Compressor discharge air to 1st stage NGV |
| **Dry Nozzle Throat Total Temp ($T_8$)** | 1,683 to 1,690 °R (935 to 939 K) | Climb Flight (M 0.32-0.89, 3.8k-32.3k ft, PLA 102°) | [M-MOD] Ennix et al. (1993, Table 2 via GE IFT) | Intermediate power 1D nozzle throat bulk temperature |
| **Local Peak Plume Stagnation Temp** | 3,750 to 3,800 °R (2,083 to 2,111 K) | Altitude Chamber (M 0.30 at 30k ft, M 0.87 at 24k ft, Max A/B) | [M-DIR] Walton & Burcham (1986, Rake at Station 9+2in) | Local flame peak 1.0 to 2.5 in inside lip; NOT bulk 1D throat temperature |
| **Centerline Plume Pressure Defect** | 20% to 45% total pressure drop | Altitude Chamber (M 0.30 at 30k ft, M 0.87 at 24k ft) | [M-DIR] Walton & Burcham (1986, Figures 9-11) | Turbine centerbody wake defect persisting through nozzle |
| **Nozzle Throat Area ($A_8$) Span** | ~215 to 420 in² | Across flight and ground envelope | [M-DIR] Ray (1990), Conners (1989); [M-MOD] Johnson (1990) | Modulates from ~215 in² at IRP to ~420 in² at Max A/B |
| **Nozzle Expansion Ratio ($AE_9/AE_8$)** | 1.24 to 1.49 | Across flight and ground envelope | [M-MOD] Ennix et al. (1993); [M-DIR] Walton & Burcham (1986) | Kinematic cam linkage limits |
| **Nozzle Exit Mach Number ($M_9$)** | 1.69 to 1.81 | Flight climb and speed sweeps (M 0.32-0.92, 3.8k-32.3k ft) | [M-MOD] Ennix et al. (1993, Tables 2-4 via GE IFT) | Invariant supersonic nozzle exit Mach number |
| **Customer Bleed Thrust Penalty** | -177 to -189 lbf / (lb/s bleed) | Edwards AFB Ground Stand (2,100 ft MSL, hot day, Military power) | [M-DIR] Yuhas & Ray (1992, Table 2) | HPC Station 3 customer bleed; doubles to -344 to -371 lbf at Max A/B |
| **Customer Bleed Percentage Rule** | ~2% net thrust loss per 1% bleed | Edwards AFB Ground Stand (Military power) | [M-DIR] Yuhas & Ray (1992) | Sensitivity rule of thumb for customer extraction |
| **In-Flight Net Thrust Uncertainty** | WT: 3.19% avg; AP: 6.11% avg | X-29A Flight Envelope (10k-40k ft, M 0.4-1.6) | [M-MOD] Conners (1989, Table 4 via GE IFT) | Mass Flow-Temp (WT) vs Area-Pressure (AP) error bounds |
| **Uncalibrated Spec Model Error** | 2σ = ±8.74% (range 40°-130°); -29.7% at idle | NASA Lewis PSL Cell 4 (11 flight conditions) | [M-DIR / M-MOD Comparison] Ray (1990, Table 6) | Scatter of standard manufacturer engine deck vs test stand |

---

## Research Selection Guide for Cycle Modelers

Depending on your modeling or validation objective, consult the following specific papers:

1. **Cycle Architecture, Station Geometries, and Bleed Fractions**:
   - Consult [Frith (1985)](md/ADA164562%20The%20General%20Electric%20F404%20-%20Engine%20of%20the%20RAAF%27s%20New%20Fighter.md) for component pressure ratios, stage counts, HPT cooling bleed fractions (11% CDP), and physical dimensions.

2. **In-Flight Thrust Calibration and Scale Thrust Verification**:
   - Consult [Ray (1990)](md/NASA%20TP%203001%20-%20Evaluation%20of%20Various%20Thrust%20Calibration%20Techniques%20on%20an%20F404%20Engine%20%28April%201990%29.md) for load-cell test stand data, error bands of the ComDev SGTM pressure method vs GE IFT gas generator deck, and uncalibrated model errors.

3. **Sensor Sensitivity and Error Propagation**:
   - Consult [Conners (1989)](md/NASA%20TM%204140%20-%20Measurement%20Effects%20on%20the%20Calculation%20of%20In-Flight%20Thrust%20for%20an%20F404%20turbofan%20engine.md) for numerical sensitivity derivatives ($C_i$) of net thrust with respect to all 10 engine sensors, and the error cancellation proof of the WT method.

4. **Exhaust Nozzle Flow Properties, Temperature Stratification, and Exit Mach Number**:
   - Consult [Walton & Burcham (1986)](md/Exhaust-Gas%20P%20%26%20T%20Survey%20of%20F404-GE-400%20engine.md) for physical rake surveys, core centerline momentum defects, and peak 3,800 °R temperatures.
   - Consult [Ennix et al. (1993)](md/NASA%20TM%204538%20-%20Flight-Determine%20Engine%20Exhaust%20Characteristics%20of%20an%20F404%20Engine%20in%20an%20F-18%20Airplane.md) for tabulated climb-to-cruise exhaust data, nozzle pressure ratios, and proof of invariant $M_9 \approx 1.7 - 1.8$.

5. **Customer Bleed Extraction Modeling**:
   - Consult [Yuhas & Ray (1992)](md/Yuhas%201992%20-%20Effects%20of%20Bleed%20ir%20Extraction%20of%20Thrust%20Levels%20of%20the%20F404-GE-400%20Turbofan%20Engine.md) for linear thrust loss slopes at dry and afterburning settings, customer bleed limits, and nozzle control coupling.

6. **Engine Sizing across Variants and Deterioration Control**:
   - Consult [Powel (1990)](md/Powel%201990%20-%20On%20the%20Leading%20Edge%2C%20Combining%20Maturity%20and%20Advanced%20Technology%20on%20the%20F404%20Turbofan%20Engine.md) for the growth roadmap from F404-400 to F404-402 EPE, RM12, F412, and non-afterburning study engines, plus deterioration compensation via $A_8$ nozzle scheduling.

7. **Flight Simulation Surrogate Models and Installation Drag**:
   - Consult [Johnson (1990)](md/NASA%20TM-4240%20-%20A%20simple%20Dynamic%20Engine%20Model%20for%20Use%20in%20a%20Real-time%20Aircraft%20Simulation%20with%20Thrust%20Vectoring.md) for full flight envelope gross thrust look-up tables (0 to 50k ft, M 0 to 1.8), throttle rate limits and lag time constants, and thrust-vectoring vane drag penalties.

8. **Alternative Fuels and Chemical Sensitivity**:
   - Consult [Hadzic et al. (2010)](md/Hadzic%202010%20-%20Limited%20Qualification%20Tests%20of%20an%20F404%20Engine%20with%20Blended%20FT-SPK%20and%20NATO%20F-34%20Fuel.md) for empirical evidence that turbomachinery aerodynamic matching remains invariant under synthetic kerosene blends.
