# Standards and Applicability — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-STD-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document defines which standards govern the thermal analysis performed by ThermPro,
identifies the scope and eligibility conditions for each calculation mode, describes the
data strategy for licensed standard tables, and specifies how standard coefficient datasets
are versioned and attributed.

---

## 2. Applicable Standards

### 2.1 IEC 61439-1 — General Rules

**Full title:** Low-voltage switchgear and controlgear assemblies — Part 1: General rules  
**Current edition:** IEC 61439-1:2011 + AMD1:2020 + AMD2:2023 (verify current edition at time of use)

**Relevance to ThermPro:**

- Provides the design verification framework within which thermal analysis sits.
- Defines "temperature-rise verification" as one of the required design verifications.
- Defines the reference ambient temperature (typically 35 °C external / 40 °C for internal equipment).
- Defines the principle of diversity factor application.
- Specifies permissible temperature limits for conductors, insulating materials, operator-accessible surfaces, and terminals.
- ThermPro SHALL NOT claim IEC 61439-1 design verification solely on the basis of its calculations. The software is a calculation aid; formal verification requires a qualified engineer's sign-off.

### 2.2 IEC 61439-2 — Power Switchgear and Controlgear Assemblies

**Full title:** Low-voltage switchgear and controlgear assemblies — Part 2: Power switchgear and controlgear assemblies  
**Current edition:** IEC 61439-2:2011 + AMD1:2020 (verify current edition at time of use)

**Relevance to ThermPro:**

- Provides product-specific requirements for LV power switchgear assemblies.
- Specifies current-carrying capacity requirements and temperature limits.
- References IEC TR 60890 as an acceptable calculation method for temperature-rise verification.

### 2.3 IEC TR 60890:2022 — Temperature-Rise Evaluation

**Full title:** IEC TR 60890:2022 — A method of temperature-rise assessment by extrapolation for partially type-tested assemblies (PTTA) of low-voltage switchgear and controlgear

**Relevance to ThermPro:**

- Provides the empirical method implemented as MODE 1.
- Is a Technical Report, not a normative standard — its use is permitted, not mandated.
- Uses tabulated empirical coefficients derived from test results.
- Is explicitly limited to natural-ventilation and certain closed-enclosure configurations.

**Important notice regarding IEC TR 60890 tables:**  
The empirical tables and coefficients in IEC TR 60890 are copyrighted by IEC. ThermPro does not ship these tables in its default distribution. An administrator must import a licensed dataset (see Section 5).

### 2.4 Schneider Electric Cahier Technique No. 145

**Full title:** Thermal Study of LV Electric Switchboards — Schneider Electric Cahier Technique No. 145

**Relevance to ThermPro:**

- Engineering reference for the nodal thermal network method (MODE 2).
- Describes the subdivision of an enclosure into isothermal volumes.
- Provides the framework for thermal admittance matrices, natural convection between cells, and the iterative solution between temperature and derating.
- The document is used as a methodology reference only. Proprietary datasets, manufacturer-specific tables, and any copyrighted numerical values from this document are NOT reproduced in ThermPro.

### 2.5 IEC 60947 — Low-Voltage Switchgear and Controlgear

**Full title:** IEC 60947 series — Low-voltage switchgear and controlgear

**Relevance to ThermPro:**

- Governs the individual devices installed in assemblies (circuit breakers, disconnectors, contactors, motor-starters, fuses).
- Temperature limits for device terminals and enclosures referenced in IEC 60947 inform the device thermal limit database.
- Loss values from IEC 60947 type-test reports are the preferred source for DeviceLibrary entries.

### 2.6 IEC 60909 — Short-Circuit Currents

**Full title:** IEC 60909-0:2016 — Short-circuit currents in three-phase a.c. systems — Part 0: Calculation of currents

**Relevance to ThermPro:**

- Provides the network-side framework for calculating prospective short-circuit current at the assembly.
- ThermPro does not perform short-circuit current calculations. The short-circuit current is an input parameter entered by the engineer.
- The adiabatic conductor-heating check uses the fault current from this source.

### 2.7 IEC TR 61641 — Internal Arcing in Enclosed LV Switchgear

