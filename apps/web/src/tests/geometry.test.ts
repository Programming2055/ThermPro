/**
 * M2 geometry — frontend unit tests.
 *
 * Tests cover:
 * 1. Scale conversion helpers (metres ↔ pixels)
 * 2. Zod schema validation for geometry request types
 */
import { describe, expect, it } from "vitest";
import { z } from "zod";

// ─── Scale conversion helpers (inlined to avoid importing React components) ──

const CANVAS_PADDING = 24;

interface ScaleCtx {
  scale: number;
  offsetX: number;
  offsetY: number;
}

function computeScale(
  widthM: number,
  depthM: number,
  canvasW = 640,
  canvasH = 480
): ScaleCtx {
  const availW = canvasW - 2 * CANVAS_PADDING;
  const availH = canvasH - 2 * CANVAS_PADDING;
  const scale = Math.min(availW / widthM, availH / depthM);
  return { scale, offsetX: CANVAS_PADDING, offsetY: CANVAS_PADDING };
}

function mx(metres: number, ctx: ScaleCtx): number {
  return ctx.offsetX + metres * ctx.scale;
}

function mz(metres: number, ctx: ScaleCtx): number {
  return ctx.offsetY + metres * ctx.scale;
}

function mLen(metres: number, ctx: ScaleCtx): number {
  return metres * ctx.scale;
}

// ─── Geometry Zod schemas (local subset for frontend validation) ─────────────

const CreateEnclosureSchema = z.object({
  name: z.string().min(1),
  external_width_m: z.number().positive(),
  external_height_m: z.number().positive(),
  external_depth_m: z.number().positive(),
  internal_width_m: z.number().positive(),
  internal_height_m: z.number().positive(),
  internal_depth_m: z.number().positive(),
  wall_thickness_m: z.number().positive().optional(),
  installation_type: z
    .enum(["FLOOR_STANDING", "WALL_MOUNTED", "RACK_MOUNTED", "FREESTANDING"])
    .optional(),
});

const CreateCompartmentSchema = z.object({
  name: z.string().min(1),
  compartment_type: z
    .enum([
      "DEVICE_CHAMBER",
      "BUSBAR_CHAMBER",
      "CABLE_CHAMBER",
      "AUXILIARY_CHAMBER",
      "VENTILATION_CHAMBER",
      "CUSTOM",
    ])
    .optional(),
  position_x_m: z.number().min(0).optional(),
  position_y_m: z.number().min(0).optional(),
  position_z_m: z.number().min(0).optional(),
  width_m: z.number().positive(),
  height_m: z.number().positive(),
  depth_m: z.number().positive(),
});

// ─── Scale conversion tests ───────────────────────────────────────────────────

describe("computeScale", () => {
  it("produces a positive scale for a standard enclosure", () => {
    const ctx = computeScale(1.0, 0.8);
    expect(ctx.scale).toBeGreaterThan(0);
  });

  it("offsets origin by CANVAS_PADDING", () => {
    const ctx = computeScale(1.0, 0.8);
    expect(ctx.offsetX).toBe(CANVAS_PADDING);
    expect(ctx.offsetY).toBe(CANVAS_PADDING);
  });

  it("scale is limited by the constraining dimension (min of both axes)", () => {
    // Wide shallow enclosure: width axis constrains (592/10=59.2, 432/0.5=864) → 59.2
    const wide = computeScale(10.0, 0.5);
    // Deep narrow enclosure: depth axis constrains (592/0.5=1184, 432/10=43.2) → 43.2
    const deepNarrow = computeScale(0.5, 10.0);
    expect(wide.scale).toBeCloseTo(59.2, 1);
    expect(deepNarrow.scale).toBeCloseTo(43.2, 1);
  });

  it("maps 0 metres to offset", () => {
    const ctx = computeScale(1.0, 0.8);
    expect(mx(0, ctx)).toBe(ctx.offsetX);
    expect(mz(0, ctx)).toBe(ctx.offsetY);
  });

  it("maps enclosure width to full available canvas width (approx)", () => {
    const ctx = computeScale(1.0, 0.8, 640, 480);
    const pixelWidth = mLen(1.0, ctx);
    expect(pixelWidth).toBeLessThanOrEqual(640 - 2 * CANVAS_PADDING + 0.001);
    expect(pixelWidth).toBeGreaterThan(0);
  });

  it("mLen returns 0 for 0 metres", () => {
    const ctx = computeScale(1.0, 0.8);
    expect(mLen(0, ctx)).toBe(0);
  });

  it("mLen is proportional — double metres gives double pixels", () => {
    const ctx = computeScale(2.0, 1.0);
    expect(mLen(0.5, ctx)).toBeCloseTo(mLen(1.0, ctx) / 2, 6);
  });

  it("mx and mz preserve relative ordering", () => {
    const ctx = computeScale(1.0, 0.8);
    expect(mx(0.5, ctx)).toBeGreaterThan(mx(0.0, ctx));
    expect(mz(0.4, ctx)).toBeGreaterThan(mz(0.0, ctx));
  });
});

