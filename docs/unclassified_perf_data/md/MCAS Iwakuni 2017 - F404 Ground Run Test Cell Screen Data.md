---
title: "MCAS Iwakuni 2017 - F404 Ground Run Test Cell Screen Data"
author: "AiirSource Military / USMC MCAS Iwakuni"
year: 2017
source: "AiirSource Military, 'Marines Test F-18 Jet's Powerful F404 Engine' (YouTube, 16 June 2017)"
url: "https://www.youtube.com/watch?v=gyaKh7BY-6c"
type: test_data
tags: [f404, reference/perf-data, ground-idle, test-cell]
created: 2026-10-25
updated: 2026-10-25
status: converted
---

# MCAS Iwakuni (2017) — F404 Ground Run Test Cell Screen Data

**Source Video:** *Marines Test F-18 Jet's Powerful F404 Engine*  
**Channel:** AiirSource Military  
**Upload Date:** 16 June 2017  
**Direct URL:** [https://www.youtube.com/watch?v=gyaKh7BY-6c](https://www.youtube.com/watch?v=gyaKh7BY-6c)  
**Location:** Marine Corps Air Station (MCAS) Iwakuni, Japan  
**Test Facility:** Fixed Ground Engine Test Cell (indoor hush-house / test bed)  
**Engine:** General Electric F404-GE-400 / F404-GE-402 turbofan  

---

## 1. Context & Operational Background

During intermediate/depot-level maintenance and acceptance testing, USMC propulsion technicians operate the General Electric F404 on an indoor test cell thrust frame to verify mechanical integrity, variable geometry schedules, lubrication system parameters, vibration levels, and gas turbine thermodynamic performance prior to airframe installation in the F/A-18 Hornet.

A sequence in the source video presents the test conductor's supervisory control console displaying real-time telemetry on the **`RUN SHEET PARAMETERS`** screen. Seven high-resolution freeze frames capture two distinct low-power operating regimes:
1. **Frames 1–6:** Steady-state Ground Idle operation at $\text{PLA} = 18.1^\circ$.
2. **Frame 7:** Slightly advanced low-throttle operation at $\text{PLA} = 21.4^\circ$.

Because previously documented F404 unclassified cycle decks and flight-test literature (e.g. [[NASA TM-4240 - A simple Dynamic Engine Model for Use in a Real-time Aircraft Simulation with Thrust Vectoring|Johnson 1990]]) define **Flight Idle** at $\text{PLA} = 31^\circ$, this dataset provides empirical measurements of the true **Ground Idle** ($\text{PLA} = 18.1^\circ$) operating point, including rotor speeds, station pressures, variable geometry positions, and nozzle throat schedule.

---

## 2. Test Cell Screen Captures

| Frame | Timestamp (Capture) | PLA | Key Features | Image Asset |
| :---: | :---: | :---: | :--- | :--- |
| **1** | 8:03:43 PM | $18.1^\circ$ | Ground idle baseline, $N_1 = 4100$, $N_2 = 10955$, EOP normal background | ![](images/mcas-iwakuni-2017/frame_1_pla18_1_80343pm.png) |
| **2** | 8:04:51 PM | $18.1^\circ$ | Steady idle, EOP turns yellow caution ($97.1\text{ psid}$), baro visible | ![](images/mcas-iwakuni-2017/frame_2_pla18_1_80451pm.png) |
| **3** | 8:05:19 PM | $18.1^\circ$ | Steady idle, $N_1 = 4089$, $N_2 = 10936$, EOP yellow ($96.5\text{ psid}$) | ![](images/mcas-iwakuni-2017/frame_3_pla18_1_80519pm.png) |
| **4** | 8:07:19 PM | $18.1^\circ$ | Steady idle, unobstructed view of `PBAROHG` and `Cell_Ref` ($29.95\text{ inHg}$) | ![](images/mcas-iwakuni-2017/frame_4_pla18_1_80719pm.png) |
| **5** | 8:10:59 PM | $18.1^\circ$ | Steady idle, thermal equilibrium, $N_2\% = 65.0\%$, $T_5 = 445^\circ\text{C}$ | ![](images/mcas-iwakuni-2017/frame_5_pla18_1_81059pm.png) |
| **6** | 8:11:50 PM | $18.1^\circ$ | Steady idle final frame, $N_1 = 4089$, $N_2 = 10933$, $W_{f,\text{core}} = 941\text{ pph}$ | ![](images/mcas-iwakuni-2017/frame_6_pla18_1_81150pm.png) |
| **7** | 8:17:47 PM | $21.4^\circ$ | Advanced throttle, $N_1 \to 4180$, $N_2 \to 11067$, $PS_3 \to 38.4\text{ psia}$, EOP normal | ![](images/mcas-iwakuni-2017/frame_7_pla21_4_81747pm.png) |

---

## 3. Digitized Run Sheet Telemetry Table [M-DIR]

All numerical values transcribed directly from the operator screen displays across the seven capture frames:

| Parameter Label | Definition & Station Reference | Units | Frame 1 | Frame 2 | Frame 3 | Frame 4 | Frame 5 | Frame 6 | Frame 7 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **PLA** | Power Lever Angle | deg | 18.1 | 18.1 | 18.1 | 18.1 | 18.1 | 18.1 | **21.4** |
| **Fan Speed** | Physical LP Spool Rotor Speed ($N_1$) | rpm | 4100 | 4093 | 4089 | 4089 | 4089 | 4089 | **4180** |
| **Core Speed** | Physical HP Spool Rotor Speed ($N_2$) | rpm | 10955 | 10942 | 10936 | 10935 | 10934 | 10933 | **11067** |
| **N2%** | High Pressure Spool Speed Percentage | % | 65.2 | 65.1 | 65.1 | 65.1 | 65.0 | 65.0 | **65.8** |
| **FN** | Test Cradle Load Cell Net Thrust Reading | lbf | -2025 | -2036 | -2040 | -2039 | -2047 | -2053 | **-2061** |
| **PS3** | High Pressure Compressor Discharge Static Pressure ($PS_3$) | psia | 36.3 | 36.3 | 36.3 | 36.3 | 36.3 | 36.2 | **38.4** |
| **PT5.6** | Turbine Exhaust / Mixer Inlet Total Pressure ($Pt_{5.6}$) | psia | 15.1 | 15.1 | 15.1 | 15.1 | 15.1 | 15.1 | **15.2** |
| **T5C** | Turbine Temperature Sensor (Control / Calculated; station unverified) | °C | 443 | 444 | 445 | 445 | 445 | 445 | **456** |
| **T5Ha** | Turbine Temperature Sensor (Harness 'A' Average; station unverified) | °C | 442 | 443 | 444 | 444 | 444 | 445 | **455** |
| **J61 T5H** | J61 T5 Thermocouple Harness Differential / Spread | °F | 5 | 5 | 9 | 10 | 10 | 11 | **16** |
| **T1** | Engine Inlet Total Temperature | °C | 26 | 26 | 26 | 26 | 26 | 26 | 26 |
| **T0AvgF** | Average Ambient / Test Cell Temperature | °F | 38 | 39 | 39 | 39 | 39 | 39 | **38** |
| **A8** | Variable Exhaust Nozzle Throat Area Indication | % | 75.7 | 75.7 | 75.7 | 75.7 | 75.7 | 75.7 | 75.7 |
| **FVG** | Fan Variable Guide Vane Angle | deg | 49.4 | 49.4 | 49.4 | 49.4 | 49.4 | 49.4 | 49.4 |
| **CVG** | Compressor Variable Geometry Vane Angle | deg | 52.5 | 52.5 | [52.5] | 52.5 | 52.5 | 52.5 | **52.3** |
| **Wfcore** | Core Fuel Mass Flow (Engine Internal Transmitter) | pph | 949 | 942 | 941 | 941 | 941 | 941 | **946** |
| **WFCELL** | Facility Fuel Flow (Test Cell External Flowmeter) | pph | 665 | 670 | 669 | 667 | 666 | 666 | **681** |
| **Pfin** | Fuel Boost Inlet Pressure at Engine Flange | psig | 55.1 | 55.1 | 55.1 | 55.1 | 55.1 | 55.0 | 55.0 |
| **EOP** | Engine Oil Differential Pressure | psid | 97.6 | 97.1 *(yel)* | 96.5 *(yel)* | 96.6 *(yel)* | 96.5 *(yel)* | 96.5 *(yel)* | **98.1** |
| **TSUMPAF** | Lube Oil Sump 'A' Temperature | °F | 98 | 99 | 100 | 100 | 100 | 100 | 100 |
| **TSCAVBF** | Lube Oil Scavenge 'B' Temperature | °F | 103 | 104 | 104 | 104 | 104 | 105 | 105 |
| **FFH** | Front Frame Horizontal Vibration Velocity | ips | 0.09 | 0.09 | 0.09 | 0.09 | 0.09 | 0.09 | 0.09 |
| **ECMS** | Engine Condition Monitoring System Vibration | ips | 0.09 | 0.09 | 0.09 | 0.09 | 0.09 | 0.09 | 0.09 |
| **MRH** | Mid-Ring / Main Bearing Horizontal Vibration | ips | 0.14 | 0.13 | 0.13 | 0.13 | 0.13 | 0.13 | 0.13 |
| **PBAROHG** | Ambient Barometric Pressure | inHg | [29.95] | 29.95 | [29.95] | 29.95 | 29.95 | 29.95 | 29.95 |
| **Cell_Ref** | Test Cell Reference Static Pressure | inHg | [29.95] | [29.95] | [29.95] | 29.95 | 29.95 | 29.95 | 29.95 |

*Note: Values in brackets `[...]` denote fields partially occluded by the operator's silhouette in that video frame, where the reading is verified identical by adjacent frames. `(yel)` denotes that the display field was highlighted in yellow caution color.*

---

## 4. Parameter Definitions & Engineering Interpretation

### Aerothermodynamic & Performance Parameters
- **`PLA` (Power Lever Angle, deg):** Commanded cockpit/throttle angle. In NASA TM-4240 (Johnson 1990), flight PLA spans from $31^\circ$ (flight idle) to $87^\circ$ (intermediate / military rated power) and $130^\circ$ (maximum afterburner). The observed $18.1^\circ$ setting confirms a true Ground Idle condition below flight idle.
- **`Fan Speed` / `N1` (rpm):** Physical rotational speed of the Low-Pressure (LP) spool (3-stage fan driven by the single-stage LPT). At Ground Idle ($4,089\text{ rpm}$), the LP spool runs at $30.8\%$ of its $100\%$ design mechanical rating ($13,270\text{ rpm}$).
- **`Core Speed` / `N2` (rpm) & `N2%` (%):** Physical rotational speed of the High-Pressure (HP) spool (7-stage HPC driven by single-stage HPT). At Ground Idle ($10,933\text{ rpm}$), the core spool operates at exactly $65.0\%$ of its $100\%$ mechanical rating ($16,810\text{ rpm}$), matching `N2% = 65.0%`.
- **`PS3` (Compressor Discharge Static Pressure, psia):** Static pressure measured at Station 3 (exit of the 7-stage HPC / diffuser inlet ahead of the combustor dome). With ambient barometric pressure $P_0 = 29.95\text{ inHg} = 14.71\text{ psia}$, the compressor discharge static-to-ambient pressure ratio proxy is:
  $$\left(\frac{PS_3}{P_0}\right)_{\text{ground-idle}} = \frac{36.3}{14.71} \approx 2.47$$
  *Caution on Cycle OPR Comparison:* This $PS_3 / P_0$ ratio is an exit-static-to-ambient proxy and does not directly equal the total-to-total overall pressure ratio ($\text{OPR} = Pt_3 / Pt_1$) used in aerothermodynamic cycle sizing. At ground idle, the compressor discharge Mach number is small (typically $M_3 \approx 0.15 - 0.25$, giving dynamic head $Pt_3/PS_3 \approx 1.02 - 1.04$) and the test cell inlet is static ($Pt_1 \approx P_0$), meaning total OPR is slightly above this static ratio. When advanced to $\text{PLA} = 21.4^\circ$, $PS_3$ increases to $38.4\text{ psia}$ ($PS_3 / P_0 \approx 2.61$).
- **`PT5.6` (Turbine Exit / Mixer Inlet Total Pressure, psia):** Total pressure at Station 5.6 (aft of the single-stage LPT exhaust frame and ahead of the confluent mixer). At Ground Idle, $PT_{5.6} = 15.1\text{ psia}$, which is approximately $0.39\text{ psi}$ above ambient barometric pressure ($14.71\text{ psia}$), confirming that exhaust flow through the mixer and augmentor duct is unchoked at idle.
- **`T5C` & `T5Ha` (Turbine Temperature Sensors, °C):** Indicated gas temperature from the engine turbine thermocouple harness. The screen display does not identify the physical gas-path station. In general gas turbine conventions, Station 5 denotes the low-pressure turbine exit. However, primary F404 literature (e.g. Henry & Moffatt 1988, ASME 88-GT-222) explicitly defines F404 $T_5$ as the **Low Pressure Turbine Inlet Total Temperature** (SAE/pyCycle Station 4.5, $Tt_{45}$, between the HPT rotor exit and LPT stator inlet), reserving Station 5.5/5.6 for turbine exhaust. Future cycle modelers calibrating turbine temperatures must treat the exact physical sensor station as unverified between Station 4.5 ($Tt_{45}$ interturbine) and Station 5.0/5.6 ($Tt_5$ turbine exhaust) rather than assuming LPT exit. On screen:
  - `T5Ha`: Direct thermocouple average from Harness 'A' of the dual-harness engine sensor installation.
  - `T5C`: Calculated / Control turbine temperature synthesized by the electronic engine control unit (ECU).
  - Both channels track within $1^\circ\text{C}$ ($442^\circ\text{C} - 445^\circ\text{C}$ at Ground Idle, $455^\circ\text{C} - 456^\circ\text{C}$ at $\text{PLA} = 21.4^\circ$).
- **`J61 T5H` (°F):** Connector J61 T5 thermocouple harness differential / channel spread. The reading ($5^\circ\text{F} - 16^\circ\text{F}$) monitors channel-to-channel or circumferential thermocouple divergence to verify sensor health.
- **`FN` (Net Thrust, lbf):** Raw test cradle load cell indication. On ground test stands, load cell instrumentation often incorporates a compression tare/pre-load offset on the restraining linkage, resulting in a signed negative raw channel display ($-2,025 \text{ to } -2,061\text{ lbf}$) prior to test cell tare subtraction.
- **`A8` (Exhaust Nozzle Throat Position, %):** Variable exhaust nozzle (VEN) throat area actuator position. Held steady at $75.7\%$ open across all frames. In the F404 nozzle schedule, $A_8$ opens wide at idle to relieve backpressure on the low-pressure turbine and reduce idle thrust on the ground.
- **`FVG` & `CVG` (Variable Vane Angles, deg):**
  - `FVG` ($49.4^\circ$): Fan Variable Guide Vane position.
  - `CVG` ($52.3^\circ - 52.5^\circ$): Compressor Variable Geometry stator vane angle.
  - Schedulers hold the variable vanes near their minimum-flow/closed stop to maintain compressor flutter and stall margin at low corrected speeds.

### Fuel & Lubrication Systems
- **`Wfcore` vs `WFCELL` (Fuel Flow Rates, pph):**
  - `Wfcore` ($941 - 949\text{ pph}$, $\approx 0.261 - 0.264\text{ lbm/s}$): Fuel mass flow metered to the engine main combustor nozzles, measured by the engine's internal fuel flow transmitter.
  - `WFCELL` ($665 - 681\text{ pph}$, $\approx 0.185 - 0.189\text{ lbm/s}$): Fuel mass flow measured by the facility's external test cell flowmeter (e.g. Coriolis or calibrated turbine meter).
  - The offset between engine-mounted transmitter output and test cell calibration meters is standard in depot testing due to transmitter density/viscosity calibration curves, bypass/spillback recirculation flows from the hydromechanical fuel control (which uses fuel as actuation hydraulic fluid for VEN and VG actuators), or facility meter calibration factors.
- **`Pfin` (Fuel Inlet Pressure, psig):** Fuel boost delivery pressure ($55.0 - 55.1\text{ psig}$) from the test facility fuel conditioning skid to the engine high-pressure pump inlet.
- **`EOP` (Engine Oil Pressure, psid):** Differential lubrication oil pressure across the engine bearing oil supply gallery. The display shows normal background at $97.6\text{ psid}$ (Frame 1) and $98.1\text{ psid}$ (Frame 7), but highlights in yellow caution at $96.5 - 97.1\text{ psid}$ (Frames 2–6). The specific test cell advisory logic (e.g. lower threshold advisory band, rate of change warning, or unacknowledged warning state) cannot be confirmed from the display alone; the data records the observed values and highlight states.
- **`TSUMPAF` & `TSCAVBF` (Oil Temperatures, °F):**
  - `TSUMPAF` ($98^\circ\text{F} - 100^\circ\text{F}$): Lube oil Sump 'A' temperature.
  - `TSCAVBF` ($103^\circ\text{F} - 105^\circ\text{F}$): Lube oil Scavenge 'B' temperature.

### Mechanical Vibration Pickups
- **`FFH`, `ECMS`, `MRH` (Vibration Velocity, ips):**
  - `FFH` ($0.09\text{ ips}$): Front Frame Horizontal velocity pickup.
  - `ECMS` ($0.09\text{ ips}$): Engine Condition Monitoring System vibration sensor.
  - `MRH` ($0.13 - 0.14\text{ ips}$): Mid-Ring / Main-Frame Horizontal velocity pickup.
  - All channels read well below the standard engine maintenance reject limit of $0.5 - 1.0\text{ ips}$, reflecting smooth mechanical balance.

### Ambient Test Cell Environment
- **`PBAROHG` & `Cell_Ref` ($29.95\text{ inHg}$):** Atmospheric pressure in inches of mercury ($29.95\text{ inHg} = 101.42\text{ kPa} = 14.71\text{ psia}$). MCAS Iwakuni sits at sea level (elevation $\approx 10\text{ ft}$), placing ambient conditions within $0.02\text{ inHg}$ of standard sea level pressure ($29.92\text{ inHg}$).
- **`T0AvgF` ($38^\circ\text{F} - 39^\circ\text{F}$):** Average ambient air temperature inside the intake duct / test cell bellmouth ($3.3^\circ\text{C} - 3.9^\circ\text{C}$, $497.7\text{ R}$).
- **`T1` ($26^\circ\text{C} = 78.8^\circ\text{F}$):** Engine inlet total temperature sensor channel. Note that $T_1$ reflects test cell internal thermal dissipation or sensor bias relative to the cold intake bellmouth average ($T_0 \approx 39^\circ\text{F}$).

---

## 5. Aerothermodynamic Cycle Comparison

Comparison of the MCAS Iwakuni Ground Idle test cell data against substantiated public F404 literature and cycle ratings:

| Cycle Parameter | Ground Idle (MCAS Iwakuni, 2017) | Flight Idle (NASA TM-4240 / Johnson 1990) | Design Point (SLS Dry Mil Rating) |
| :--- | :---: | :---: | :---: |
| **PLA** | $18.1^\circ$ [M-DIR] | $31.0^\circ$ [M-SPEC] (p. 2) | $87.0^\circ$ (Johnson 1990) / $\approx 85^\circ$ [M-SPEC] |
| **$N_1$ Physical Speed** | $4,089\text{ rpm}$ ($30.8\%$) [M-DIR] | *Not reported* | $13,270\text{ rpm}$ ($100\%$) [M-SPEC] (Frith 1985) |
| **$N_2$ Physical Speed** | $10,933\text{ rpm}$ ($65.0\%$) [M-DIR] | *Not reported* | $16,810\text{ rpm}$ ($100\%$) [M-SPEC] (Frith 1985) |
| **Static Pressure Ratio ($PS_3 / P_0$)** | $2.47:1$ [M-DIR] *(proxy)* | *Not reported* | $\approx 25.0:1$ (Total OPR $Pt_3/Pt_1$) [M-SPEC] |
| **Compressor Exit Static ($PS_3$)** | $36.3\text{ psia}$ [M-DIR] | *Not reported* | $\approx 367\text{ psia}$ (nominal CDP) |
| **Turbine Exit Total Pressure ($PT_{5.6}$)** | $15.1\text{ psia}$ [M-DIR] | *Not reported* | $\approx 42\text{ psia}$ |
| **Turbine Temp ($T_5$)** | $444^\circ\text{C}$ ($1,291^\circ\text{R}$) [M-DIR] *(unverified station)* | *Not reported* | $1,692 - 1,746^\circ\text{R}$ (LPT inlet $Tt_{45}$) [M-PLOT] (Henry 1988) |
| **Core Fuel Flow ($W_f$)** | $941\text{ pph}$ ($0.261\text{ lbm/s}$) [M-DIR] | *Not reported* | $\approx 8,500\text{ pph}$ [M-SPEC] |
| **Nozzle Position ($A_8$)** | $75.7\%$ open [M-DIR] | $400\text{ in}^2$ [M-MOD] (p. 8) | $\approx 232 - 249\text{ in}^2$ [M-DIR] (TM-4538, TM-4140) |

*Note on Johnson (1990) Flight Idle Data:* NASA TM-4240 developed a simplified real-time dynamic simulation model whose tabular lookup blocks only recorded steady-state gross thrust ($FG$), ram drag ($F_{\text{ram}}$), nozzle pressure ratio (NPR), nozzle throat area ($A_8$), and installation drags as functions of Mach, altitude, and PLA (breakpoints: flight idle $31^\circ$, Mil power $87^\circ$, Min AB, Max AB). Internal turbomachinery spool speeds, station pressures, gas temperatures, and fuel flows were not included in the simple model tables and are therefore designated as *Not reported* rather than speculative.

### Modeling Significance
1. **Low-Power Off-Design Sizing Anchor:** Provides direct empirical validation points for pyCycle off-design part-power operating lines at ground idle ($\text{PLA} = 18.1^\circ$) where public data has historically been sparse.
2. **Variable Exhaust Nozzle Schedule Validation:** Confirms the F404 VEN schedule holds $A_8$ at $\approx 75.7\%$ open at idle to prevent turbine backpressure and eliminate residual ground idle thrust.
3. **Spool Speed Matching:** Verifies that at ground idle, the core spool governs at $\approx 65\%$ mechanical speed while the LP fan spool windmilling/driving speed drops to $\approx 31\%$.