**Full title:** IEC TR 61641:2014 — Enclosed low-voltage switchgear and controlgear assemblies — Guide for testing under conditions of arcing due to internal fault

**Relevance to ThermPro:**

- Defines internal-arc testing philosophy and pressure/thermal effects on assembly enclosures.
- The arc-flash safety module references IEC TR 61641 for enclosure-level internal-arc behaviour.
- ThermPro does not replace the IEC TR 61641 test; the software provides informative hazard screening using IEEE 1584 parametric methods.

### 2.8 IEC TS 63107 — Active Arc-Fault Mitigation

**Full title:** IEC TS 63107 — Low-voltage switchgear and controlgear assemblies — Guide for active arc fault mitigation systems

**Relevance to ThermPro:**

- Referenced when the arc-flash module evaluates mitigation options (arc detection relays, arc-quenching devices).
- Mitigation systems modelled in ThermPro should be labelled with reference to IEC TS 63107 or equivalent product documentation.

### 2.9 IEEE 1584-2018 — Arc-Flash Hazard Calculations

**Full title:** IEEE 1584-2018 — IEEE Guide for Performing Arc-Flash Hazard Calculations

**Relevance to ThermPro:**

- Provides the parametric incident-energy model for LV and MV electrical equipment.
- ThermPro's arc-flash safety module implements the IEEE 1584-2018 workflow:
  - Electrode configuration classification (VCB, VCBB, HCB, VOA, HOA).
  - Working distance and enclosure size inputs.
  - Arcing current calculation from bolted fault current.
  - Incident energy in cal/cm² and arc-flash boundary in metres.
- Results are labelled as INFORMATIVE. The engineer must verify applicability of the IEEE 1584 model to the specific equipment.

### 2.10 North American Standards — UL 891, UL 1558, ANSI/IEEE C37.20.1

**Full titles:**
- UL 891 — Switchboards, 1000 V or Less
- UL 1558 — Metal-Enclosed Low-Voltage Power Circuit Breaker Switchgear
- ANSI/IEEE C37.20.1 — IEEE Standard for Metal-Enclosed Low-Voltage (1000 Vac and Below, 3200 Vdc and Below) Power Circuit Breaker Switchgear

**Relevance to ThermPro:**

- Cover North American switchboard and metal-enclosed switchgear product families.
- UL/ANSI temperature-rise limits differ from IEC 61439 in some respects; in particular, a 65 °C bus temperature rise above a 40 °C maximum ambient is a common UL/ANSI design reference for relevant designs.
- ThermPro implements a **dual compliance mode** that allows the engineer to select between IEC 61439 and UL/ANSI temperature-limit profiles. The same thermal calculation is used; only the compliance interpretation layer differs.
- The software separates **physical prediction** from **compliance interpretation** so that the same temperature field can be assessed against either standard family without re-running the solver.

### 2.11 NFPA 70E — Electrical Safety in the Workplace

**Full title:** NFPA 70E:2024 — Standard for Electrical Safety in the Workplace

**Relevance to ThermPro:**

- Governs safe work practices for personnel working on or near energised electrical equipment.
- The arc-flash safety module outputs required by NFPA 70E include: incident energy (cal/cm²), arc-flash protection boundary (m), and required PPE category.
- ThermPro labels NFPA 70E outputs clearly and does not substitute for a formal arc-flash study by a qualified person.

---

## 3. Calculation Modes and Standards Alignment

| Mode | Name | Standard/Method | Normative Status |
|------|------|-----------------|-----------------|
| MODE 1 | IEC TR 60890 | IEC TR 60890:2022 | Permitted method per IEC 61439 |
| MODE 2 | Nodal Thermal Network | CT145 / physics-based | Engineering calculation (not standardised) |
| MODE 3 | Forced-Ventilation Airflow Network | Physics-based | Engineering calculation (not standardised) |
| MODE 4 | CFD Export/Import Adapter | External solver | External solver provides results |
| ARC-FLASH | IEEE 1584-2018 Arc-Flash Module | IEEE 1584-2018 + NFPA 70E | Informative safety screening only |

