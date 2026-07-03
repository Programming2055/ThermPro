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

---

## 3. Calculation Modes and Standards Alignment

| Mode | Name | Standard/Method | Normative Status |
|------|------|-----------------|-----------------|
| MODE 1 | IEC TR 60890 | IEC TR 60890:2022 | Permitted method per IEC 61439 |
| MODE 2 | Nodal Thermal Network | CT145 / physics-based | Engineering calculation (not standardised) |
| MODE 3 | Forced-Ventilation Airflow Network | Physics-based | Engineering calculation (not standardised) |
| MODE 4 | CFD Export/Import Adapter | External solver | External solver provides results |

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

The following thermal analysis topics are not covered by any current standard-compliant
method in ThermPro and must be handled by a qualified engineer using external tools:

- Short-circuit thermal effects (adiabatic temperature rise of conductors).
- Temperature rise during arc-flash events.
- Thermal ageing models for insulation.
- Transient start-up and load-cycle analysis (architecture is provided but steady-state is the initial implementation).
- Outdoor enclosures subject to direct solar radiation (solar load may be entered as an additional heat source but is not calculated internally).

---

*End of THERM-STD-001*
