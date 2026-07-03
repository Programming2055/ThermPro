# Units and Dimensional Analysis Policy — LV Switchboard Thermal Digital Twin

**Document:** M0-10  
**Milestone:** 0 (correction commit)  
**Date:** 2026-07-03  
**Status:** APPROVED (DR-011)  
**Source:** OQ-011 resolution; THERM-EQN-001 Rev 0.2

---

## 1. Governing Principle

All numerical computations inside `thermpro_engine` use SI base units without exception.
Unit conversion is performed at the boundary between external data (API input, library
records, user interface) and the engine. The engine never accepts ambiguous units.

---

## 2. Canonical SI Units Table

The following table defines the one canonical unit for every physical quantity used in
thermpro_engine. Any deviation from this table is a bug.

| Quantity | Symbol | Canonical SI unit | Forbidden in engine |
|----------|--------|-------------------|---------------------|
| Temperature | T | K (kelvin, absolute) | °C, °F, °R |
| Temperature difference / rise | ΔT | K | °C difference |
| Length | L | m (metres) | mm, cm, ft, in |
| Area | A | m² | mm², cm², ft², in² |
| Volume | V | m³ | L, mL, cm³, ft³ |
| Mass | m | kg | g, lb |
| Time | t | s (seconds) | min, h |
| Mass flow rate | ṁ | kg/s | kg/h, g/s |
| Volumetric flow rate | Q_vol | m³/s | m³/h, L/s, CFM |
| Pressure | P | Pa (pascal, absolute) | bar, mbar, kPa, gauge |
| Pressure difference | ΔP | Pa | Pa gauge |
| Power | P | W (watts) | kW, mW |
| Energy | E | J (joules) | kWh, Wh |
| Electrical resistance | R | Ω (ohms) | mΩ, µΩ, kΩ |
| Electrical resistivity | ρ_e | Ω·m | µΩ·cm, Ω·mm²/m |
| Current | I | A (amperes) | mA, kA |
| Voltage | V | V (volts) | kV, mV |
| Frequency | f | Hz (hertz) | rpm |
| Thermal conductivity | k | W/(m·K) | W/(cm·K), BTU/(h·ft·°F) |
| Specific heat capacity | cp | J/(kg·K) | J/(g·K), kJ/(kg·K) |
| Density | ρ | kg/m³ | g/cm³, kg/L |
| Dynamic viscosity | μ | Pa·s | cP, mPa·s |
| Kinematic viscosity | ν | m²/s | mm²/s, cSt |
| Convection coefficient | h | W/(m²·K) | W/(cm²·K) |
| Emissivity | ε | — (dimensionless 0–1) | % |
| Stefan-Boltzmann constant | σ | W/(m²·K⁴) | (fixed value) |
| Force | F | N (newtons) | kN, lbf |
| Torque | τ | N·m | N·cm, lbf·ft |

---

## 3. Input Boundary Conversions

At every system boundary (API input, library record loading, file import) the following
conversions must be applied before data enters the engine:

| Input field / context | Typical user unit | Required conversion |
|-----------------------|-------------------|---------------------|
| Enclosure dimensions | mm (drawings) | ÷ 1000 → m |
| Busbar cross-section, width, thickness | mm | ÷ 1000 → m |
| Device dimensions | mm | ÷ 1000 → m |
| Opening dimensions | mm | ÷ 1000 → m |
| Conductor cross-section | mm² | ÷ 1 000 000 → m² |
| Contact resistance | µΩ | ÷ 1 000 000 → Ω |
| Bulk resistivity | µΩ·cm or nΩ·m | convert to Ω·m |
| Temperature (user input) | °C | + 273.15 → K |
| Temperature rise (user input) | K | no conversion needed |
| Volumetric flow rate | m³/h | ÷ 3600 → m³/s |
| Pressure (display) | Pa gauge | + P_atm → Pa absolute |
| Thermal conductivity (display) | W/(m·K) | already SI |
| Fan flow rate (datasheet) | m³/h or CFM | convert to m³/s |
| Fan pressure (datasheet) | Pa or mm H₂O | convert to Pa |

All conversions must be performed by a dedicated `unit_conversion.py` module within
`thermpro_engine`. No ad hoc conversion factors are permitted in physics modules.

---

## 4. Area Conventions

### 4.1 Gross Area vs. Net Free Area

These two quantities must never be confused. Their definitions and usage:

| Concept | Definition | Used where |
|---------|-----------|------------|
| `gross_area_m2` | Total face area of the opening or filter, including frame | Geometry display |
| `net_free_area_m2` | Area through which air actually flows (gross × open_area_fraction) | Orifice flow equation |
| `effective_area_m2` | Cd × net_free_area_m2 | Airflow network element |

The orifice flow equation uses `effective_area_m2` only:
```
Q = effective_area_m2 × sqrt(2 × |ΔP| / ρ)
```

The Cd (discharge coefficient) is applied to produce effective area; it must never be
applied twice.

### 4.2 Busbar Cross-Section

When a busbar is described by width and thickness (rectangular cross-section):
```
cross_section_m2 = width_m × thickness_m
```
The per-unit-length resistance is:
```
R_per_m = ρ_ref × [1 + α(T − T_ref)] / cross_section_m2   [Ω/m]
```
The total segment resistance is:
```
R_segment = R_per_m × length_m   [Ω]
```

