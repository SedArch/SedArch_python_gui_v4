# SedArch Engine — Architecture & Process Reference

This document describes the internal architecture of the `sedarch/` Python package: how the
time-step loop is organised, what each geologic process module does, and how the data
structures represent the sedimentary system.

---

## Table of Contents

- [Package Overview](#package-overview)
- [Entry Point — `__main__.py`](#entry-point----__main__py)
- [Time-Step Loop](#time-step-loop)
- [Data Structures](#data-structures)
  - [Vars — simulation parameter container](#vars----simulation-parameter-container)
  - [Sequence — sediment column storage](#sequence----sediment-column-storage)
  - [SedVector — single column](#sedvector----single-column)
- [Process Modules](#process-modules)
  - [Waves](#waves)
  - [Dispersion](#dispersion)
  - [Channels (Fluvial)](#channels-fluvial)
  - [Gravity Flow (SFLOW)](#gravity-flow-sflow)
  - [Carbonate Growth](#carbonate-growth)
  - [Tectonics](#tectonics)
- [I/O — VVM Parser & Writer](#io----vvm-parser--writer)
- [Flow-Path Geometry — `paths.py`](#flow-path-geometry----pathspy)
- [Sub-Basin Analysis — `basin.py`](#sub-basin-analysis----basinpy)
- [step_callback — GUI Integration](#step_callback----gui-integration)
- [Module Dependency Graph](#module-dependency-graph)

---

## Package Overview

```
sedarch/
├── __init__.py     version metadata, GPL v3 licence declaration
├── __main__.py     CLI entry point; run() function; time-step loop
├── geology.py      Vars class + every geologic process function
├── vvm.py          VVM file parser (read) and writer (output per step)
├── sequence.py     SedVector / Sequence — sediment column data structures
├── basin.py        sub-basin identification for channel overflow routing
└── paths.py        2-D flow-path geometry (complex-number grid coords)
```

The engine is a pure-Python port of the original C++ SedArch codebase. All heavy
array operations use **NumPy**; no compiled extensions are required.

---

## Entry Point — `__main__.py`

```python
from sedarch.__main__ import run

run(
    input_file="Input/carboclastics.vvm",
    step_callback=None   # optional GUI hook
)
```

Or from the command line:

```bash
python -m sedarch Input/carboclastics.vvm
```

`run()` performs the following top-level sequence:

1. Parse input VVM → populate `Vars` and `Sequence` objects via `geology.read_input()`.
2. Determine which process modules are active (non-zero factors / non-empty sources).
3. Apply any initial tectonics snapshot.
4. Create/clear the output VVM file and write the initial state.
5. Execute the **main time loop** (see below).
6. Print timing statistics to stdout.

---

## Time-Step Loop

For each of `STEP_COUNT` timesteps:

```
┌─────────────────────────────────────────────────────┐
│  1. WAVES         wave energy field + shoreface transport  │
│  2. DISPERSION    slope diffusion                          │
│  3. CHANNELS      fluvial routing via basin overflow chain │
│  4. SFLOW         gravity-driven sediment flows            │
│  5. GROWTH        carbonate / organic production           │
│  6. TECTONICS     vertical tectonic movement               │
│  7. Write output  append state to OUTFILE (VVM)            │
│  8. step_callback GUI: update progress, check cancel       │
└─────────────────────────────────────────────────────┘
```

Each process is **only called if its controlling factor is non-zero** (lazy activation).
The order is fixed: wave-driven transport precedes slope-diffusion, which precedes
fluvial routing, etc.

---

## Data Structures

### Vars — simulation parameter container

`geology.Vars` is a plain Python object whose attributes hold **all** model parameters.
It is populated by `read_input()` from the VVM file and then passed to every process
function by reference.

Key attribute groups:

| Group | Attributes |
|---|---|
| **Grid** | `nx`, `ny`, `cellside`, `xorigin`, `yorigin`, `rotation` |
| **Topography** | `top` — shape `(nx, ny)` float32 array, elevation in metres |
| **Sediments** | `sed_diameters`, `sed_base_fracs` — vectors of length `nsed` |
| **Time** | `time`, `timeprev`, `step_duration`, `step_count` |
| **Sea level** | `sealevel` (scalar) or `time_sealevel_curve` (2-col array) |
| **Dispersion** | `disp_factor`, `level_disp_curve`, `disp_map` |
| **Waves** | `wave_factor`, `wave_sources`, `time_wave_curve` |
| **Channels** | `channel_factor`, `channel_sources`, `channel_event_period` |
| **Gravity flow** | `sflow_factor`, `sflow_source_map`, `sflow_depth_map` |
| **Growth** | `growth_factor`, `level_growth_curve`, `erg_growth_curve` |
| **Tectonics** | `tect_factor`, `tect_map`, `time_tect_curve` |

---

### Sequence — sediment column storage

`sequence.Sequence` stores the stratigraphic record for the **entire grid** as a list of
`SedVector` objects, one per grid node (flattened to a 1-D list of length `nx × ny`).

Helper functions operate on a Sequence as a whole:

| Function | Description |
|---|---|
| `new_top_seq(seq, nx, ny)` | Prepend a new active layer to every column |
| `remove_top_seq(seq, nx, ny)` | Remove the top layer from every column |
| `merge_top(seq, nx, ny)` | Merge the top two layers |
| `trim_all_tops(seq, nx, ny)` | Remove layers thinner than a threshold |
| `write_sequence(seq, path)` | Serialise stratigraphic record to file |

---

### SedVector — single column

`sequence.SedVector` represents the sediment stack at **one grid node**.

Internally it stores a 2-D NumPy array `thick_` of shape `(nlayers, nsed)`:

- Axis 0 → layers (index 0 = basement / oldest, topmost index = active layer)
- Axis 1 → sediment types (matches `SED_DIAMETERS` order)

Key methods:

| Method | Returns | Description |
|---|---|---|
| `n_layers()` | int | Total number of layers including basement |
| `sed_top()` | array (nsed,) | Sediment fractions in the active (top) layer |
| `sed_at(i)` | array (nsed,) | Fractions in layer i |
| `thick_top()` | float | Thickness of the active layer (m) |
| `thick_at(i)` | float | Thickness of layer i (m) |

---

## Process Modules

All process functions live in `geology.py`. They receive `v` (`Vars`) and `seq`
(`Sequence`) and modify them in place.

---

### Waves

**Function:** `wave(v)` + `move_sed_waves(v, seq)`

Simulates wave energy propagation from open-water boundary sources toward shore. Wave
energy decays with water depth following a configurable attenuation curve. The energy
field drives shoreface sediment transport:

- Sediment is moved **up-energy-gradient** (onshore) in proportion to `WAVE_FACTOR`.
- Grain mobility is controlled by `WAVE_SED_FACTOR` per grain type (coarser grains
  are less mobile).
- Energy and transport can be modulated through time by `TIME_WAVE_CURVE`.

---

### Dispersion

**Function:** `move_sed_disp(v, seq)`

Slope-driven diffusive transport — the simplest and most universal process. At each
node, sediment moves down the local topographic gradient at a rate proportional to:

```
flux = DISP_FACTOR × depth_multiplier(z) × time_multiplier(t) × slope
```

where `LEVEL_DISP_CURVE` provides the depth multiplier and `DISP_MAP` provides a
spatial multiplier. The diffusion is explicit (Forward Euler), so very large
`DISP_FACTOR` values or very steep slopes may require reducing `STEP_DURATION`.

---

### Channels (Fluvial)

**Functions:** `channels(v, seq)` (calls `basin.SubBasins`)

Implements a simplified fluvial routing scheme based on **sub-basin overflow**:

1. The grid is partitioned into sub-basins drained by local topographic lows.
2. Each sub-basin fills with sediment from `CHANNEL_SOURCES` boundary nodes until it
   overflows to the next downstream basin.
3. The overflow cascade continues to the open boundary.
4. Channel avulsion / switching is triggered at intervals of
   `CHANNEL_EVENT_PERIOD`, lasting `CHANNEL_EVENT_DURATION` ka.

This produces deltaic switching and distributary-fan patterns characteristic of
fluvial-dominated margins.

---

### Gravity Flow (SFLOW)

**Function:** `sflow(v, seq)`

Simulates sediment gravity flows (turbidity currents, debris flows) triggered when
slope angles exceed a threshold or when `SFLOW_SOURCE_MAP` activates flow at
prescribed locations. Material flows downslope following steepest-descent paths
computed by `paths.py`. Flow intensity is scaled by `SFLOW_FACTOR` and modulated by
`TIME_SFLOW_CURVE`.

---

### Carbonate Growth

**Function:** `growth(v, seq)`

Adds carbonate (or organically produced) sediment to the active layer at each node.
The growth rate at a node is:

```
rate = GROWTH_FACTOR
     × depth_multiplier(water_depth)   ! from LEVEL_GROWTH_CURVE
     × energy_multiplier(wave_energy)  ! from ERG_GROWTH_CURVE
     × time_multiplier(t)              ! from TIME_GROWTH_CURVE
     × spatial_multiplier(x,y)         ! from GROWTH_MAP
```

Newly produced carbonate is added exclusively to the sediment type specified by
`GROWTH_SED_ID`. This enables mixed carbonate–clastic stratigraphy when combined with
clastic processes.

---

### Tectonics

**Function:** `vertical_tectonics(v)`

Applies simple vertical movement (subsidence positive, uplift negative) uniformly or
spatially across the grid:

```
Δelevation = TECT_FACTOR × TECT_MAP(x,y) × TIME_TECT_CURVE(t) × STEP_DURATION
```

Tectonics is applied **after all transport processes** in each timestep, ensuring that
transport responds to the topography _before_ tectonic modification.

---

## I/O — VVM Parser & Writer

### Reading

`vvm.parse_file(path) → dict`

Parses a VVM file recursively (following `INCLUDE` directives) and returns a dictionary
mapping keyword strings to Python values (scalars, strings, NumPy arrays).

The parser handles:
- Inline `!` comments (respecting quoted strings)
- Scalar and vector values on one line
- 2-D grid blocks (multi-line, blank-line terminated)
- 3-D volume blocks (double blank-line terminated)
- Nested `INCLUDE` with paths relative to the including file

### Writing

The engine writes output in append mode, calling these functions each step:

| Function | Description |
|---|---|
| `clear_file(path)` | Initialise (or overwrite) the output file |
| `write_initial_state(v, seq)` | Write timestep 0 (initial conditions) |
| `write_step(v, seq, ...)` | Append the current timestep state |
| `write_value(stream, keyword, value)` | Low-level: write one keyword block |

Output VVM files grow by one state block per step and can be large for high-resolution
long-duration runs (hundreds of MB is common for 160 × 100 × 200-step models).

---

## Flow-Path Geometry — `paths.py`

`paths.py` provides utilities for 2-D flow routing on the grid. Grid positions are
encoded as **Python `complex` numbers** (`Dot` type):

```
real(dot) → column index (x)
imag(dot) → row index (y)
```

This allows concise vector arithmetic. Key functions:

| Function | Description |
|---|---|
| `vec_pro(a, b)` | 2-D cross product |
| `unit_vec(v)` | Normalise to unit length |
| `rotate(v, angle)` | Rotate vector by angle (radians) |
| `proj_pt(p, a, b)` | Project point onto segment AB |
| `dist_pt_seg(p, a, b)` | Distance from point to segment |

Used by `basin.py` and the channels / gravity-flow modules to trace downslope paths.

---

## Sub-Basin Analysis — `basin.py`

`basin.SubBasins` partitions the grid into drainage basins:

1. Each grid node is assigned to a sub-basin by following the steepest-descent path
   to a local minimum.
2. Sill nodes (lowest points on each basin boundary) are identified.
3. Sediment from channel sources fills the sub-basin to the sill elevation, then
   overflows to the next downstream basin.

The `Bas` dataclass stores per-basin metadata:

| Field | Description |
|---|---|
| `isill` | Index of the sill (outflow) node |
| `zsill` | Elevation of the sill |
| `sill_on_boundary` | True if the sill is a grid boundary node |
| `idfm` | Index of the downstream (receiving) basin |

---

## step_callback — GUI Integration

`run()` accepts an optional `step_callback` function used by the GUI to track progress
and handle cancellation:

```python
def step_callback(
    step: int,        # current step number (1-based)
    total: int,       # total number of steps
    time: float,      # current model time (ka)
    top: np.ndarray,  # copy of current topography (nx × ny)
    sealevel: float,  # current sea level (m)
    seq: Sequence     # current sediment sequence
) -> bool:            # return True to CANCEL the run
    ...
```

The GUI's `SimulationWorker` provides this callback; it:
- Emits a Qt signal to update the progress bar.
- Emits a signal with `top` and `sealevel` to refresh the live topography preview.
- Checks a shared `QMutex`-protected cancel flag and returns `True` if the user
  pressed Stop.

When running via the CLI (`python -m sedarch`), no callback is passed and `step_callback=None`.

---

## Module Dependency Graph

```
__main__.py
    ├── geology.py
    │     ├── vvm.py
    │     └── sequence.py
    │           └── (numpy)
    ├── sequence.py
    ├── basin.py
    │     ├── paths.py
    │     └── sequence.py
    └── vvm.py
```

There are **no circular imports**. `paths.py` and `sequence.py` are leaf modules with
no intra-package dependencies beyond NumPy.
