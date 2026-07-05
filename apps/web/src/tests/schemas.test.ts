import { describe, it, expect } from "vitest";
import { FanOperatingStateSchema, StandardProfileSchema, CalculationModeSchema } from "@/types/schemas";

describe("FanOperatingStateSchema", () => {
  const valid = [
    "RUNNING_FORWARD",
    "STOPPED_FREE_FLOW",
    "STOPPED_WITH_DAMPER",
    "FAILED_OPEN",
    "FAILED_BLOCKED",
    "REVERSE_FLOW_ESTIMATED",
  ] as const;

  for (const state of valid) {
    it(`accepts ${state}`, () => {
      expect(FanOperatingStateSchema.parse(state)).toBe(state);
    });
  }

  it("rejects old name FORWARD_OPERATING", () => {
    expect(() => FanOperatingStateSchema.parse("FORWARD_OPERATING")).toThrow();
  });

  it("rejects old name ESTIMATED_REVERSE_FLOW", () => {
    expect(() => FanOperatingStateSchema.parse("ESTIMATED_REVERSE_FLOW")).toThrow();
  });
});

describe("StandardProfileSchema", () => {
  it("rejects UL_891 (deferred to Phase 3+)", () => {
    expect(() => StandardProfileSchema.parse("UL_891")).toThrow();
  });

  it("rejects ARC_FLASH (removed from MVP)", () => {
    expect(() => StandardProfileSchema.parse("ARC_FLASH")).toThrow();
  });

  it("accepts IEC_61439_2", () => {
    expect(StandardProfileSchema.parse("IEC_61439_2")).toBe("IEC_61439_2");
  });
});

describe("CalculationModeSchema", () => {
  it("rejects ARC_FLASH mode (removed from MVP)", () => {
    expect(() => CalculationModeSchema.parse("ARC_FLASH")).toThrow();
  });

  it("accepts MODE_1 through MODE_4", () => {
    for (const mode of ["MODE_1", "MODE_2", "MODE_3", "MODE_4"] as const) {
      expect(CalculationModeSchema.parse(mode)).toBe(mode);
    }
  });
});
