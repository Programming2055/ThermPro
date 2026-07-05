/**
 * EnclosureEditorPage — M2 2D SVG editor foundation.
 *
 * Renders a top-down (XZ plane) floor-plan view of the enclosure with
 * compartments, partitions, device placements, and busbar placements.
 *
 * Coordinate mapping:
 *   - Enclosure X (width) → SVG canvas X axis
 *   - Enclosure Z (depth) → SVG canvas Y axis (inverted: Z=0 at top)
 *   - Y (height) is not shown in this 2D view
 *
 * Scale: auto-fit to canvas dimensions preserving aspect ratio.
 *
 * No thermal/airflow calculations (M2 scope boundary, CR-ENG-001).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  compartmentsApi,
  partitionsApi,
  devicePlacementsApi,
  busbarPlacementsApi,
  enclosuresApi,
} from "@/api/client";
import type {
  BusbarPlacement,
  Compartment,
  DevicePlacement,
  Enclosure,
  Partition,
  ValidationResponse,
} from "@/types/api";

// ─── Scale helpers ────────────────────────────────────────────────────────────

const CANVAS_W = 640;
const CANVAS_H = 480;
const CANVAS_PADDING = 24;

interface ScaleCtx {
  scale: number;   // pixels per metre
  offsetX: number; // left padding in pixels
  offsetY: number; // top padding in pixels
}

function computeScale(widthM: number, depthM: number): ScaleCtx {
  const availW = CANVAS_W - 2 * CANVAS_PADDING;
  const availH = CANVAS_H - 2 * CANVAS_PADDING;
  const scale = Math.min(availW / widthM, availH / depthM);
  return {
    scale,
    offsetX: CANVAS_PADDING,
    offsetY: CANVAS_PADDING,
  };
}

/** Convert metres to SVG pixels along X axis. */
function mx(metres: number, ctx: ScaleCtx): number {
  return ctx.offsetX + metres * ctx.scale;
}

/** Convert metres to SVG pixels along Z axis (depth → Y on canvas). */
function mz(metres: number, ctx: ScaleCtx): number {
  return ctx.offsetY + metres * ctx.scale;
}

/** Convert metres to pixel length (same scale for both axes). */
function mLen(metres: number, ctx: ScaleCtx): number {
  return metres * ctx.scale;
}

// ─── Colour palette ───────────────────────────────────────────────────────────

const COMPARTMENT_COLOURS: Record<string, string> = {
  DEVICE_CHAMBER: "#b3d9f2",
  BUSBAR_CHAMBER: "#f2d9b3",
  CABLE_CHAMBER: "#d9f2b3",
  AUXILIARY_CHAMBER: "#f2b3d9",
  VENTILATION_CHAMBER: "#d9b3f2",
  CUSTOM: "#e0e0e0",
};

const SEVERITY_COLOURS: Record<string, string> = {
  BLOCKER: "#d32f2f",
  ERROR: "#f57c00",
  WARNING: "#fbc02d",
  INFO: "#1976d2",
};

// ─── Component ────────────────────────────────────────────────────────────────

interface SelectableEntity {
  kind: string;
  id: string;
  label: string;
  details: Record<string, string | number | boolean | null>;
}