---

## 5. Pressure Convention

All pressures inside the engine are **absolute** in pascals (Pa). The airflow network
uses gauge pressure differences (ΔP) but the underlying node pressures are absolute.

Standard atmospheric pressure for air property calculations: 101 325 Pa.

When the user specifies a gage pressure (e.g. filter pressure drop), add P_atm before
passing to any air property function that requires absolute pressure.

Buoyancy stack pressure is a differential (ΔP) and is always computed correctly:
```
ΔP_buoy = (ρ_cold − ρ_hot) × g × H   [Pa]
```
No absolute-to-gauge correction is needed here; ΔP is already gauge-equivalent.

---

## 6. Mandatory Unit Conversion Tests

The following unit conversion tests must pass on every CI push (tagged `@pytest.mark.units`).
They are part of the `tests/unit/test_unit_conversions.py` test file.

| Test ID | Test description | Asserts |
|---------|-----------------|---------|
| UT-UNITS-001 | Convert 600 mm to m | result == 0.600 m (tolerance: 1e-9) |
| UT-UNITS-002 | Convert 50 µΩ to Ω | result == 50e-6 Ω (tolerance: 1e-15) |
| UT-UNITS-003 | Convert 40 °C to K | result == 313.15 K (tolerance: 1e-6) |
| UT-UNITS-004 | Radiation with T[°C] input raises ValueError | ValueError raised before engine receives value |
| UT-UNITS-005 | Convert 1000 m³/h to m³/s | result == 0.2778 m³/s (tolerance: 1e-4) |
| UT-UNITS-006 | Gross area vs. net free area vs. effective area | gross=0.1 m², open_fraction=0.6, Cd=0.6 → effective=0.036 m² |
| UT-UNITS-007 | Gauge pressure 50 Pa (gauge) → absolute 101 375 Pa | P_abs = P_gauge + 101 325 (tolerance: 1 Pa) |
| UT-UNITS-008 | Thermal conductivity 50 W/(m·K) passes through unchanged | value == 50.0 W/(m·K) (no conversion required; verify it's not scaled) |
| UT-UNITS-009 | Resistance 1.72e-8 Ω·m (Cu resistivity) × length / area | R consistent with UT-JOULE-001 |
| UT-UNITS-010 | Density 1.2 kg/m³ is not confused with 1200 g/m³ | value in kg/m³; any g/m³ input must be rejected or converted |

---

## 7. Display Units

The API may return values in display units for the UI, clearly labelled. Display
conversions are the responsibility of the API layer, not the engine. The engine returns
SI units only.

Recommended display units:

| Quantity | Display unit | Conversion from SI |
|----------|-------------|-------------------|
| Temperature | °C | T_display = T_K − 273.15 |
| Temperature rise | K | same as SI |
| Dimension | mm | L_display = L_m × 1000 |
| Resistance | µΩ | R_display = R_Ω × 1 000 000 |
| Flow rate | m³/h | Q_display = Q_m3s × 3600 |
| Pressure | Pa | same as SI |
| Power | W | same as SI |

Display unit conversions must be tested with a round-trip test (SI → display → SI)
for each quantity.

---

## 8. Dimensional Analysis Checklist

Every new equation added to `thermpro_engine/physics/` or `thermpro_engine/network/`
must include:
- A docstring listing the units of every input and output parameter
- A dimensional analysis comment showing the equation is dimensionally consistent
- A corresponding unit test in `tests/unit/`

Example (from `physics/conduction.py`):
```python
def conduction_conductance(k: float, area: float, length: float) -> float:
    """
    Compute thermal conductance for flat-wall conduction.

    Args:
        k:      Thermal conductivity [W/(m·K)]
        area:   Cross-sectional area [m²]
        length: Wall thickness [m]

    Returns:
        Conductance G [W/K]

    Dimensional check:
        G = k [W/(m·K)] × A [m²] / L [m]
          = W/(m·K) × m² / m
          = W/K  ✓
    """
    return k * area / length
```

Reviewers must reject any PR that adds physics code without a dimensional check comment.

---

## 9. Schema Unit Annotations

All fields in `M0-03-calculation-input-schema.json` and `M0-04-calculation-result-schema.json`
include a `"description"` field that states the SI unit in square brackets.

Example: `"external_height_m": { "description": "External enclosure height [m]." }`

The field name suffix convention:

| Suffix | Unit implied |
|--------|-------------|
| `_m` | metres |
| `_m2` | m² |
| `_m3` | m³ |
| `_K` | kelvin |
| `_C` | °C (display fields only) |
| `_W` | watts |
| `_A` | amperes |
| `_V` | volts |
| `_Hz` | hertz |
| `_Pa` | pascal (absolute) |
| `_ohm` | ohms |
| `_ohm_m` | Ω·m |
| `_W_mK` | W/(m·K) |
| `_J_kgK` | J/(kg·K) |
| `_kg_m3` | kg/m³ |
| `_m3s` | m³/s |
| `_1_K` | 1/K (e.g. temperature coefficient) |
| `_Nm` | N·m (torque) |
| `_s` | seconds |
| `_fraction` | dimensionless, 0–1 |

Any new field that does not follow this naming convention must be justified in the PR review.
