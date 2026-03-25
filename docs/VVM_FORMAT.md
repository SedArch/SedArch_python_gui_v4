# VVM File Format Reference

VVM (_Vars / Values / Matrix_) is the plain-text file format used by SedArch for both
**input** (simulation parameters) and **output** (per-step results).

---

## Table of Contents

- [Overview](#overview)
- [Syntax Rules](#syntax-rules)
- [Data Types](#data-types)
- [INCLUDE Directive](#include-directive)
- [OUTFILE Keyword](#outfile-keyword)
- [Input Keywords Reference](#input-keywords-reference)
  - [Global / Metadata](#global--metadata)
  - [Grid](#grid)
  - [Time Control](#time-control)
  - [Sediments](#sediments)
  - [Sea Level](#sea-level)
  - [Dispersion](#dispersion)
  - [Waves](#waves)
  - [Channels (Fluvial)](#channels-fluvial)
  - [Gravity Flow (SFLOW)](#gravity-flow-sflow)
  - [Carbonate Growth](#carbonate-growth)
  - [Tectonics](#tectonics)
- [Output File Structure](#output-file-structure)
- [Curve Files](#curve-files)
- [Map Files](#map-files)
- [Minimal Example](#minimal-example)
- [Full Example (carboclastics)](#full-example-carboclastics)

---

## Overview

A VVM file is a UTF-8 text file. Each **keyword block** associates a name with one or more
values:

```
KEYWORD = <value(s)>
```

Blocks are separated by blank lines. The parser is case-insensitive for keywords.

---

## Syntax Rules

| Rule | Detail |
|---|---|
| **Comments** | `!` to end-of-line. Everything after `!` is ignored. |
| **Quoting** | String values (file paths, titles) must be enclosed in `"double quotes"`. |
| **Case** | Keywords are case-insensitive (`OUTFILE` = `outfile`). |
| **Continuation** | Multi-row data (grids) continues until a blank line. |
| **Blank lines** | Separate data blocks; extra blank lines are ignored. |

```
TITLE   = "My model"         ! quoted string
CELLSIDE = 500               ! scalar integer or float
SED_DIAMETERS = 20 5 1       ! space-separated vector on one line
```

---

## Data Types

| Type | Description | Example |
|---|---|---|
| **Scalar** | Single number | `SEALEVEL = -50` |
| **String** | Quoted text | `TITLE = "Stage 2"` |
| **Vector** | Space-separated numbers on one line | `SED_DIAMETERS = 20 10 5 1` |
| **2-D grid** | One row per line; blank line terminates | See [Map Files](#map-files) |
| **Curve** | 2-column matrix (x, y), one pair per line | See [Curve Files](#curve-files) |

---

## INCLUDE Directive

```
INCLUDE = "relative/or/absolute/path.vvm"
```

- Recursively inserts the contents of another VVM file at that point.
- **Relative paths** are resolved relative to the **directory of the file that contains the INCLUDE**, not the working directory.
- Used for topography grids, curve data, and chained simulation stages.

```
INCLUDE = "maps/top_slope_4p_60x40.vvm"     ! topography
INCLUDE = "curves/sealevel_cycles_rise_15ma.vvm"  ! sea-level curve
```

---

## OUTFILE Keyword

```
OUTFILE = "C:/absolute/path/to/Output/result_out.vvm"
```

- **Must be an absolute path.** The GUI fills this in automatically.
- The engine creates the file on start-up and appends one block per timestep.
- The directory must already exist.

---

## Input Keywords Reference

### Global / Metadata

| Keyword | Type | Default | Description |
|---|---|---|---|
| `TITLE` | string | `""` | Human-readable label stored in the output file |
| `OUTFILE` | string | _(required)_ | Absolute path for the output VVM file |

---

### Grid

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `CELLSIDE` | scalar | m | Side length of each square grid cell |
| `NX` | scalar | — | Number of columns (inferred from TOP if not given) |
| `NY` | scalar | — | Number of rows (inferred from TOP if not given) |
| `TOP` | 2-D grid | m | Initial sea-floor / land-surface elevation (positive = above SL) |
| `XORIGIN` | scalar | m | X coordinate of the grid origin (default 0) |
| `YORIGIN` | scalar | m | Y coordinate of the grid origin (default 0) |
| `ROTATION` | scalar | degrees | Grid rotation angle (default 0) |

The `TOP` block (or an INCLUDE pointing to a map file) must be provided.

---

### Time Control

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `STEP_COUNT` | int | — | Number of timesteps to run |
| `STEP_DURATION` | scalar | ka | Duration of each timestep in kiloyears |
| `INITIAL_TIME` | scalar | ka | Model start time (default 0) |

---

### Sediments

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `SED_DIAMETERS` | vector | mm | Grain diameters, one per sediment type (max 4) |
| `SED1` … `SED4` | scalar | fraction | Initial base fraction of each sediment type (sum should be 1) |

Finer grains are more mobile (higher transportability). Coarser grains dominate lag deposits.

---

### Sea Level

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `SEALEVEL` | scalar | m | Constant sea level (used if no curve is given) |
| `TIME_SEALEVEL_CURVE` | 2-col curve | ka, m | Sea-level through time; column 1 = time, column 2 = elevation |

```
TIME_SEALEVEL_CURVE =
  0      0
  50   -20
  100   10
  150  -30
```

Usually provided via `INCLUDE = "curves/sealevel_xxx.vvm"`.

---

### Dispersion

Slope-driven diffusive sediment transport (simulates bioturbation, creep, storm reworking).

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `DISP_FACTOR` | scalar | m²/ka | Base diffusivity |
| `LEVEL_DISP_CURVE` | 2-col curve | m, factor | Multiplier on DISP_FACTOR as a function of water depth |
| `TIME_DISP_CURVE` | 2-col curve | ka, factor | Multiplier as a function of time |
| `DISP_MAP` | 2-D grid | factor | Spatial multiplier on DISP_FACTOR |

---

### Waves

Wave-driven sediment transport in the shoreface.

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `WAVE_FACTOR` | scalar | — | Base wave energy / transport intensity |
| `WAVE_SOURCES` | vector | — | Boundary indices from which wave energy propagates |
| `TIME_WAVE_CURVE` | 2-col curve | ka, factor | Wave intensity multiplier through time |
| `WAVE_SED_FACTOR` | vector | — | Per-grain-type wave mobility factor |

---

### Channels (Fluvial)

Sub-basin overflow routing simulating river channels and delta switching.

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `CHANNEL_FACTOR` | scalar | — | Overall channel transport intensity |
| `CHANNEL_REWORK_FACTOR` | scalar | — | Secondary reworking fraction |
| `CHANNEL_EVENT_PERIOD` | scalar | ka | Avulsion / switching period |
| `CHANNEL_EVENT_DURATION` | scalar | ka | Duration of each channel event |
| `CHANNEL_SOURCES` | vector | — | Grid-boundary source nodes for sediment input |
| `TIME_CHANNEL_CURVE` | 2-col curve | ka, factor | Channel intensity multiplier through time |

---

### Gravity Flow (SFLOW)

Sediment gravity flows (turbidity currents, debris flows) down-slope.

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `SFLOW_FACTOR` | scalar | — | Overall flow intensity |
| `SFLOW_SED_FACTOR` | vector | — | Per-grain-type mobility in gravity flows |
| `TIME_SFLOW_CURVE` | 2-col curve | ka, factor | Flow intensity through time |
| `SFLOW_SOURCE_MAP` | 2-D grid | — | Spatial map of source areas |
| `SFLOW_DEPTH_MAP` | 2-D grid | m | Trigger depth map |

---

### Carbonate Growth

Biologically-controlled carbonate (or organic) sediment production.

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `GROWTH_FACTOR` | scalar | m/ka | Base growth rate |
| `GROWTH_SED_ID` | int | — | Which sediment type receives the growth (1-based) |
| `LEVEL_GROWTH_CURVE` | 2-col curve | m, factor | Growth multiplier as a function of water depth |
| `CARB_LEVEL_GROWTH` | 2-col curve | m, factor | Alias for LEVEL_GROWTH_CURVE |
| `ERG_GROWTH_CURVE` | 2-col curve | energy, factor | Growth multiplier as a function of wave energy |
| `CARB_ERG_GROWTH` | 2-col curve | energy, factor | Alias for ERG_GROWTH_CURVE |
| `TIME_GROWTH_CURVE` | 2-col curve | ka, factor | Growth multiplier through time |
| `GROWTH_MAP` | 2-D grid | factor | Spatial growth multiplier |

---

### Tectonics

Vertical tectonic movement (subsidence or uplift).

| Keyword | Type | Unit | Description |
|---|---|---|---|
| `TECT_FACTOR` | scalar | m/ka | Base tectonic rate (negative = subsidence) |
| `TECT_MAP` | 2-D grid | factor | Spatial multiplier on TECT_FACTOR |
| `TIME_TECT_CURVE` | 2-col curve | ka, factor | Tectonic rate multiplier through time |

---

## Output File Structure

The output VVM file produced by the engine contains one **state block** per timestep, each
consisting of:

```
TIME = <current time in ka>
SEALEVEL = <sea level in m>
TOP = <NX × NY grid of elevations>
SED = <NX × NY × NSTEP sediment fraction volume>
```

Each block is appended sequentially; the Visualizer reads them all and presents them as a
time-slider sequence.

---

## Curve Files

Curve files contain a two-column matrix (time or depth in column 1, value in column 2):

```
! Sea-level curve — time (ka) vs elevation (m)
TIME_SEALEVEL_CURVE =
     0.0    0.0
    20.0  -30.0
    40.0   10.0
    60.0  -50.0
```

The `INCLUDE` keyword is used to reference them:

```
INCLUDE = "curves/sealevel_cycles_rise_15ma.vvm"
```

---

## Map Files

Map files contain a 2-D grid of values (one row per line, space-separated):

```
! Initial topography — 60 columns × 40 rows
TOP =
  -200.0  -198.5  -197.1  ...  (60 values)
  -200.0  -198.5  -197.1  ...
  ...                           (40 rows total)
```

The grid dimensions must match `NX` (columns) × `NY` (rows) set in the main input file.

---

## Minimal Example

```vvm
TITLE    = "Simple aggradation"
OUTFILE  = "C:/path/to/Output/simple_out.vvm"

CELLSIDE = 500
INCLUDE  = "maps/top_slope_4p_60x40.vvm"

SED_DIAMETERS = 20 5
SED1 = 0.7
SED2 = 0.3

STEP_DURATION = 20
STEP_COUNT    = 50

SEALEVEL     = 0
DISP_FACTOR  = 0.05
```

---

## Full Example (carboclastics)

```vvm
TITLE    = "Carboclastics — mixed carbonate + clastic system"
OUTFILE  = "C:/path/to/Output/carboclastics_out.vvm"

CELLSIDE = 500
INCLUDE  = "maps/top_slope_4p_60x40.vvm"        ! initial surface

SED_DIAMETERS = 20 5 1 0.1
SED1 = 0.4   SED2 = 0.3   SED3 = 0.2   SED4 = 0.1

STEP_DURATION = 20
STEP_COUNT    = 75
INITIAL_TIME  = 0

INCLUDE = "curves/sealevel_cycles_rise_15ma.vvm"  ! sea-level
DISP_FACTOR = 0.05
INCLUDE = "curves/dispersion_curve.vvm"            ! depth multiplier

GROWTH_FACTOR = 0.08
GROWTH_SED_ID = 4
INCLUDE = "curves/carb_level_growth.vvm"           ! depth-growth curve

CHANNEL_FACTOR = 0.5
CHANNEL_SOURCES = 1 2 3
CHANNEL_EVENT_PERIOD   = 100
CHANNEL_EVENT_DURATION = 20
```