// ─── Zod schema validation ────────────────────────────────────────────────────

describe("CreateEnclosureSchema", () => {
  it("accepts a valid enclosure request", () => {
    const result = CreateEnclosureSchema.safeParse({
      name: "MCC Panel A",
      external_width_m: 0.6,
      external_height_m: 2.0,
      external_depth_m: 0.4,
      internal_width_m: 0.556,
      internal_height_m: 1.95,
      internal_depth_m: 0.356,
    });
    expect(result.success).toBe(true);
  });

  it("rejects zero external width", () => {
    const result = CreateEnclosureSchema.safeParse({
      name: "Bad",
      external_width_m: 0,
      external_height_m: 2.0,
      external_depth_m: 0.4,
      internal_width_m: 0.5,
      internal_height_m: 1.9,
      internal_depth_m: 0.35,
    });
    expect(result.success).toBe(false);
  });

  it("rejects negative internal height", () => {
    const result = CreateEnclosureSchema.safeParse({
      name: "Bad",
      external_width_m: 0.6,
      external_height_m: 2.0,
      external_depth_m: 0.4,
      internal_width_m: 0.5,
      internal_height_m: -1.0,
      internal_depth_m: 0.35,
    });
    expect(result.success).toBe(false);
  });

  it("rejects empty name", () => {
    const result = CreateEnclosureSchema.safeParse({
      name: "",
      external_width_m: 0.6,
      external_height_m: 2.0,
      external_depth_m: 0.4,
      internal_width_m: 0.5,
      internal_height_m: 1.9,
      internal_depth_m: 0.35,
    });
    expect(result.success).toBe(false);
  });

  it("accepts optional installation_type", () => {
    const result = CreateEnclosureSchema.safeParse({
      name: "X",
      external_width_m: 0.6,
      external_height_m: 2.0,
      external_depth_m: 0.4,
      internal_width_m: 0.5,
      internal_height_m: 1.9,
      internal_depth_m: 0.35,
      installation_type: "WALL_MOUNTED",
    });
    expect(result.success).toBe(true);
  });
});

describe("CreateCompartmentSchema", () => {
  it("accepts a valid compartment", () => {
    const result = CreateCompartmentSchema.safeParse({
      name: "Device bay",
      width_m: 0.5,
      height_m: 1.8,
      depth_m: 0.35,
    });
    expect(result.success).toBe(true);
  });

  it("rejects zero depth", () => {
    const result = CreateCompartmentSchema.safeParse({
      name: "X",
      width_m: 0.5,
      height_m: 1.8,
      depth_m: 0,
    });
    expect(result.success).toBe(false);
  });

  it("rejects invalid compartment_type", () => {
    const result = CreateCompartmentSchema.safeParse({
      name: "X",
      width_m: 0.5,
      height_m: 1.8,
      depth_m: 0.35,
      compartment_type: "ARC_FLASH_CHAMBER",
    });
    expect(result.success).toBe(false);
  });
});