### 3.1 North American Parallel Rules Stack

ThermPro supports a parallel compliance interpretation layer for North American markets.
The thermal solver is identical; only the temperature-limit profile and report labels change.

| Element | IEC Framework | North American Framework |
|---------|--------------|------------------------|
| Primary assembly standard | IEC 61439-2 | UL 891 / UL 1558 / ANSI/IEEE C37.20.1 |
| Calculation method | IEC TR 60890 (MODE 1) or physics-based | Physics-based; UL temperature limits applied |
| Bus temperature limit | 70 K rise (copper, bare) per IEC 61439 | 65 K rise above 40 °C max ambient (UL/ANSI typical) |
| Arc-flash standard | IEC TR 61641 (internal arc test) | IEEE 1584-2018 + NFPA 70E |
| Short-circuit current | IEC 60909 | ANSI/IEEE C37 methods |
| Compliance claim | "Temperature-rise verification per IEC TR 60890" | "Temperature assessment per UL 891 / UL 1558 limits" |

**Key principle:** Physical prediction and compliance interpretation are separated.
The same temperature field can be assessed against either standard family without
re-running the solver.

---

## 4. IEC TR 60890 Eligibility Conditions

The following conditions must ALL be met for MODE 1 to be declared Eligible. Any failed
condition renders the configuration either Not Eligible or Eligible with Warnings.

### 4.1 Mandatory Eligibility Conditions

| Condition | Description | Failure Effect |
|-----------|-------------|----------------|
| ELIG-01 | No forced ventilation (fans) active in the enclosure | Not Eligible |
| ELIG-02 | Enclosure is partially type-tested (PTTA) or newly assembled | Not Eligible |
| ELIG-03 | Internal devices are mounted in a manner consistent with the test basis of the method | Warning |
| ELIG-04 | The ambient temperature is within the standard's defined range | Warning |
| ELIG-05 | The total internal power dissipation is within applicable limits of the method | Warning |
| ELIG-06 | The enclosure is not a sealed (IP6X) enclosure relying solely on conduction | Warning — separate calculation required |
| ELIG-07 | An authorised licensed coefficient dataset is loaded for the applicable configuration | Insufficient Information |
| ELIG-08 | Openings, if present, are natural ventilation openings consistent with the method's basis | Warning |

### 4.2 Eligibility Results

| Result | Meaning |
|--------|---------|
| **Eligible** | All mandatory conditions met; result is within claimed scope of IEC TR 60890. |
| **Eligible with Warnings** | Mandatory conditions met; one or more warning-level conditions not satisfied. Result is informative; engineer must review warnings. |
| **Not Eligible** | One or more mandatory conditions failed. MODE 1 cannot be used. |
| **Insufficient Information** | Required data are not entered or the coefficient dataset is not loaded. Cannot determine eligibility. |

### 4.3 Forced Ventilation Exclusion

When any supply fan, exhaust fan, or internal circulation fan is active in an enclosure or
compartment, the IEC TR 60890 mode SHALL be automatically disabled for that enclosure.
The software SHALL display a clear message explaining the reason.

An override switch is NOT provided. The exclusion is non-negotiable under the current
scope of the standard.

---

## 5. Data Strategy for Licensed Standard Tables

### 5.1 Problem

The empirical coefficient tables in IEC TR 60890 are copyrighted by IEC. Distributing
them inside the application software without a licence would constitute copyright
infringement.

### 5.2 Adopted Strategy: Administrator-Import of Licensed Data

ThermPro adopts Strategy 2 from the requirements:

1. The application ships with a **template JSON file** that defines the required data
   structure for IEC TR 60890 coefficients — with all numerical values replaced by `null`
   and clear field descriptions.

2. An engineer or administrator who holds a valid IEC TR 60890:2022 licence enters the
   coefficient values into the template and imports it via the administrator interface.

3. The imported dataset is assigned a version number, a descriptive name, a source
   statement ("IEC TR 60890:2022, Table X"), and a creation timestamp.

4. ThermPro uses only the imported licensed dataset for calculations. The dataset is
   stored in the database and referenced by version in every calculation run.

