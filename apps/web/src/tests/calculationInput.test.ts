import { describe, expect, it } from "vitest";
import {
  buildInputSnapshot,
  DEFAULT_FORM,
  FACES,
  kelvinToCelsius,
  validateForm,
} from "@/lib/calculationInput";

type Snap = {
  mode: string;
  schema_version: string;
  library_manifest: object;
  enclosure: { external_height_m: number; devices: Array<{ id: string; load_current_A: number }> };
  service_conditions: { ambient_temperature_max_C: number };
};

describe("buildInputSnapshot", () => {
  it("produces a MODE_2 snapshot with an explicit (empty) library manifest", () => {
    const s = buildInputSnapshot(DEFAULT_FORM) as unknown as Snap;
    expect(s.mode).toBe("MODE_2");
    expect(s.schema_version).toBe("1.0");
    expect(s.library_manifest).toEqual({});
  });

  it("maps form values to SI schema fields", () => {
    const s = buildInputSnapshot({
      ...DEFAULT_FORM,
      heightM: 1.8,
      ambientMaxC: 35,
    }) as unknown as Snap;
    expect(s.enclosure.external_height_m).toBe(1.8);
    expect(s.service_conditions.ambient_temperature_max_C).toBe(35);
    expect(s.enclosure.devices[0]?.load_current_A).toBe(400);
  });

  it("gives every device a unique id", () => {
    const f = { ...DEFAULT_FORM, devices: [DEFAULT_FORM.devices[0]!, DEFAULT_FORM.devices[0]!] };
    const s = buildInputSnapshot(f) as unknown as Snap;
    expect(new Set(s.enclosure.devices.map((d) => d.id)).size).toBe(2);
  });
});

describe("validateForm", () => {
  it("accepts the defaults", () => {
    expect(validateForm(DEFAULT_FORM)).toEqual([]);
  });

  it("rejects non-positive dimensions", () => {
    expect(validateForm({ ...DEFAULT_FORM, heightM: 0 })).toContain(
      "Height must be greater than 0."
    );
  });

  it("rejects all faces restricted", () => {
    expect(validateForm({ ...DEFAULT_FORM, restricted: [...FACES] }).length).toBe(1);
  });

  it("rejects average ambient above maximum", () => {
    expect(validateForm({ ...DEFAULT_FORM, ambientAvgC: 50 }).length).toBe(1);
  });
});

describe("kelvinToCelsius", () => {
  it("converts at the display boundary", () => {
    expect(kelvinToCelsius(313.15)).toBeCloseTo(40, 10);
  });
});