export function EnclosureEditorPage() {
  const { enclosureId } = useParams<{ enclosureId: string }>();

  const [enclosure, setEnclosure] = useState<Enclosure | null>(null);
  const [compartments, setCompartments] = useState<Compartment[]>([]);
  const [partitions, setPartitions] = useState<Partition[]>([]);
  const [devices, setDevices] = useState<DevicePlacement[]>([]);
  const [busbars, setBusbars] = useState<BusbarPlacement[]>([]);
  const [selected, setSelected] = useState<SelectableEntity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationResponse | null>(null);
  const [validating, setValidating] = useState(false);

  const loadAll = useCallback(async () => {
    if (!enclosureId) return;
    setLoading(true);
    setError(null);
    try {
      const [enc, comps, parts, devs, buses] = await Promise.all([
        enclosuresApi.get(enclosureId),
        compartmentsApi.list(enclosureId),
        partitionsApi.list(enclosureId),
        devicePlacementsApi.list(enclosureId),
        busbarPlacementsApi.list(enclosureId),
      ]);
      setEnclosure(enc);
      setCompartments(comps);
      setPartitions(parts);
      setDevices(devs);
      setBusbars(buses);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load enclosure");
    } finally {
      setLoading(false);
    }
  }, [enclosureId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const scaleCtx = useMemo<ScaleCtx | null>(() => {
    if (!enclosure) return null;
    return computeScale(enclosure.internal_width_m, enclosure.internal_depth_m);
  }, [enclosure]);

  const runValidation = async () => {
    if (!enclosureId) return;
    setValidating(true);
    try {
      const result = await enclosuresApi.validate(enclosureId);
      setValidation(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Validation failed");
    } finally {
      setValidating(false);
    }
  };

  if (loading) return <p style={{ padding: "2rem" }}>Loading…</p>;
  if (error) return <p style={{ padding: "2rem", color: "#d32f2f" }}>{error}</p>;
  if (!enclosure || !scaleCtx) return <p style={{ padding: "2rem" }}>Enclosure not found.</p>;

  const enc = enclosure;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* ── Left panel: canvas ── */}
      <div style={{ flex: 1, padding: "1rem", overflow: "auto" }}>
        <h1 style={{ margin: "0 0 0.5rem", fontSize: "1.25rem" }}>
          {enc.name} — Floor Plan (XZ)
        </h1>
        <p style={{ margin: "0 0 1rem", fontSize: "0.8rem", color: "#666" }}>
          {Math.round(enc.internal_width_m * 1000)} mm ×{" "}
          {Math.round(enc.internal_depth_m * 1000)} mm internal
          {" | "}Scale: 1 m = {Math.round(scaleCtx.scale)} px
        </p>

        <svg
          width={CANVAS_W}
          height={CANVAS_H}
          style={{ border: "1px solid #ccc", background: "#fafafa", display: "block" }}
          aria-label={`Floor plan for enclosure ${enc.name}`}
        >
          {/* Enclosure boundary */}
          <rect
            x={mx(0, scaleCtx)}
            y={mz(0, scaleCtx)}
            width={mLen(enc.internal_width_m, scaleCtx)}
            height={mLen(enc.internal_depth_m, scaleCtx)}
            fill="none"
            stroke="#333"
            strokeWidth={2}
          />

          {/* Compartments */}
          {compartments.map((c) => {
            const fill = COMPARTMENT_COLOURS[c.compartment_type] ?? "#e0e0e0";
            const isSelected = selected?.id === c.id;
            return (
              <g
                key={c.id}
                onClick={() =>
                  setSelected({
                    kind: "Compartment",
                    id: c.id,
                    label: c.name,
                    details: {
                      type: c.compartment_type,
                      "X (m)": c.position_x_m,
                      "Z (m)": c.position_z_m,
                      "W (mm)": Math.round(c.width_m * 1000),
                      "H (mm)": Math.round(c.height_m * 1000),
                      "D (mm)": Math.round(c.depth_m * 1000),
                    },
                  })
                }
                style={{ cursor: "pointer" }}
                role="button"
                aria-label={`Compartment ${c.name}`}
              >
                <rect
                  x={mx(c.position_x_m, scaleCtx)}
                  y={mz(c.position_z_m, scaleCtx)}
                  width={mLen(c.width_m, scaleCtx)}
                  height={mLen(c.depth_m, scaleCtx)}
                  fill={fill}
                  stroke={isSelected ? "#1976d2" : "#555"}
                  strokeWidth={isSelected ? 2.5 : 1}
                  opacity={0.85}
                />
                <text
                  x={mx(c.position_x_m + c.width_m / 2, scaleCtx)}
                  y={mz(c.position_z_m + c.depth_m / 2, scaleCtx)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={Math.max(9, Math.min(12, mLen(c.width_m, scaleCtx) / 6))}
                  fill="#333"
                  pointerEvents="none"
                >
                  {c.name}
                </text>
              </g>
            );
          })}

          {/* Partitions */}
          {partitions.map((p) => {
            const isSelected = selected?.id === p.id;
            const x1 = mx(p.position_x_m, scaleCtx);
            const z1 = mz(p.position_z_m, scaleCtx);
            const isVertical = p.orientation === "VERTICAL_YZ";
            return (
              <line
                key={p.id}
                x1={x1}
                y1={z1}
                x2={isVertical ? x1 : mx(p.position_x_m + p.width_m, scaleCtx)}
                y2={isVertical ? mz(p.position_z_m + p.width_m, scaleCtx) : z1}
                stroke={isSelected ? "#1976d2" : "#555"}
                strokeWidth={isSelected ? 3 : 1.5}
                strokeDasharray="4 2"
                style={{ cursor: "pointer" }}
                onClick={() =>
                  setSelected({
                    kind: "Partition",
                    id: p.id,
                    label: p.name ?? p.id,
                    details: {
                      orientation: p.orientation,
                      "X (m)": p.position_x_m,
                      "Z (m)": p.position_z_m,
                      "W (mm)": Math.round(p.width_m * 1000),
                      "H (mm)": Math.round(p.height_m * 1000),
                      "T (mm)": Math.round(p.thickness_m * 1000),
                    },
                  })
                }
              />
            );
          })}

          {/* Device placements */}
          {devices.map((d) => {
            const isSelected = selected?.id === d.id;
            return (
              <g
                key={d.id}
                onClick={() =>
                  setSelected({
                    kind: "Device",
                    id: d.id,
                    label: d.name,
                    details: {
                      "X (m)": d.position_x_m,
                      "Z (m)": d.position_z_m,
                      "W (mm)": Math.round(d.width_m * 1000),
                      "H (mm)": Math.round(d.height_m * 1000),
                      "D (mm)": Math.round(d.depth_m * 1000),
                      ref: d.device_library_ref ?? "—",
                    },
                  })
                }
                style={{ cursor: "pointer" }}
                role="button"
                aria-label={`Device ${d.name}`}
              >
                <rect
                  x={mx(d.position_x_m, scaleCtx)}
                  y={mz(d.position_z_m, scaleCtx)}
                  width={mLen(d.width_m, scaleCtx)}
                  height={mLen(d.depth_m, scaleCtx)}
                  fill={isSelected ? "#90caf9" : "#bbdefb"}
                  stroke={isSelected ? "#1565c0" : "#1976d2"}
                  strokeWidth={isSelected ? 2 : 1}
                />
              </g>
            );
          })}

          {/* Busbar placements */}
          {busbars.map((b) => {
            const isSelected = selected?.id === b.id;
            return (
              <rect
                key={b.id}
                x={mx(b.position_x_m, scaleCtx)}
                y={mz(b.position_z_m, scaleCtx)}
                width={mLen(b.width_m, scaleCtx)}
                height={mLen(b.length_m, scaleCtx)}
                fill={isSelected ? "#ffcc80" : "#ffe0b2"}
                stroke={isSelected ? "#e65100" : "#ef6c00"}
                strokeWidth={isSelected ? 2 : 1}
                style={{ cursor: "pointer" }}
                onClick={() =>
                  setSelected({
                    kind: "Busbar",
                    id: b.id,
                    label: b.name,
                    details: {
                      phase: b.phase_designation ?? "—",
                      "X (m)": b.position_x_m,
                      "Z (m)": b.position_z_m,
                      "W (mm)": Math.round(b.width_m * 1000),
                      "L (mm)": Math.round(b.length_m * 1000),
                      "T (mm)": Math.round(b.thickness_m * 1000),
                    },
                  })
                }
              />
            );
          })}
        </svg>

        {/* Legend */}
        <div style={{ display: "flex", gap: "1rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
          {Object.entries(COMPARTMENT_COLOURS).map(([type, colour]) => (
            <span key={type} style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem" }}>
              <span style={{ width: 14, height: 14, background: colour, border: "1px solid #999", display: "inline-block" }} />
              {type.replace(/_/g, " ")}
            </span>
          ))}
          <span style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem" }}>
            <span style={{ width: 14, height: 14, background: "#bbdefb", border: "1px solid #1976d2", display: "inline-block" }} />
            Device
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem" }}>
            <span style={{ width: 14, height: 14, background: "#ffe0b2", border: "1px solid #ef6c00", display: "inline-block" }} />
            Busbar
          </span>
        </div>
      </div>

      {/* ── Right panel: inspector + validation ── */}
      <div
        style={{
          width: 280,
          borderLeft: "1px solid #e0e0e0",
          padding: "1rem",
          overflowY: "auto",
          background: "#fff",
          display: "flex",
          flexDirection: "column",
          gap: "1.5rem",
        }}
      >
        {/* Entity inspector */}
        <section>
          <h2 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem", color: "#333" }}>
            Inspector
          </h2>
          {selected ? (
            <div>
              <p style={{ margin: "0 0 0.25rem", fontWeight: 600, fontSize: "0.9rem" }}>
                {selected.kind}: {selected.label}
              </p>
              <table style={{ width: "100%", fontSize: "0.8rem", borderCollapse: "collapse" }}>
                <tbody>
                  {Object.entries(selected.details).map(([k, v]) => (
                    <tr key={k}>
                      <td style={{ paddingRight: "0.5rem", color: "#666" }}>{k}</td>
                      <td style={{ fontFamily: "monospace" }}>{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ color: "#999", fontSize: "0.85rem" }}>
              Click a shape on the canvas to inspect it.
            </p>
          )}
        </section>

        {/* Summary counts */}
        <section>
          <h2 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem", color: "#333" }}>
            Contents
          </h2>
          <ul style={{ margin: 0, padding: "0 0 0 1rem", fontSize: "0.85rem" }}>
            <li>{compartments.length} compartment{compartments.length !== 1 ? "s" : ""}</li>
            <li>{partitions.length} partition{partitions.length !== 1 ? "s" : ""}</li>
            <li>{devices.length} device placement{devices.length !== 1 ? "s" : ""}</li>
            <li>{busbars.length} busbar placement{busbars.length !== 1 ? "s" : ""}</li>
          </ul>
        </section>

        {/* Validation */}
        <section>
          <h2 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem", color: "#333" }}>
            Geometry Validation
          </h2>
          <button
            onClick={runValidation}
            disabled={validating}
            style={{
              padding: "0.35rem 0.75rem",
              fontSize: "0.85rem",
              cursor: validating ? "wait" : "pointer",
              borderRadius: 4,
              border: "1px solid #1976d2",
              background: "#e3f2fd",
              color: "#1565c0",
            }}
          >
            {validating ? "Validating…" : "Run Validation"}
          </button>

          {validation && (
            <div style={{ marginTop: "0.75rem" }}>
              <p style={{ margin: "0 0 0.5rem", fontSize: "0.85rem" }}>
                {validation.issue_count === 0 ? (
                  <span style={{ color: "#388e3c" }}>✓ No issues found</span>
                ) : (
                  <span>
                    {validation.error_count > 0 && (
                      <span style={{ color: SEVERITY_COLOURS.ERROR }}>
                        {validation.error_count} error{validation.error_count !== 1 ? "s" : ""}
                      </span>
                    )}
                    {validation.error_count > 0 && validation.warning_count > 0 && ", "}
                    {validation.warning_count > 0 && (
                      <span style={{ color: SEVERITY_COLOURS.WARNING }}>
                        {validation.warning_count} warning{validation.warning_count !== 1 ? "s" : ""}
                      </span>
                    )}
                  </span>
                )}
              </p>
              <ul style={{ margin: 0, padding: 0, listStyle: "none", fontSize: "0.78rem" }}>
                {validation.issues.map((issue) => (
                  <li
                    key={issue.id}
                    style={{
                      borderLeft: `3px solid ${SEVERITY_COLOURS[issue.severity] ?? "#999"}`,
                      paddingLeft: "0.5rem",
                      marginBottom: "0.4rem",
                      color: "#333",
                    }}
                  >
                    <strong>{issue.rule_id}</strong> — {issue.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
