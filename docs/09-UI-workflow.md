# UI Workflow — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-UI-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document describes the user interface layout, the ten-step engineering workflow,
view modes, drawing editor capabilities, colour conventions, accessibility provisions,
and keyboard shortcuts for ThermPro.

---

## 2. Design Principles

1. **Engineering first.** The UI serves engineering work, not decoration. Every object
   in the drawing is a real engineering entity with coordinates, properties, and
   traceability.

2. **Explicit over implicit.** The active calculation mode, its assumptions, its
   applicability status, and its limitations are visible at all times — not hidden in
   a report.

3. **Non-destructive.** Calculations, optimisation suggestions, and comparisons never
   modify the active design without explicit user approval.

4. **Auditable.** Every state that produced a result is preserved. The user can
   navigate back to any historical calculation run and see exactly what was calculated.

5. **Progressive disclosure.** Simple projects require simple inputs. Advanced options
   (manual grid refinement, radiosity matrix, CFD export) are accessible but not
   imposed on every user.

---

## 3. Application Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TOP BAR                                                                    │
│  [ThermPro]  [Project ▾]  [View ▾]  [Calculate ▾]  [Compare ▾]  [Report ▾]│
│              [Project name: Substation MV/LV Room — Panel DB-A]            │
└───────────┬───────────────────────────────────────┬──────────────┬──────────┘
│           │                                       │              │
│  LEFT     │         CENTRE                        │   RIGHT      │
│  PANEL    │         DRAWING EDITOR                │   INSPECTOR  │
│  (240px)  │         (flex width)                  │   (300px)    │
│           │                                       │              │
│ ┌────────┐│  ┌──────────────────────────────────┐│ ┌──────────┐ │
│ │Library ││  │  [View buttons][Zoom][Grid][Snap] ││ │Properties│ │
│ │ tabs:  ││  │                                  ││ │ of       │ │
│ │Devices ││  │                                  ││ │ selected │ │
│ │Busbars ││  │         Enclosure Drawing        ││ │ entity   │ │
│ │Fans    ││  │         (Konva.js canvas)        ││ │          │ │
│ │Mater.  ││  │                                  ││ │Dimensions│ │
│ │Std. Lib││  │                                  ││ │Material  │ │
│ └────────┘│  │                                  ││ │Losses    │ │
│           │  │                                  ││ │Status    │ │
│ Search:   │  │                                  ││ │Source    │ │
│ [_______] │  │                                  ││ │          │ │
│           │  └──────────────────────────────────┘│ └──────────┘ │
│ Drag items│                                       │              │
│ onto      │                                       │Calculation   │
│ canvas    │                                       │Mode: [▾]    │
│           │                                       │Status: —    │
└───────────┴───────────────────────────────────────┴──────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│  BOTTOM PANEL (collapsible)                                                 │
│  [Validation] [Calculation Log] [Warnings] [Convergence]                   │
│  ● W-001 Fan F1 has no manufacturer P-Q curve — using default              │
│  ● E-002 Device CB-12 overlaps with busbar B2 at [x=350, y=800]           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Ten-Step Workflow

The workflow is accessible from the top bar `[Project ▾]` menu or from a step wizard
that can be opened at any time.

### Step 1 — Project Information

**Screen:** Project settings dialog (modal or dedicated page)

**Fields:**
- Project name (required)
- Customer name
- Assembly designation
- Standard edition (dropdown: IEC 61439-1:2011+AMD1:2020, ...)
- System voltage [V] and frequency [Hz]
- Ambient temperature maximum [°C] and minimum [°C]
- Reference temperature [°C] (pre-filled to 20 °C; overridable)
- Altitude [m]
- Installation: Indoor / Outdoor
- IP rating (text field with validation)
- Notes (free text, supports markdown)

**Validation (live):**
- Standard edition must be selected before calculation.
- Missing required fields shown with inline error indicators.

---

### Step 2 — Enclosure Layout

**Screen:** Main drawing editor

**Sub-steps accessible from left panel or right-click menu:**
- Create new enclosure → opens dimension form
- Enter H × W × D, wall thickness, material (from library)
- Select installation type
- Add adjacent cubicle (side, rear)
- Mark surfaces as exposed / covered / wall-mounted
- Add doors and removable panels
- Create compartment (draw a rectangle inside the enclosure)
- Add partition (draw a line; set material and perforation)
- Add opening between compartments

**Drawing feedback:**
- Enclosure drawn as dimensioned rectangle with labelled dimensions.
- Compartments shown as shaded zones.
- Partitions shown as thick lines.
- Openings shown as dashed gaps in partitions.
- Form type label shown in the corner of each compartment.

---

### Step 3 — Heat-Source Placement

**Screen:** Main drawing editor with left panel showing Device / Busbar / Conductor tabs

**Placement actions:**
- Drag a device from the library panel and drop onto the drawing.
- The system snaps the device to the grid and checks for overlaps.
- Double-click a placed device to open the inspector (right panel).
- Inspector shows: library entry, dimensions, rated current, rated loss, data confidence.
- User enters actual operating current and optionally overrides loss value.
- Busbar is drawn by clicking start point → end point. Properties set in inspector.

