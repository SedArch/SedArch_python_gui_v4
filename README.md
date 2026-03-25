# SedArch Python GUI

> **A full-featured desktop application for sedimentary & stratigraphic forward modelling**

SedArch is a physics-based forward model that simulates sediment transport, carbonate growth, sea-level change, tectonic subsidence, wave energy, and fluvial processes on a 2-D grid over geological time. This repository bundles the Python engine together with a **PySide6 GUI** that lets you build, run, visualise, and compare simulations without touching the command line.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Workflow](#workflow)
  - [Input Editor](#️-input-editor-tab)
  - [Run](#-run-tab)
  - [Visualize](#-visualize-tab)
  - [Compare](#-compare-tab)
- [VVM File Format](#vvm-file-format)
- [Bundled Example Scenarios](#bundled-example-scenarios)
- [Engine Architecture](#engine-architecture)
- [CLI Usage](#cli-usage)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [License](#license)

---

## Features

| Category | Details |
|---|---|
| **GUI framework** | PySide6 (Qt 6), dark-mode theme |
| **Input editing** | Form-based VVM editor with interactive curve editors |
| **Simulation** | Background thread; live topography preview every step |
| **Visualisation** | 9 plot types: maps, cross-sections, time-series, strat columns, net-change maps |
| **Comparison** | Side-by-side two-run comparison with difference map |
| **Output** | VVM result files + PNG export at 200 dpi |
| **Processes modelled** | Waves · Dispersion · Channels · Gravity flow · Carbonate growth · Tectonics |
| **Sediment types** | Up to 4 grain-size classes per simulation |

---

## Screenshots

> _Add screenshots here after first run — place images in `docs/images/`._

| Input Editor | Run tab (live preview) | Visualizer |
|---|---|---|
| _(screenshot)_ | _(screenshot)_ | _(screenshot)_ |

---

## Requirements

| Package | Minimum version |
|---|---|
| Python | 3.9 |
| PySide6 | 6.4 |
| NumPy | 1.23 |
| Matplotlib | 3.6 |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/sedarch_python_gui_v4.git
cd sedarch_python_gui_v4

# 2. (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install PySide6 matplotlib numpy
```

> **Windows Store Python note:** If you see a `DLL load failed while importing QtCore` error,
> install Python from [python.org](https://www.python.org/downloads/) instead of the Microsoft Store.

---

## Quick Start

```bash
# Open the GUI with an empty editor
python sedarch_gui.py

# Open the GUI and pre-load an existing VVM input file
python sedarch_gui.py Input/carboclastics.vvm
```

On first launch, go to **Tools → Settings** and confirm the *SedArch Path* points to the
project root (the folder that contains the `sedarch/` package). This is auto-detected but can
be changed at any time.

---

## Project Structure

```
sedarch_python_gui_v4/
│
├── sedarch_gui.py          # Main GUI application (entry point)
│
├── sedarch/                # Physics engine (Python package)
│   ├── __init__.py         # Version & licence metadata
│   ├── __main__.py         # run() function + CLI entry point
│   ├── geology.py          # Vars class + all geologic processes
│   ├── vvm.py              # VVM file parser & writer
│   ├── sequence.py         # SedVector / Sequence sediment-column types
│   ├── basin.py            # Sub-basin analysis for channel routing
│   └── paths.py            # Flow-path geometry utilities
│
├── Input/                  # Example simulation input files
│   ├── *.vvm               # Top-level scenario files (28 examples)
│   ├── maps/               # Initial topography & tectonics grids (27 files)
│   └── curves/             # Sea-level, growth, dispersion curves (13 files)
│
├── Output/                 # Simulation output files (written here at runtime)
│
└── docs/                   # Extended documentation
    ├── VVM_FORMAT.md       # VVM file format reference
    └── ENGINE.md           # Engine architecture & process descriptions
```

---

## Workflow

### ✏ Input Editor tab

Build or edit a simulation input file visually.

| Section | Editable parameters |
|---|---|
| **General** | Title · Step count · Step duration (ka) · Initial time (ka) |
| **Grid** | Cell side length (m) · Topography source (file or constant elevation) |
| **Sediments** | Up to 4 grain diameters (mm) and base fractions |
| **Sea Level** | Constant value **or** interactive TIME_SEALEVEL_CURVE |
| **Dispersion** | DISP_FACTOR and interactive LEVEL_DISP_CURVE |
| **Growth** | GROWTH_FACTOR for carbonates |
| **File Paths** | Full absolute path to the output VVM file |
| **Raw VVM** | Free-text editor for any advanced/unlisted parameter |

**Curve editors** — click any *Edit … Curve …* button to open a table + live chart dialog.
Add, remove, and edit rows; the preview updates as you type. You can also load a `.vvm`
curve file directly from disk.

**Apply button** — press *Apply Changes to VVM* to rebuild the Raw VVM text from all form
fields above, giving you a single canonical source of truth before saving or running.

---

### ▶ Run tab

Execute the simulation and watch it progress in real time.

1. Browse for your `.vvm` input file (or it is filled automatically after saving from the Editor).
2. Click **▶ Run** — the engine starts in a background thread so the UI stays responsive.
3. The **progress bar** and **elapsed timer** update every step.
4. The **live topography preview** (right panel) refreshes after every step — shoreline contour shown in white.
5. All simulation output is captured in the **Log** panel.
6. On completion a dialog offers to load the output directly into the Visualizer.
7. **⬛ Stop** cancels after the current step finishes cleanly.

---

### 📊 Visualize tab

Load any output `.vvm` file and explore the full time sequence interactively.

| Plot type | Description |
|---|---|
| **Topography Map** | 2-D colour map + shoreline contour; scrub with time slider |
| **Sediment Maps** | 4-panel surface fraction for each grain-size class |
| **E–W Cross-Section** | Centreline elevation profiles, multiple timesteps overlaid |
| **N–S Cross-Section** | Same, perpendicular direction |
| **Sea Level & Shoreline** | Dual-axis time-series: sea level (m) and shoreline position (km) |
| **Grain-Size Timeseries** | Surface sediment fractions at grid centre through time |
| **Strat Column** | Marine vs. terrestrial exposure history at grid centre |
| **Net Change Map** | Final − initial topography (red/blue diverging scale) |
| **Overview** | Six-panel summary dashboard |

Controls: time slider · colormap selector · shoreline / grid toggles · **Export PNG** (200 dpi) · Matplotlib navigation toolbar (zoom, pan, save).

---

### ⚖ Compare tab

Load two output VVM files (Run A and Run B) and compare them side by side.

| Plot type | Description |
|---|---|
| **Topography Maps** | Side-by-side colour maps at the same timestep |
| **Cross-sections** | Both runs' centreline profiles overlaid |
| **Sea Level & Shoreline** | Combined time-series on one chart |
| **Grain-size** | Two-panel grain-size timeseries |
| **Difference Map** | A − B elevation + distribution histogram |

A single **synchronised timestep slider** steps both runs together.

---

## VVM File Format

VVM (_Vars/Values/Matrix_) is the plain-text format used for both input and output.

```
TITLE = "My simulation"
OUTFILE = "C:/path/to/Output/result_out.vvm"

CELLSIDE = 500           ! cell side in metres
SED_DIAMETERS = 20 5 1   ! grain diameters in mm (coarse → fine)

INCLUDE = "maps/top_slope_4p_60x40.vvm"   ! include initial topography

STEP_DURATION = 20       ! ka per step
STEP_COUNT    = 50       ! number of steps

SEALEVEL = 0             ! constant sea level, or use TIME_SEALEVEL_CURVE
DISP_FACTOR = 0.05
```

Key rules:
- `!` starts an inline comment.
- `INCLUDE = "path"` inserts another VVM file; path is relative to the **including file's directory**.
- `OUTFILE` must be an **absolute path** (the GUI fills this in automatically).
- Multi-row data blocks (e.g. topography grids) are space-separated values, one row per line.

See [`docs/VVM_FORMAT.md`](docs/VVM_FORMAT.md) for the complete reference.

---

## Bundled Example Scenarios

All examples live in `Input/`. Run any of them via the GUI or CLI.

| File | Processes active | Grid | Steps |
|---|---|---|---|
| `agg_small.vvm` | Dispersion | 3 × 4 | 10 |
| `aggradation.vvm` | Dispersion | 9 × 9 | 20 |
| `simple.vvm` | Dispersion | 60 × 40 | 10 |
| `fluvial.vvm` | Channels · Dispersion | 60 × 40 | 30 |
| `fluvial_long.vvm` | Channels · Dispersion | 60 × 40 | 200 |
| `fluvial_multi.vvm` | Channels · Dispersion | 160 × 100 | 50 |
| `fluvial_volve_2/3/4.vvm` | Channels · Dispersion (chained) | 60 × 40 | 30 each |
| `delta.vvm` | Channels · Dispersion · Waves | 60 × 40 | 50 |
| `waves.vvm` | Waves · Dispersion | 60 × 40 | 30 |
| `turbidites.vvm` | Gravity flow · Dispersion | 60 × 40 | 50 |
| `turb_fan.vvm` | Gravity flow · Dispersion | 60 × 40 | 50 |
| `turb_fan_long.vvm` | Gravity flow · Dispersion | 60 × 40 | 200 |
| `carbonates.vvm` | Growth · Dispersion · Sea level | 60 × 40 | 75 |
| `carboclastics.vvm` | Growth · Channels · Sea level | 60 × 40 | 75 |
| `atoll.vvm` | Growth (energy + depth curves) | 60 × 40 | 50 |
| `carb_reef.vvm` | Growth (energy + depth curves) | 60 × 40 | 50 |
| `tectonics.vvm` | Dispersion · Tectonics · Sea level | 60 × 40 | 75 |
| `basins.vvm` | Channels · Dispersion | 60 × 40 | 30 |
| `dispersion.vvm` | Dispersion · Sea level | 60 × 40 | 75 |
| `stage_1.vvm` | Channels · Dispersion (stage 1 of 2) | 60 × 40 | 50 |
| `stage_2.vvm` | Channels · Dispersion (stage 2 of 2) | 60 × 40 | 50 |
| `idle.vvm` | Sea level only (no transport) | 1 × 1 | 100 |
| `single_cell.vvm` | Single cell test | 1 × 1 | 5 |

---

## Engine Architecture

The `sedarch/` package is a pure-Python port of the original C++ SedArch engine.

```
sedarch/
├── __main__.py   ← orchestrates the time loop; calls all process modules
├── geology.py    ← Vars (parameter container) + all process functions
├── vvm.py        ← VVM parser (read) and writer (output per step)
├── sequence.py   ← SedVector / Sequence: sediment column data structures
├── basin.py      ← sub-basin identification for channel routing
└── paths.py      ← 2-D flow-path geometry (complex-number coordinates)
```

### Time-step loop (per step in `__main__.py`)

```
1. WAVES          — compute wave energy field; transport sediment shoreward
2. DISPERSION     — slope-driven diffusion of sediment
3. CHANNELS       — fluvial routing via sub-basin overflow chain
4. SFLOW          — gravity-driven sediment gravity flow (turbidites)
5. GROWTH         — carbonate / organic growth as function of depth & energy
6. TECTONICS      — vertical tectonic movement (subsidence / uplift)
7. Write output   — append current state to OUTFILE
8. step_callback  — GUI hook: update progress bar, live preview, check cancel
```

See [`docs/ENGINE.md`](docs/ENGINE.md) for a detailed description of each process.

---

## CLI Usage

You can run simulations without the GUI:

```bash
# Run a single VVM input file
python -m sedarch Input/carboclastics.vvm

# Run multiple files in sequence
python -m sedarch Input/stage_1.vvm Input/stage_2.vvm
```

Output is written to the path specified by `OUTFILE` in each VVM file.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New input file |
| `Ctrl+O` | Open VVM file |
| `Ctrl+S` | Save current file |
| `F5` | Start simulation |

---

## License

This project is licensed under the **GNU General Public License v3.0**.
See [`LICENSE`](LICENSE) for the full text.

---

_Built with [PySide6](https://doc.qt.io/qtforpython/), [Matplotlib](https://matplotlib.org/), and [NumPy](https://numpy.org/)._
