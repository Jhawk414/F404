// ==============================================================================
// GE F404 Turbofan Cycle Architecture Diagram
// Built with Typst & CeTZ vector drawing engine
// ==============================================================================
// Compile commands:
//   typst compile docs/f404_cycle.typ docs/f404_cycle.svg
//   typst compile --ppi 300 docs/f404_cycle.typ docs/f404_cycle.png
// ==============================================================================

#set page(
  width: auto,
  height: auto,
  margin: (x: 1.0cm, top: 0.9cm, bottom: 0.9cm),
  fill: white,
)

#set text(
  font: ("Palatino", "Charter", "Georgia", "Helvetica Neue"),
  size: 10pt,
)

#import "@preview/cetz:0.3.4": canvas, draw

// --- Color & Style Design Tokens ---
#let cyan-accent   = rgb("#0090ff")
#let cyan-stroke   = 1.6pt + cyan-accent
#let dark-slate    = rgb("#0f172a")
#let text-muted    = rgb("#475569")
#let flow-stroke   = 1.35pt + dark-slate
#let amber-shaft   = rgb("#d97706")
#let bypass-blue   = rgb("#2563eb")
#let bleed-gray    = rgb("#64748b")

#canvas(length: 1cm, {
  import draw: *

  // 1. Box Component (Inlet, Splitter, Mixer, Bypass Duct, Nozzle)
  let box-node(name, pos, w, h, label-content, stroke-style: cyan-stroke, fill-color: white, radius: 0) = {
    let (x, y) = pos
    group(name: name, {
      rect(
        (x - w/2, y - h/2), (x + w/2, y + h/2),
        stroke: stroke-style,
        fill: fill-color,
        radius: radius
      )
      content((x, y), align(center + horizon)[
        #set align(center)
        #label-content
      ])
      anchor("west",   (x - w/2, y))
      anchor("east",   (x + w/2, y))
      anchor("north",  (x, y + h/2))
      anchor("south",  (x, y - h/2))
      anchor("center", (x, y))
    })
  }

  // 2. Turbomachinery Trapezoid (Compressors & Turbines)
  let trap-node(name, pos, w, h-in, h-out, label-content) = {
    let (x, y) = pos
    let x-l = x - w/2
    let x-r = x + w/2
    let y-in-top  = y + h-in/2
    let y-in-bot  = y - h-in/2
    let y-out-top = y + h-out/2
    let y-out-bot = y - h-out/2
    let max-h = calc.max(h-in, h-out)

    group(name: name, {
      line(
        (x-l, y-in-bot),
        (x-l, y-in-top),
        (x-r, y-out-top),
        (x-r, y-out-bot),
        close: true,
        stroke: cyan-stroke,
        fill: white
      )
      content((x, y), align(center + horizon)[
        #set align(center)
        #label-content
      ])
      anchor("west",   (x-l, y))
      anchor("east",   (x-r, y))
      anchor("north",  (x, y + max-h/2))
      anchor("south",  (x, y - max-h/2))
      anchor("bottom", (x, y - max-h/2))
      anchor("center", (x, y))
    })
  }

  // 3. Station Badge (Aerospace Standard Black Badge with White Numeral)
  let station-badge(pos, num-str) = {
    content(pos, box(
      fill: black,
      radius: 2.2pt,
      inset: (x: 4.8pt, y: 2.8pt),
      align(center + horizon)[#text(fill: white, size: 7.5pt, weight: "bold")[#num-str]]
    ))
  }

  // Helper: Directed core flow line with intermediate station badge
  let connect-with-badge(from-node, to-node, badge-text) = {
    line(from-node + ".east", to-node + ".west",
         stroke: flow-stroke,
         mark: (end: "stealth", fill: dark-slate, size: 0.22))
    station-badge(((from-node + ".east"), 0.5, (to-node + ".west")), badge-text)
  }

  // ---------------------------------------------------------------------------
  // Geometric Layout Coordinates along Engine Centerline (y = 0)
  // ---------------------------------------------------------------------------
  let x-s0         = 0.0
  let x-inlet      = 1.90
  let x-fan        = 4.70
  let x-splitter   = 7.45
  let x-hpc        = 10.05
  let x-combustor  = 13.30
  let x-hpt        = 16.35
  let x-lpt        = 18.90
  let x-mixer      = 21.55
  let x-afterburn  = 24.75
  let x-nozzle     = 28.25
  let x-s9         = 30.40

  // Station 0: Ambient Freestream Streamtube
  circle((x-s0, 0), radius: 0.36, stroke: 1.3pt + dark-slate, fill: white, name: "s0")
  content("s0.center", text(size: 9.5pt, weight: "bold", fill: dark-slate)[0])

  // Core Flowpath Components
  box-node("inlet", (x-inlet, 0), 1.50, 1.25,
           text(weight: "medium")[Inlet])

  trap-node("fan", (x-fan, 0), 1.65, 2.40, 1.70,
            text(weight: "medium")[Fan\ (LPC)])

  box-node("splitter", (x-splitter, 0), 1.40, 1.25,
           text(weight: "medium")[Splitter])

  trap-node("hpc", (x-hpc, 0), 1.50, 1.90, 1.30,
            text(weight: "medium")[HPC])

  box-node("combustor", (x-combustor, 0), 2.55, 1.45,
           align(center + horizon)[#text(weight: "medium")[Combustor] \ #v(1pt) #text(size: 6.8pt, fill: text-muted)[Tt4: 3100 °R (MIL)]],
           radius: 0.25)

  trap-node("hpt", (x-hpt, 0), 1.20, 1.30, 1.80,
            text(weight: "medium")[HPT])

  trap-node("lpt", (x-lpt, 0), 1.40, 1.80, 2.40,
            text(weight: "medium")[LPT])

  box-node("mixer", (x-mixer, 0), 1.40, 1.25,
           text(weight: "medium")[Mixer])

  box-node("afterburn", (x-afterburn, 0), 2.75, 1.45,
           align(center + horizon)[#text(weight: "medium")[Afterburner] \ #v(1pt) #text(size: 6.5pt, fill: text-muted)[Tt7: 3800 °R (Max AB)]],
           radius: 0.25)

  box-node("nozzle", (x-nozzle, 0), 2.05, 1.45,
           align(center + horizon)[#text(weight: "medium")[Nozzle] \ #v(1pt) #text(size: 6.5pt, fill: text-muted)[Net Thrust (Fn)]])

  // Station 9: Exhaust Plume
  circle((x-s9, 0), radius: 0.36, stroke: 1.3pt + dark-slate, fill: white, name: "s9")
  content("s9.center", text(size: 9.5pt, weight: "bold", fill: dark-slate)[9])

  // ---------------------------------------------------------------------------
  // Core Gas Path Interconnections & SAE AS755 Station Numbering
  // ---------------------------------------------------------------------------
  connect-with-badge("s0", "inlet", "1")               // Station 1: Cowl Inlet Lip
  connect-with-badge("inlet", "fan", "2")              // Station 2: Fan Face
  connect-with-badge("fan", "splitter", "2.1")         // Station 2.1: Fan Exit
  connect-with-badge("splitter", "hpc", "2.5")         // Station 2.5: HPC Inlet
  connect-with-badge("hpc", "combustor", "3")          // Station 3: HPC Exit / Burner Inlet
  connect-with-badge("combustor", "hpt", "4")          // Station 4: Combustor Exit / HPT Inlet (MIL Tt4)
  connect-with-badge("hpt", "lpt", "4.5")              // Station 4.5: HPT Exit / LPT Inlet
  connect-with-badge("lpt", "mixer", "5")              // Station 5: LPT Exit / Core Discharge
  connect-with-badge("mixer", "afterburn", "6")        // Station 6: Mixer Exit / Afterburner Inlet
  connect-with-badge("afterburn", "nozzle", "7")       // Station 7: Afterburner Exit / Nozzle Inlet (Max AB Tt7)
  line("nozzle.east", "s9.west", stroke: flow-stroke, mark: (end: "stealth", fill: dark-slate, size: 0.22))

  // ---------------------------------------------------------------------------
  // Bypass Stream: Splitter -> Bypass Duct -> Mixer
  // ---------------------------------------------------------------------------
  let x-byp = (x-splitter + x-mixer) / 2
  let y-byp = 2.80
  box-node("bypass", (x-byp, y-byp), 2.45, 0.95,
           text(weight: "medium", fill: dark-slate)[Bypass Duct],
           stroke-style: 1.6pt + bypass-blue)

  let wp-byp-l = (x-splitter, 1.70)
  let wp-byp-r = (x-mixer, 1.70)

  // Splitter up to waypoint 13, then to bypass duct
  line("splitter.north", wp-byp-l, stroke: 1.4pt + bypass-blue)
  station-badge((x-splitter, 1.15), "13")              // Station 13: Fan Bypass Duct Inlet
  line(wp-byp-l, "bypass.west", stroke: 1.4pt + bypass-blue, mark: (end: "stealth", fill: bypass-blue, size: 0.22))

  // Bypass duct to waypoint 16, then down into mixer
  line("bypass.east", wp-byp-r, stroke: 1.4pt + bypass-blue)
  line(wp-byp-r, "mixer.north", stroke: 1.4pt + bypass-blue, mark: (end: "stealth", fill: bypass-blue, size: 0.22))
  station-badge((x-mixer, 1.15), "16")                 // Station 16: Bypass Duct Exit into Mixer

  // ---------------------------------------------------------------------------
  // Bleed 3: HPC Customer / Turbine Cooling Bleed Tap
  // ---------------------------------------------------------------------------
  let y-bleed-cross = 2.14
  let y-bleed-top = 3.70
  // Segment below crossing
  line("hpc.north", (x-hpc, y-bleed-cross - 0.16),
       stroke: (paint: bleed-gray, thickness: 1.35pt, dash: "dashed"))
  // Segment above crossing with terminal arrow
  line((x-hpc, y-bleed-cross + 0.16), (x-hpc, y-bleed-top),
       stroke: (paint: bleed-gray, thickness: 1.35pt, dash: "dashed"),
       mark: (end: "stealth", fill: bleed-gray, size: 0.22))
  content((x-hpc, y-bleed-top + 0.35), text(size: 8.5pt, fill: bleed-gray, weight: "bold")[Bleed 3])

  // ---------------------------------------------------------------------------
  // Mechanical Shaft Couplings (Spools)
  // ---------------------------------------------------------------------------
  let hp-y = -1.80
  let lp-y = -2.60

  // HP Spool: HP Shaft (14,000 rpm) connecting HPC to HPT
  line("hpc.bottom", (x-hpc, hp-y), (x-hpt, hp-y), "hpt.bottom",
       stroke: (paint: amber-shaft, thickness: 1.4pt, dash: "dashed"))
  let hp-mid-x = (x-hpc + x-hpt) / 2
  content((hp-mid-x, hp-y),
          box(fill: white, inset: (x: 5.5pt, y: 1.5pt), radius: 2pt)[
            #text(size: 8pt, weight: "bold", fill: amber-shaft)[HP Shaft (14,000 rpm)]
          ])

  // LP Spool: LP Shaft (10,000 rpm) connecting Fan to LPT
  line("fan.bottom", (x-fan, lp-y), (x-lpt, lp-y), "lpt.bottom",
       stroke: (paint: amber-shaft, thickness: 1.4pt, dash: "dashed"))
  let lp-mid-x = (x-fan + x-lpt) / 2
  content((lp-mid-x, lp-y),
          box(fill: white, inset: (x: 5.5pt, y: 1.5pt), radius: 2pt)[
            #text(size: 8pt, weight: "bold", fill: amber-shaft)[LP Shaft (10,000 rpm)]
          ])
})