5. The template file itself contains only structural metadata — no copyrighted numerical
   values.

### 5.3 Template Structure (Illustrative)

```jsonc
{
  "schema_version": "1.0",
  "dataset_name": "IEC TR 60890:2022 Coefficients",
  "standard_edition": "IEC TR 60890:2022",
  "source_statement": "<Enter: 'IEC TR 60890:2022, Table X, page Y'>",
  "licence_reference": "<Enter your IEC licence reference>",
  "imported_by": "<Engineer name>",
  "import_date": "<ISO 8601 date>",
  "coefficients": {
    "enclosure_constant_c0": null,
    "installation_factor_a": {
      "wall_mounted": null,
      "free_standing": null,
      "flush_mounted": null
    },
    "partition_factor_table": null,
    "temperature_distribution_factor": null
  }
}
```

### 5.4 Alternative Strategies (Not Currently Implemented)

| Strategy | Description | When Applicable |
|----------|-------------|-----------------|
| Strategy 1 | User enters coefficients manually during each session | Small deployments; no administrator role |
| Strategy 3 | Formula implementation where the standard text (not tables) explicitly permits parameterised computation | Must be verified with a lawyer; limited scope |
| Strategy 4 | External standards-data provider API | If IEC creates a licensed data service |

### 5.5 Dataset Versioning

Every coefficient dataset import creates a new immutable version record. Calculation runs
reference the dataset by version UUID. Updating or re-importing a dataset creates a new
version and does not alter any existing calculation that referenced the previous version.

---

## 6. IEC 61439 Temperature Limits

The following temperature limits from IEC 61439-1 are configurable reference values.
ThermPro ships with the values below as defaults. The engineer shall verify that the
edition and amendment current at the time of design are used.

| Location / Component | Default Limit (°C) | Notes |
|----------------------|--------------------|-------|
| Busbars — bare copper | 70 | Above ambient; verify with conductor type |
| Busbars — insulated copper | 70 | Above ambient at insulation surface |
| Terminals for external conductors | 70 | Above ambient |
| Operator-accessible metal surfaces | 55 | Above ambient |
| Operator-accessible insulating surfaces | 65 | Above ambient |
| Internal air (top of enclosure) | 40 | Rise above external ambient |
| Device maximum ambient | Per manufacturer | Must be imported from device library |

These limits are stored as configurable parameters, not hard-coded values, to allow
project-specific or national-variant adjustments.

---

## 7. Standard Versioning Policy

ThermPro maintains a configuration record specifying:

| Field | Description |
|-------|-------------|
| standard_id | Unique identifier (e.g., IEC_61439_1) |
| edition | Standard edition (e.g., 2011+AMD1:2020+AMD2:2023) |
| effective_date | Date this edition was adopted in the project |
| superseded_date | Date this edition was replaced (null if current) |
| notes | Any project-specific deviations or restrictions |

When a new standard edition is released, the engineer creates a new configuration record.
All historical calculation runs retain their original standard reference.

---

## 8. Limitations and Exclusions

The following topics are either covered with stated restrictions or excluded from
ThermPro and must be handled by a qualified engineer using external tools:

- **Short-circuit thermal effects:** The adiabatic I²t conductor-heating check is
  implemented as a screening calculation only. Non-adiabatic transient analysis is
  not currently implemented.
- **Arc-flash hazard:** The IEEE 1584-2018 module is an informative screening tool.
  It does not replace a formal arc-flash hazard analysis by a qualified person. Results
  carry an INFORMATIVE label and require engineer review before use in safety labels
  or work procedures.
- **Thermal ageing models for insulation:** Not implemented. Insulation ageing is
  outside the scope of steady-state thermal assessment.
- **Transient start-up and load-cycle analysis:** Architecture is provided but
  steady-state is the initial implementation. Transient capability is planned for
  a later milestone.
- **Outdoor enclosures subject to direct solar radiation:** Solar load may be entered
  as an additional heat source, but solar irradiance is not calculated internally.
- **Electromagnetic force analysis:** Electrodynamic forces from short-circuit currents
  are not calculated. ThermPro is a thermal tool only.

---

*End of THERM-STD-001*
