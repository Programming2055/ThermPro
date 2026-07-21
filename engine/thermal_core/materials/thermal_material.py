"""
ThermalMaterial — a resolved, immutable engineering material for the solver.

The LibraryResolver converts MaterialLibraryEntry (M3) into ThermalMaterial (M4).
The solver only sees ThermalMaterial — it never queries the library.

All values in SI base units (CR-ENG-013, M0-10).
Temperatures in kelvin (CR-ENG-003).

This class deliberately uses property methods with a temperature argument to
prepare the interface for future temperature-dependent properties (k(T), Cp(T),
ρ(T), ε(T), ρe(T)).  In MVP they return constant values, but callers are
written to pass T so the interface need not change when T-dependence is added.

Equation reference: THERM-EQN-001 §6.1 (Solid Material Properties)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ThermalMaterial:
    """
    Resolved thermophysical and electrical properties of a solid material.

    MVP: all properties are constant (independent of temperature).
    Future: polynomial or lookup-table T-dependence can be added without
    changing the calling interface.
    """
    material_id: str
    name: str

    # Thermal properties (SI)
    thermal_conductivity_w_per_m_k: float   # k [W/(m·K)]
    density_kg_per_m3: float                # ρ [kg/m³]
    specific_heat_j_per_kg_k: float         # Cp [J/(kg·K)]

    # Electrical properties (optional)
    electrical_resistivity_ohm_m: Optional[float] = None   # ρ_e [Ω·m] at T_ref
    temp_coeff_resistance_per_k: Optional[float] = None    # α_T [K⁻¹]

    # Surface radiative property (if material surface is exposed)
    emissivity: Optional[float] = None      # ε [-]

    # Maximum operating temperature
    max_operating_temp_k: Optional[float] = None  # T_max [K]

    def __post_init__(self) -> None:
        if self.thermal_conductivity_w_per_m_k <= 0:
            raise ValueError(
                f"ThermalMaterial.thermal_conductivity_w_per_m_k must be > 0; "
                f"got {self.thermal_conductivity_w_per_m_k}"
            )
        if self.density_kg_per_m3 <= 0:
            raise ValueError(
                f"ThermalMaterial.density_kg_per_m3 must be > 0; "
                f"got {self.density_kg_per_m3}"
            )
        if self.specific_heat_j_per_kg_k <= 0:
            raise ValueError(
                f"ThermalMaterial.specific_heat_j_per_kg_k must be > 0; "
                f"got {self.specific_heat_j_per_kg_k}"
            )
        if self.emissivity is not None and not (0.0 <= self.emissivity <= 1.0):
            raise ValueError(
                f"ThermalMaterial.emissivity must be in [0, 1]; got {self.emissivity}"
            )
        if (
            self.max_operating_temp_k is not None
            and self.max_operating_temp_k <= 0
        ):
            raise ValueError(
                f"ThermalMaterial.max_operating_temp_k must be > 0 K; "
                f"got {self.max_operating_temp_k}"
            )

    # ------------------------------------------------------------------
    # Temperature-aware property interface (MVP: constant values)
    # ------------------------------------------------------------------

    def k(self, temperature_k: float) -> float:
        """Thermal conductivity at T [W/(m·K)]. MVP: constant."""
        _ = temperature_k  # reserved for future T-dependence
        return self.thermal_conductivity_w_per_m_k

    def rho(self, temperature_k: float) -> float:
        """Density at T [kg/m³]. MVP: constant."""
        _ = temperature_k
        return self.density_kg_per_m3

    def cp(self, temperature_k: float) -> float:
        """Specific heat capacity at T [J/(kg·K)]. MVP: constant."""
        _ = temperature_k
        return self.specific_heat_j_per_kg_k

    def rho_e(self, temperature_k: float, t_ref_k: float = 293.15) -> Optional[float]:
        """
        Electrical resistivity at T [Ω·m] with linear temperature correction.

        ρ_e(T) = ρ_e(T_ref) × [1 + α_T × (T - T_ref)]

        Returns None if electrical_resistivity_ohm_m is not specified.
        """
        if self.electrical_resistivity_ohm_m is None:
            return None
        if self.temp_coeff_resistance_per_k is None:
            return self.electrical_resistivity_ohm_m
        alpha = self.temp_coeff_resistance_per_k
        return self.electrical_resistivity_ohm_m * (1.0 + alpha * (temperature_k - t_ref_k))

    def eps(self, temperature_k: float) -> Optional[float]:
        """Emissivity at T [-]. MVP: constant. Returns None if not set."""
        _ = temperature_k
        return self.emissivity