**Validation feedback (real-time):**
- Red outline on device: overlap detected.
- Yellow outline: insufficient clearance.
- Orange outline: device outside any assigned compartment.
- Green badge: valid placement.

---

### Step 4 — Ventilation Placement

**Screen:** Main drawing editor with left panel showing Ventilation tab

**Placement actions:**
- Select element type from the left panel (inlet grille, fan, etc.).
- Click on an enclosure wall or internal surface to place.
- Inspector shows: type, position, free area, Cd, filter status.
- For fans: opens fan curve editor (plot of Q vs ΔP from library data).
- User enters installed speed if different from rated.
- Thermostat or speed-control settings shown in inspector.

---

### Step 5 — Electrical Loading

**Screen:** Loading table (right panel or dedicated dialog accessible from Calculate menu)

**Columns per circuit:**
- Circuit ID / label
- Device reference
- Rated current [A]
- Actual current [A]
- Diversity factor
- THD [%]
- Calculated loss [W] (live preview)
- Override loss [W] (optional)
- Loss source (CALCULATED / MANUFACTURER / MEASURED / ASSUMED)
- Data confidence

**Global:**
- Total actual power dissipation [W] shown at bottom.
- Flag indicator when ASSUMED values are present.

---

### Step 6 — Mesh / Nodal-Grid Definition

**Screen:** Mesh view (toggle from View menu)

**Actions:**
- Click "Generate Grid" → system auto-generates thermal cells.
- Grid shown as a fine rectangular overlay on the drawing.
- Click any cell to inspect: dimensions, assigned compartment, cell type.
- Click "Refine Region" → draw a rectangle; grid doubles within the region.
- Summary panel: total cell count, minimum and maximum cell size.

---

### Step 7 — Calculation

**Screen:** Calculate dialog (from Calculate menu)

**Actions:**
1. Select calculation mode (MODE 1 / 2 / 3 / auto-select).
2. View eligibility check results before running.
3. Configure solver settings (or use defaults).
4. Click "Run Calculation."
5. Progress bar shows outer iteration, inner iteration, maximum ΔT.
6. Calculation log streams in the bottom panel.
7. On completion: status shown (Converged / Non-converged / Failed) with details.

**Eligibility display:**
A table lists every eligibility condition with PASS / FAIL / WARNING status.
Non-eligible configurations cannot proceed to MODE 1 — the user must switch to MODE 2/3.

---

### Step 8 — Results

**Screen:** Results overlay on the drawing editor, plus Results tab in right panel

**Selectable overlays (from View menu):**

| Overlay | Description |
|---------|-------------|
| Thermal heat map | False-colour temperature map on air cells |
| Airflow arrows | Directional arrows with mass-flow and velocity labels |
| Hot spots | Labelled markers with severity colour coding |
| Component temperatures | Text annotations on each device and busbar |
| Derating | Permissible current annotation on each device |
| Thermal margins | Colour-coded margin bands on each component |
| Pass/Fail status | Green/yellow/orange/red overlay per component |

**Right panel — Results Inspector:**

For each selected object:
- Absolute temperature [°C]
- Temperature rise [K]
- Permissible limit [K]
- Thermal margin [K]
- Severity: PASS / WATCH / WARNING / FAIL / NOT_VERIFIABLE
- Calculation mode used
- Data confidence

**Summary table (bottom panel — Results tab):**
- All components sorted by severity (FAIL first)
- Click any row to highlight the component in the drawing

---

### Step 9 — Optimisation

**Screen:** Optimisation panel (from Calculate → Optimise)

**Display:**
- List of suggested improvements, each showing:
  - Suggestion description
  - Predicted improvement [K]
  - Confidence level
  - Supporting evidence (linked to hot spot or warning)
  - "Apply to New Alternative" button

**Rules:**
- Suggestions are generated automatically from the results.
- The user may apply any suggestion to a new design alternative for comparison.
- No suggestion is applied to the current design without explicit user action.

---

### Step 10 — Report

**Screen:** Report dialog (from Report menu)

**Options:**
- Report title and reference
- Author and reviewer fields
- Include/exclude sections:
  - Project inputs
  - Enclosure drawings (at selected views)
  - Device and ventilation schedule
  - Calculation method and mode
  - Governing equations
  - Assumptions and limitations
  - Data provenance table
  - Convergence records
  - Heat maps (colour or monochrome)
  - Hot-spot table
  - Compliance/applicability statements
  - Audit checksum

**Output formats:**
- PDF (download or view in browser)
- XLSX (structured data export)

---

## 5. View Modes

