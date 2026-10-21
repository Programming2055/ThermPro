/**
 * Builds the M0-03 InputSnapshot for a MODE_2 (zonal thermal network) run
 * from the New Calculation form. Pure function; all units are SI and
 * temperatures are in °C here because the schema converts at its boundary.
 */

export const FACES = ["FRONT", "REAR", "LEFT", "RIGHT", "TOP", "BOTTOM"] as const;
export type Face = (typeof FACES)[number];

export type ThermalModel = "QUADRATIC" | "LINEAR" | "FIXED_POWER";
export type DataConfidence = "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";

export interface DeviceForm {
  name: string;
  loadCurrentA: number;
  ratedCurrentA: number;
  powerAtRatedW: number;
  thermalModel: ThermalModel;
  dataConfidence: DataConfidence;
}

export interface CalculationForm {
  heightM: number;
  widthM: number;
  depthM: number;
  wallThicknessM: number;
  wallConductivity: number;
  emissivity: number;
  restricted: Face[];
  ambientMaxC: number;
  ambientAvgC: number;
  humidityPercent: number;
  devices: DeviceForm[];
  maxIterations: number;
  toleranceK: number;
  relaxation: number;
}

export const DEFAULT_FORM: CalculationForm = {
  heightM: 2.0,
  widthM: 0.8,
  depthM: 0.6,
  wallThicknessM: 0.002,
  wallConductivity: 50,
  emissivity: 0.9,
  restricted: [],
  ambientMaxC: 40,
  ambientAvgC: 35,
  humidityPercent: 50,
  devices: [
    {
      name: "MCCB-1",
      loadCurrentA: 400,
      ratedCurrentA: 630,
      powerAtRatedW: 200,
      thermalModel: "QUADRATIC",
      dataConfidence: "MEDIUM",
    },
  ],
  maxIterations: 200,
  toleranceK: 0.01,
  relaxation: 0.7,
};

const uuid = (): string => crypto.randomUUID();

export function buildInputSnapshot(f: CalculationForm): Record<string, unknown> {
  return {
    schema_version: "1.0",
    mode: "MODE_2",
    standard_profile: ["IEC_61439_2"],
    // No library release is pinned: device losses are entered inline.
    library_manifest: {},
    service_conditions: {
      ambient_temperature_max_C: f.ambientMaxC,
      ambient_temperature_avg_24h_C: f.ambientAvgC,
      relative_humidity_max_percent: f.humidityPercent,
      altitude_m: 0,
      pollution_degree: 2,
    },
    enclosure: {
      id: uuid(),
      external_height_m: f.heightM,
      external_width_m: f.widthM,
      external_depth_m: f.depthM,
      wall_thickness_m: f.wallThicknessM,
      wall_thermal_conductivity_W_mK: f.wallConductivity,
      paint_emissivity: f.emissivity,
      restricted_surfaces: f.restricted,
      devices: f.devices.map((d, i) => ({
        id: uuid(),
        name: d.name || `Device ${i + 1}`,
        device_library_id: "manual",
        position_x_m: 0.1,
        position_y_m: 0.1,
        position_z_m: 0.1 + i * 0.1,
        load_current_A: d.loadCurrentA,
        rated_current_A: d.ratedCurrentA,
        thermal_model: d.thermalModel,
        power_at_rated_W: d.powerAtRatedW,
        data_confidence: d.dataConfidence,
      })),
    },
    solver_settings: {
      max_outer_iterations: 50,
      max_inner_iterations: f.maxIterations,
      convergence_T_K: f.toleranceK,
      convergence_flow_fraction: 0.005,
      convergence_power_fraction: 0.005,
      energy_imbalance_limit: 0.01,
      mass_imbalance_limit: 0.005,
      relaxation_factor: f.relaxation,
    },
  };
}

/** Client-side checks that mirror the schema; returns a list of problems. */
export function validateForm(f: CalculationForm): string[] {
  const problems: string[] = [];
  const positive: Array<[string, number]> = [
    ["Height", f.heightM],
    ["Width", f.widthM],
    ["Depth", f.depthM],
    ["Wall thickness", f.wallThicknessM],
    ["Wall conductivity", f.wallConductivity],
    ["Tolerance", f.toleranceK],
  ];
  for (const [label, v] of positive) {
    if (!(v > 0)) problems.push(`${label} must be greater than 0.`);
  }
  if (f.emissivity < 0 || f.emissivity > 1) problems.push("Emissivity must be between 0 and 1.");
  if (f.relaxation <= 0 || f.relaxation > 1) problems.push("Relaxation must be in (0, 1].");
  if (f.maxIterations < 1 || f.maxIterations > 1000)
    problems.push("Max iterations must be between 1 and 1000.");
  if (f.ambientAvgC > f.ambientMaxC)
    problems.push("24 h average ambient must not exceed the maximum ambient.");
  if (f.restricted.length === FACES.length)
    problems.push("At least one face must exchange heat with the surroundings.");
  f.devices.forEach((d, i) => {
    if (!(d.ratedCurrentA > 0)) problems.push(`Device ${i + 1}: rated current must be > 0.`);
    if (d.loadCurrentA < 0 || d.powerAtRatedW < 0)
      problems.push(`Device ${i + 1}: current and power must not be negative.`);
  });
  return problems;
}

export const kelvinToCelsius = (k: number): number => k - 273.15;
