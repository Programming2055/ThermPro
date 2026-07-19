"""
Engineering library domain types for thermpro_engine — Milestone 3.

All library entries are immutable value objects (frozen dataclasses).
All physical quantities are in SI base units (CR-ENG-013, M0-10).
Temperatures are stored in kelvin (CR-ENG-003).
No FastAPI, SQLAlchemy, or HTTP dependencies (CR-TECH-001).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Confidence and source enumerations
# ---------------------------------------------------------------------------


class LossConfidence(str, Enum):
    """Confidence level of a power-loss figure in a library entry."""

    MANUFACTURER_CERTIFIED = "MANUFACTURER_CERTIFIED"    # test-report backed
    MANUFACTURER_TYPICAL = "MANUFACTURER_TYPICAL"        # datasheet typical
    MEASURED = "MEASURED"                                # site / lab measurement
    CORRELATED = "CORRELATED"                            # validated correlation
    ESTIMATED = "ESTIMATED"                              # engineering estimate
    ASSUMED_DEFAULT = "ASSUMED_DEFAULT"                  # generic assumption


class MountingType(str, Enum):
    """Device mounting method within an enclosure."""

    DIN_RAIL = "DIN_RAIL"
    BOLT_ON = "BOLT_ON"
    DRAW_OUT = "DRAW_OUT"
    PLUG_IN = "PLUG_IN"
    PANEL_MOUNT = "PANEL_MOUNT"
    FREE_STANDING = "FREE_STANDING"


class VentilationRequirement(str, Enum):
    """Minimum ventilation requirement declared by the device manufacturer."""

    NONE = "NONE"
    CLEARANCE_TOP = "CLEARANCE_TOP"
    CLEARANCE_ALL_SIDES = "CLEARANCE_ALL_SIDES"
    FORCED_COOLING = "FORCED_COOLING"
    DEDICATED_COMPARTMENT = "DEDICATED_COMPARTMENT"


class BusbarProfile(str, Enum):
    """Cross-sectional profile of a busbar conductor."""

    FLAT = "FLAT"
    L_SECTION = "L_SECTION"
    C_SECTION = "C_SECTION"
    T_SECTION = "T_SECTION"
    TUBULAR = "TUBULAR"


class BusbarCoating(str, Enum):
    """Surface treatment of a busbar conductor."""

    BARE = "BARE"
    TIN_PLATED = "TIN_PLATED"
    SILVER_PLATED = "SILVER_PLATED"
    NICKEL_PLATED = "NICKEL_PLATED"
    PAINTED = "PAINTED"
    HEAT_SHRINK = "HEAT_SHRINK"


class ContactQuality(str, Enum):
    """Electrical contact quality at a bolted joint."""

    SILVER_PLATED = "SILVER_PLATED"
    TIN_PLATED = "TIN_PLATED"
    BARE_CLEANED = "BARE_CLEANED"
    BARE_AGED = "BARE_AGED"
    UNKNOWN = "UNKNOWN"


class MaterialCategory(str, Enum):
    """Physical category of a material library entry."""

    CONDUCTOR = "CONDUCTOR"        # copper, aluminium
    ENCLOSURE = "ENCLOSURE"        # steel, galvanised steel
    INSULATION = "INSULATION"      # ABS, FR plastic, epoxy
    COATING = "COATING"            # paint, polyester, SMC
    COMPOSITE = "COMPOSITE"        # multi-layer panels


class FanDirection(str, Enum):
    """Airflow direction relative to the fan face."""

    AXIAL_INTAKE = "AXIAL_INTAKE"
    AXIAL_EXHAUST = "AXIAL_EXHAUST"
    CENTRIFUGAL = "CENTRIFUGAL"


class OpeningAccessory(str, Enum):
    """Accessory type fitted to a ventilation opening."""

    NONE = "NONE"
    LOUVER = "LOUVER"
    GRILLE = "GRILLE"
    MESH = "MESH"
    FILTER = "FILTER"
    FILTER_WITH_GRILLE = "FILTER_WITH_GRILLE"


class CableInsulation(str, Enum):
    """Cable insulation type affecting loss model parameters."""

    PVC = "PVC"
    XLPE = "XLPE"
    EPR = "EPR"
    LSZH = "LSZH"
    MINERAL = "MINERAL"


class CableConductor(str, Enum):
    """Cable conductor material."""

    COPPER = "COPPER"
    ALUMINIUM = "ALUMINIUM"


# ---------------------------------------------------------------------------
# Power-loss curve point (device loss vs current)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LossCurvePoint:
    """
    Single point on a device power-loss vs load-current curve.

    current_fraction:
        Fraction of rated current (dimensionless, 0.0–1.25 typical).
    power_loss_w:
        Corresponding total power dissipated in watts (SI).
    """

    current_fraction: float   # 0.0 – 1.25, dimensionless
    power_loss_w: float       # watts, SI


# ---------------------------------------------------------------------------
# Fan curve point (pressure vs flow)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FanCurvePoint:
    """
    Single point on a fan pressure-flow characteristic curve.

    flow_m3_per_s:
        Volumetric flow rate in m³/s (SI).
    static_pressure_pa:
        Fan static pressure at that flow in pascals (SI).
    power_w:
        Shaft power consumed at that operating point in watts (SI).
        None if not supplied by the manufacturer.
    efficiency:
        Fan total efficiency at that point (0–1, dimensionless).
        None if not supplied.
    """

    flow_m3_per_s: float             # m³/s, SI
    static_pressure_pa: float        # Pa, SI
    power_w: Optional[float]         # watts, SI (may be None)
    efficiency: Optional[float]      # 0–1, dimensionless (may be None)


# ---------------------------------------------------------------------------
# Material library entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MaterialLibraryEntry:
    """
    Physical material specification for enclosure, conductor, or coating.

    All thermal properties at 20 °C (293.15 K) reference unless noted.
    Temperatures stored in kelvin (CR-ENG-003).
    """

    entry_id: str                              # UUID string
    library_version: str                       # semver, e.g. "1.0.0"
    name: str                                  # "Copper", "Mild Steel", …
    category: MaterialCategory
    thermal_conductivity_w_per_m_k: float      # W/(m·K), SI
    density_kg_per_m3: float                   # kg/m³, SI
    specific_heat_j_per_kg_k: float            # J/(kg·K), SI
    electrical_resistivity_ohm_m: Optional[float]  # Ω·m, SI; None for non-conductors
    temp_coeff_resistance_per_k: Optional[float]   # 1/K; None for non-conductors
    emissivity: Optional[float]                    # 0–1; None if not applicable
    max_operating_temp_k: Optional[float]          # K (CR-ENG-003)
    references: tuple[str, ...] = field(default_factory=tuple)
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Surface library entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SurfaceLibraryEntry:
    """
    Radiative and optical properties of a treated or coated surface.

    Used to populate boundary conditions for radiation calculations in M4.
    """

    entry_id: str
    library_version: str
    name: str                      # "RAL 7035 Powder Coat", "Bare Aluminium", …
    emissivity: float              # 0–1 (hemispherical total)
    absorptivity: Optional[float]  # 0–1; if None, assume = emissivity (grey body)
    roughness_um: Optional[float]  # surface roughness in micrometres
    coating: Optional[str]         # descriptive, e.g. "Polyester powder coat"
    material_ref: Optional[str]    # UUID of base material in MaterialLibraryEntry
    references: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Busbar profile library entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusbarProfileLibraryEntry:
    """
    Cross-sectional specification of a busbar conductor.

    material_ref:
        UUID of the MaterialLibraryEntry (must be a CONDUCTOR).
    All dimensions in metres (SI, CR-ENG-013).
    """

    entry_id: str
    library_version: str
    name: str                              # e.g. "Cu 50×5 Flat Bare"
    material_ref: str                      # UUID → MaterialLibraryEntry
    profile: BusbarProfile
    coating: BusbarCoating
    thickness_m: float                     # metres, SI
    width_m: float                         # metres, SI
    cross_section_area_m2: float           # metres², SI (may differ from width×thickness for non-flat)
    max_continuous_current_a: Optional[float]  # amperes, SI
    emissivity_override: Optional[float]   # overrides material emissivity if coated
    references: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Device library entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceLibraryEntry:
    """
    Full specification of a switchgear device for heat-source modelling.

    power_loss_curve:
        Ordered tuple of LossCurvePoint, sorted by current_fraction ascending.
        Must contain at least one point. The rated-current point (fraction=1.0)
        should always be present.
    max_ambient_temp_k:
        Maximum allowable ambient temperature in kelvin (CR-ENG-003).
    """

    entry_id: str
    library_version: str
    manufacturer: str              # "Siemens", "ABB", "Schneider Electric", …
    family: str                    # "3WL", "Emax 2", "Masterpact MTZ", …
    model: str                     # "3WL1225-3BB37-1AA2", …
    rated_current_a: float         # amperes, SI
    poles: int                     # 3 or 4
    width_m: float                 # metres, SI
    height_m: float                # metres, SI
    depth_m: float                 # metres, SI
    mounting_type: MountingType
    ventilation_requirement: VentilationRequirement
    max_ambient_temp_k: float      # kelvin (CR-ENG-003)
    power_loss_curve: tuple[LossCurvePoint, ...]
    loss_confidence: LossConfidence
    references: tuple[str, ...] = field(default_factory=tuple)
    notes: Optional[str] = None

    def power_loss_at_rated_w(self) -> Optional[float]:
        """Return loss at fraction=1.0 if the curve contains that point."""
        for pt in self.power_loss_curve:
            if abs(pt.current_fraction - 1.0) < 1e-6:
                return pt.power_loss_w
        return None


# ---------------------------------------------------------------------------
# Fan library entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FanLibraryEntry:
    """
    Manufacturer fan specification with complete pressure-flow curve.

    fan_curve:
        Ordered tuple of FanCurvePoint, sorted by flow_m3_per_s ascending.
        Must contain at least two points to define a curve.
    rated_speed_rpm:
        Nameplate speed. Used for fan affinity law scaling (M4).
    """

    entry_id: str
    library_version: str
    manufacturer: str
    model: str
    direction: FanDirection
    rated_speed_rpm: float         # rev/min
    rated_flow_m3_per_s: float     # m³/s at rated duty, SI
    rated_pressure_pa: float       # Pa static at rated duty, SI
    rated_power_w: float           # shaft power at rated duty, SI
    voltage_v: Optional[float]     # volts, SI
    frequency_hz: Optional[float]  # Hz, SI
    fan_curve: tuple[FanCurvePoint, ...]
    references: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Filter library entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FilterLibraryEntry:
    """
    Pressure-drop specification for a ventilation filter or mat.

    pressure_drop_pa:
        Pressure drop at rated_flow_m3_per_s in clean condition (pascals, SI).
    loss_coefficient:
        Dimensionless resistance coefficient K such that ΔP = K·ρ·v²/2.
        Used in M4 airflow network.
    """

    entry_id: str
    library_version: str
    manufacturer: str
    model: str
    dust_class: Optional[str]          # ISO 16890 / EN 779 class, e.g. "ePM10 50%"
    rated_flow_m3_per_s: float         # m³/s, SI
    pressure_drop_pa: float            # Pa at rated flow, clean (SI)
    loss_coefficient: float            # dimensionless
    porosity: Optional[float]          # 0–1 open area fraction
    initial_efficiency: Optional[float]  # 0–1
    references: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Ventilation opening library entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VentilationOpeningLibraryEntry:
    """
    Catalogue entry for a standard ventilation accessory (louver, grille, etc.).

    open_area_fraction:
        Net free area / gross area (dimensionless, 0–1).
    discharge_coefficient:
        Cd used in orifice-flow equation Q = Cd·A·√(2|ΔP|/ρ).
    """

    entry_id: str
    library_version: str
    manufacturer: str
    model: str
    accessory: OpeningAccessory
    gross_width_m: float               # metres, SI
    gross_height_m: float              # metres, SI
    open_area_fraction: float          # 0–1, dimensionless
    discharge_coefficient: float       # 0–1, dimensionless (typical 0.5–0.65)
    filter_ref: Optional[str]          # UUID → FilterLibraryEntry if integrated
    references: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Cable library entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CableLibraryEntry:
    """
    Cable specification for heat-source contribution estimation.

    resistance_ohm_per_m:
        DC resistance at 20 °C per metre of cable length (Ω/m, SI).
        Used with actual current to estimate I²R loss per unit length.
    """

    entry_id: str
    library_version: str
    manufacturer: Optional[str]
    designation: str               # e.g. "YJY 3×185 mm² CU XLPE"
    conductor: CableConductor
    insulation: CableInsulation
    conductor_cross_section_m2: float   # m², SI
    outer_diameter_m: float             # m, SI
    rated_current_a: float             # A, SI (per IEC 60364 / BS 7671 installation method)
    resistance_ohm_per_m: float        # Ω/m at 20 °C, SI
    temp_coeff_resistance_per_k: float  # 1/K, for correction to operating temp
    max_conductor_temp_k: float         # K (CR-ENG-003)
    references: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Connection (joint) library entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConnectionLibraryEntry:
    """
    Electrical joint resistance specification per DR-004 data hierarchy.

    joint_resistance_ohm:
        Total resistance of a single bolted joint in ohms (SI).
        Source must follow DR-004 hierarchy:
          MEASURED > MANUFACTURER > JOINT_LIBRARY > USER_ASSUMPTION
    bolt_torque_n_m:
        Required bolt torque in N·m (SI). None if not specified.
    """

    entry_id: str
    library_version: str
    name: str                          # e.g. "M10 silver-plated bolted Cu-Cu"
    contact_quality: ContactQuality
    plating: Optional[str]             # "silver", "tin", "nickel", None = bare
    bolt_size_m: Optional[float]       # bolt diameter, metres, SI
    bolt_torque_n_m: Optional[float]   # N·m, SI
    contact_pressure_pa: Optional[float]  # Pa, SI
    joint_resistance_ohm: float        # Ω, SI
    resistance_source: str             # ContactResistanceSource value
    age_factor: float = 1.0            # dimensionless multiplier for aged joints
    references: tuple[str, ...] = field(default_factory=tuple)
    notes: Optional[str] = None