| View | Description | Hotkey |
|------|-------------|--------|
| Front | Front elevation of selected enclosure | F1 |
| Rear | Rear elevation | F2 |
| Left | Left side elevation | F3 |
| Right | Right side elevation | F4 |
| Top | Plan (top) view | F5 |
| Section | Horizontal or vertical cross-section | F6 |
| 3D | Three.js 3D render of enclosure | F7 |
| Thermal | Results overlay: heat map | F8 |
| Airflow | Results overlay: airflow arrows | F9 |
| Losses | Results overlay: loss density | F10 |
| Validation | Geometry and data validation overlay | F11 |

Section view: user draws a cutting plane on any view; the editor shows the cross-section
with all components intersected by that plane.

---

## 6. Drawing Editor Capabilities

| Feature | Description |
|---------|-------------|
| Grid | Configurable grid (default 10 mm); toggle with G key |
| Snap | Snap to grid, snap to other objects' edges, snap to dimension lines |
| Zoom | Scroll wheel; Ctrl+= / Ctrl+- ; fit-to-window button |
| Pan | Middle-click drag or Space+drag |
| Select | Left click; Ctrl+click for multi-select; drag rectangle to select region |
| Move | Drag selected objects; arrow keys for 1 mm nudge; Shift+arrow for 10 mm |
| Dimensions | Live dimension display on selected objects and between selected pairs |
| Copy/Paste | Ctrl+C / Ctrl+V; paste offset by 10 mm to avoid overlap |
| Mirror | Horizontal/vertical mirror of selected objects |
| Rotate | R key for 90° steps; precise angle in inspector |
| Lock | Prevent accidental movement of fixed objects (Ctrl+L) |
| Group | Group multiple objects (Ctrl+G); treat as single movable unit |
| Layers | Show/hide device layer, busbar layer, ventilation layer, thermal cell layer |
| Undo/Redo | Ctrl+Z / Ctrl+Y; 50 levels default |

---

## 7. Colour Conventions

### 7.1 Heat Map Scale

| Colour | Meaning |
|--------|---------|
| Blue | Below ambient (reference) temperature |
| Cyan | Low temperature rise (0–5 K above ambient) |
| Green | Moderate temperature rise (5–15 K) |
| Yellow | Elevated temperature rise (15–25 K) |
| Orange | High temperature rise (25–35 K) |
| Red | Very high temperature rise (> 35 K) |

Scale endpoints are configurable. Default: 0 K (blue) to 40 K (red).

### 7.2 Severity Colours

| Severity | Colour | Hex |
|----------|--------|-----|
| PASS | Green | #2E7D32 |
| WATCH | Teal | #00838F |
| WARNING | Amber | #F57F17 |
| FAIL | Red | #C62828 |
| NOT_VERIFIABLE | Grey | #616161 |

### 7.3 Airflow Arrows

| Condition | Arrow Colour |
|-----------|-------------|
| Inlet air (near ambient) | Blue |
| Intermediate air | Green → yellow (temperature gradient) |
| Outlet / exhaust air | Red / orange |
| Reverse flow | Dashed red |
| Stagnant zone | Grey dotted |

Arrow width is proportional to mass flow rate [kg/s].
Annotations: velocity [m/s] and temperature [°C] at element midpoint.

### 7.4 Monochrome Mode

When monochrome mode is active (for engineering report printing):
- Heat map replaced by greyscale (darker = hotter).
- Severity indicated by hatch pattern (PASS = none, WARNING = diagonal, FAIL = cross-hatch).
- Airflow arrows replaced by black arrows with numerical annotations.
- All colour-only information is also conveyed by text labels or symbols.

---

## 8. State Management (Frontend)

```
Zustand stores:

projectStore     — active project, assembly, enclosure list
editorStore      — active view, grid settings, selected objects, undo stack
libraryStore     — cached device/material library data
calculationStore — active calculation run, status, progress
resultStore      — latest result snapshot, selected overlay
comparisonStore  — list of saved alternatives for comparison
uiStore          — panel sizes, open dialogs, notifications
```

Each store slice is independently subscribable. Heavy result data (heat maps, node arrays)
is stored in `resultStore` as typed arrays for efficient rendering.

---

## 9. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+S | Save project |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+C | Copy selection |
| Ctrl+V | Paste |
| Ctrl+G | Group selection |
| Ctrl+L | Lock/unlock selection |
| Ctrl+A | Select all |
| Del / Backspace | Delete selection (with confirmation if significant) |
| G | Toggle grid |
| R | Rotate selection 90° |
| F1–F11 | View modes (see Section 5) |
| Space+drag | Pan |
| Esc | Deselect / cancel active tool |
| Ctrl+= | Zoom in |
| Ctrl+- | Zoom out |
| Ctrl+0 | Fit to window |
| Ctrl+Enter | Run calculation |

---

## 10. Accessibility and Engineering Compliance

- All colour-coded information is supplemented by text or symbol alternatives.
- Monochrome mode produces a print-ready engineering drawing compliant with standard
  black-and-white report formats.
- All numeric values display their unit symbol.
- Screen reader support: ARIA labels on all interactive controls.
- Tab order follows the logical engineering workflow.
- No information is conveyed solely by colour.

---

*End of THERM-UI-001*
