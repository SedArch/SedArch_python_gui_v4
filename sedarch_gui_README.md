# SedArch GUI

A full-featured PySide6 desktop application for the SedArch sedimentary simulation engine.

---

## Installation

```bash
pip install PySide6 matplotlib numpy
```

---

## Usage

```bash
# Open with empty editor
python sedarch_gui.py

# Open with an existing VVM input file
python sedarch_gui.py path/to/input.vvm
```

---

## Tabs

### ✏ Input Editor
Edit simulation parameters visually before running.

| Section | What you can edit |
|---------|-------------------|
| General | Title, step count, step duration, initial time |
| Grid | Cell side length (m) |
| Sediments | Grain diameters (mm) and base fractions for up to 4 types |
| Sea Level | Constant sea level or interactive TIME_SEALEVEL_CURVE editor |
| Dispersion | DISP_FACTOR and interactive LEVEL_DISP_CURVE editor |
| Growth | GROWTH_FACTOR for carbonates |
| File Paths | Output VVM path |
| Raw VVM | Full free-text editor for any advanced parameters |

**Curve editor**: click any "Edit …CURVE…" button to open an interactive table + live chart preview. Rows are fully editable; the plot updates as you type.

### ▶ Run
- Browse for your input `.vvm` file and the `sedarch_python/` directory  
- Click **Run** — simulation runs in a background thread  
- **Progress bar** updates every step  
- **Live preview** shows the topography heatmap (with shoreline contour) after each step  
- **Log** captures all simulation output  
- When complete, a dialog offers to load the results directly into the Visualizer  

### 📊 Visualize
Load any output `.vvm` file and explore results interactively.

| Plot type | Description |
|-----------|-------------|
| Topography Map | 2D colour map with shoreline contour; use slider to step through time |
| Sediment Maps | 4-panel grid showing each sediment type's surface fraction |
| E–W Cross-Section | Centreline elevation profiles, multiple timesteps overlaid |
| N–S Cross-Section | Same, perpendicular direction |
| Sea Level & Shoreline | Dual-axis time-series: sea level (m) and shoreline position (km) |
| Grain-Size Timeseries | Surface sediment fractions at grid centre through time |
| Strat Column | Marine vs. terrestrial exposure history at grid centre |
| Net Change Map | Final − initial topography with red/blue diverging colourscale |
| Overview (4-panel) | Six-panel summary: map, net change, grain size, cross-section, sea level, timeseries |

Controls:
- **Timestep slider** — scrub through all saved timesteps  
- **Colormap** selector  
- **Show shoreline / Show grid** toggles  
- **Export PNG** — saves the current figure at 200 dpi  
- **Navigation toolbar** — zoom, pan, save (standard Matplotlib toolbar)  

### ⚖ Compare
Load two separate output VVM files (Run A and Run B) and compare them side by side.

| Plot type | Description |
|-----------|-------------|
| Topography Maps | Side-by-side colour maps at the same timestep |
| Cross-sections | Overlay of both runs' centreline profiles |
| Sea Level & Shoreline | Both runs' SL and shoreline histories on one chart |
| Grain-size | Two-panel grain-size timeseries |
| Difference Map | A − B elevation difference map + histogram of the distribution |

A single **synchronized timestep slider** steps both runs together.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New input file |
| Ctrl+O | Open VVM file |
| Ctrl+S | Save current file |
| F5 | Start simulation |

---

## Notes

- The **SedArch Path** is the directory containing the `sedarch/` Python package  
  (i.e., the folder with `sedarch/__init__.py`). Set it via **Settings → Set SedArch Path…**  
  This setting is remembered between sessions.  
- The simulation runs in a **background QThread** so the GUI stays responsive.  
- You can **cancel** a running simulation with the Stop button; the current step will finish first.  
- Window size and position are **remembered** between sessions.
